import logging
import math
import time
import numpy as np
import torch
from line_profiler import profile
from rl.env import EngineEnv, sys_config
from rl.config import setup_logging, init_mlflow, end_mlflow, log_metrics, encode_human_intent
from rl.gail import GAILArgs
from rl.config import num_envs as cfg_num_envs, pop_size as cfg_pop_size, steps_per_gen as cfg_steps_per_gen, min_expert_frames, expert_max_matches, expert_max_frames
from rl.expert_buffer import ExpertBuffer
from Game import poll_events, MenuResult, Visuals, step_interactive_frameskip

import os
# Torch intra-op threads alternate with the engine's OpenMP threads (never
# concurrent), so torch can use half the cores without oversubscribing.
torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))

logger = logging.getLogger("rl.test_gail")


@profile
def main():
    setup_logging()
    init_mlflow(project="rl-engine", run_name="pb2_gail_interactive")

    render_env = EngineEnv(render=True, sys_config=sys_config)
    Visuals.init(render_env.engine, render_env.p1, render_env.p2)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    from rl.pb2_league import PB2League
    league = PB2League(pop_size=cfg_pop_size(), num_envs=cfg_num_envs(), device=device)

    expert_buffer = ExpertBuffer(max_matches=expert_max_matches(), max_frames=expert_max_frames())

    cycle_num = 1
    while True:
        cycle_start = time.time()
        champion = league.get_champion()
        champion.gail.env = render_env

        logger.info("CYCLE %d", cycle_num)
        logger.info(
            "Challenging Champion %d (Score: %.2f, GenLR: %.2e, DiscLR: %.2e)",
            champion.id,
            champion.score,
            champion.gen_lr,
            champion.disc_lr,
        )

        start_play = False
        while True:
            frame = poll_events()
            if frame.quit:
                return
            result = Visuals.start_menu(render_env.engine, frame)
            if result == MenuResult.PLAY:
                start_play = True
                break
            elif result == MenuResult.QUIT:
                return

        if not start_play:
            break

        # --- PHASE 1: Human vs PPO (Collecting Data) ---
        logger.info("PHASE 1: Human vs PPO (Collecting Data)")
        render_env.reset()
        expert_obs = []
        expert_actions = []

        boss_lstm_state = (
            torch.zeros(champion.gail.boss.lstm.num_layers, 1, champion.gail.boss.lstm.hidden_size).to(device),
            torch.zeros(champion.gail.boss.lstm.num_layers, 1, champion.gail.boss.lstm.hidden_size).to(device),
        )

        frame_skip = render_env.frame_skip
        quit_early = False

        render_env.p1.damage_dealt_step = 0.0
        render_env.p1.damage_taken_step = 0.0
        render_env.p2.damage_dealt_step = 0.0
        render_env.p2.damage_taken_step = 0.0
        human_total_damage_dealt = 0.0
        human_total_damage_taken = 0.0

        while not render_env.engine.is_done():
            current_obs = render_env._get_obs()
            # Aim must be encoded against the position the obs was taken at,
            # not the post-step position.
            pre_px, pre_py = render_env.p1.px, render_env.p1.py

            current_boss_intent, boss_lstm_state = champion.gail.get_boss_intent(current_obs["boss"], boss_lstm_state, render_env.p2)

            fake_intent, quit_early = step_interactive_frameskip(render_env.engine, current_boss_intent, frame_skip, 1.0 / 60.0)

            expert_obs.append(current_obs["player"])
            expert_actions.append(encode_human_intent(fake_intent, pre_px, pre_py))
            human_total_damage_dealt += render_env.p1.damage_dealt_step
            human_total_damage_taken += render_env.p1.damage_taken_step

            if quit_early:
                break

        assert len(expert_obs) > 0
        expert_buffer.add_match(expert_obs, expert_actions)
        human_damage_ratio = human_total_damage_dealt / (human_total_damage_dealt + human_total_damage_taken + 1e-8)

        logger.info("Collected %d frames of expert data (total: %d)", len(expert_obs), len(expert_buffer))

        if len(expert_buffer) < min_expert_frames():
            logger.warning(
                "Not enough expert data (%d < %d), skipping training this cycle",
                len(expert_buffer), min_expert_frames(),
            )
            cycle_num += 1
            continue
        dx = render_env.p1.px - render_env.p2.px
        dy = render_env.p1.py - render_env.p2.py
        log_metrics({
            "eval/match_duration_s": len(expert_obs) * frame_skip / 60.0,
            "eval/human_health": render_env.p1.health,
            "eval/boss_health": render_env.p2.health,
            "eval/human_damage_dealt": human_total_damage_dealt,
            "eval/human_damage_taken": human_total_damage_taken,
            "eval/human_damage_ratio": human_damage_ratio,
            "eval/distance_to_opponent": math.sqrt(dx * dx + dy * dy),
        }, step=cycle_num)

        # --- PHASE 2: Train all generators (GAIL) ---
        logger.info("PHASE 2: Training generators")

        obs_np, act_np, dones_np = expert_buffer.arrays()

        league.apply_learning_rates()

        log_metrics({
            "train/gen_lr": champion.gen_lr,
            "train/disc_lr": champion.disc_lr,
        }, step=cycle_num)

        for agent in league.population:
            logger.info(
                "Agent %d (GenLR: %.2e, DiscLR: %.2e) started training",
                agent.id, agent.gen_lr, agent.disc_lr,
            )
            agent.gail.env = agent.env
            num_envs = agent.env.num_envs
            persistent_state = agent.get_states(device, num_envs)
            gen_score, gen_damage_ratio, gen_damage, persistent_state = agent.gail.train(act_np, obs_np, total_timesteps=cfg_steps_per_gen(), persistent_state=persistent_state, expert_dones=dones_np)

            agent.score = 1.0 - abs(gen_damage_ratio - human_damage_ratio)

            # Re-reset env — train() left it in an arbitrary state
            obs, _ = agent.env.reset()
            done = np.zeros(num_envs, dtype=bool)
            persistent_state = (obs, done, persistent_state[2], persistent_state[3], persistent_state[4])
            agent.save_states(*persistent_state)

            logger.info("Agent %d score: %.4f (disc: %.4f, dmg_ratio: %.4f vs human: %.4f) | damage: %.2f", agent.id, agent.score, gen_score, gen_damage_ratio, human_damage_ratio, gen_damage)
            log_metrics({f"train/agent_{agent.id}_gen_damage": gen_damage, f"train/agent_{agent.id}_damage_ratio": gen_damage_ratio}, step=cycle_num)

        # --- PHASE 3: Train champion's boss PPO ---
        champion = league.get_champion()
        logger.info("PHASE 3: Training boss for Champion %d (Score: %.4f)", champion.id, champion.score)

        log_metrics({"gen/best_score": champion.score}, step=cycle_num)

        num_envs = champion.env.num_envs
        args = GAILArgs(num_steps=128, num_envs=num_envs)
        obs, done, gen_lstm_state, boss_lstm_state, disc_lstm_state = champion.get_states(device, num_envs)

        # Pre-allocate tensors
        obs_dim = obs["player"].shape[1]
        p1_obs_buf = torch.empty((num_envs, obs_dim), dtype=torch.float32, device=device)
        p2_obs_buf = torch.empty((num_envs, obs_dim), dtype=torch.float32, device=device)
        done_buf = torch.empty((num_envs,), dtype=torch.float32, device=device)

        boss_global_step = 0
        cycle_reward_sum = 0.0
        boss_metrics_accum = {}
        boss_updates = 0

        while boss_global_step < cfg_steps_per_gen():
            p1_obs_buf.copy_(champion.gail.obs_normalizer.normalize(torch.as_tensor(obs["player"], dtype=torch.float32, device=device)))
            p2_obs_buf.copy_(champion.gail.obs_normalizer.normalize(torch.as_tensor(obs["boss"], dtype=torch.float32, device=device)))
            done_buf.copy_(torch.as_tensor(done))

            with torch.no_grad():
                action1, gen_lstm_state = champion.gail.generator.act(p1_obs_buf, gen_lstm_state, done_buf, inference=True)
            action2, boss_lstm_state = champion.gail.boss.act(p2_obs_buf, boss_lstm_state, done_buf, inference=False)

            obs, rewards, dones, _, _ = champion.env.step({"player": action1.cpu().numpy(), "boss": action2.cpu().numpy()})
            done = dones["__all__"] if isinstance(dones, dict) else dones

            champion.gail.boss.store_reward(rewards["boss"])

            if champion.gail.boss.is_buffer_full():
                cycle_reward_sum += champion.gail.boss.rewards_buf.sum(dim=0).mean().item()
                next_obs = champion.gail.obs_normalizer.normalize(torch.as_tensor(obs["boss"], dtype=torch.float32, device=device))
                next_done = torch.as_tensor(done, dtype=torch.float32, device=device)
                metrics = champion.gail.boss.update(champion.gail.boss_optimizer, args, next_obs, next_done, boss_lstm_state)
                
                for k, v in metrics.items():
                    boss_metrics_accum[k] = boss_metrics_accum.get(k, 0.0) + v
                boss_updates += 1

            boss_global_step += 1

        champion.save_states(obs, done, gen_lstm_state, boss_lstm_state, disc_lstm_state)

        if boss_updates > 0:
            log_metrics({
                "boss/v_loss": boss_metrics_accum.get("v_loss", 0.0) / boss_updates,
                "boss/pg_loss": boss_metrics_accum.get("pg_loss", 0.0) / boss_updates,
                "boss/entropy": boss_metrics_accum.get("entropy_loss", 0.0) / boss_updates,
                "boss/avg_reward": cycle_reward_sum / boss_updates,
                "boss/explained_var": boss_metrics_accum.get("explained_var", 0.0) / boss_updates,
                "boss/approx_kl": boss_metrics_accum.get("approx_kl", 0.0) / boss_updates,
                "boss/clipfrac": boss_metrics_accum.get("clipfrac", 0.0) / boss_updates,
            }, step=cycle_num)

        # --- EVOLVE ---
        league.evolve(cycle_num)
        logger.info("PB2 Evolution Complete! Click CONTINUE on the Level Up screen")

        scores = [a.score for a in league.population]
        log_metrics({
            "pop/mean_score": float(np.mean(scores)),
            "pop/std_score": float(np.std(scores)),
            "pop/max_score": float(np.max(scores)),
            "pop/min_score": float(np.min(scores)),
        }, step=cycle_num)

        log_metrics({"cycle/wall_clock_s": time.time() - cycle_start}, step=cycle_num)
        logger.info("Cycle %d complete in %.1fs", cycle_num, time.time() - cycle_start)

        while True:
            frame = poll_events()
            if frame.quit:
                return

            result = Visuals.end_menu(render_env.engine, frame)

            if result == MenuResult.RESTART:
                break
            elif result == MenuResult.QUIT:
                return

            time.sleep(1.0 / 60.0)

        cycle_num += 1

    end_mlflow()

if __name__ == "__main__":
    main()
