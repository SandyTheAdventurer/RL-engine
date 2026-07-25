import logging
import math
import time
import numpy as np
import torch
from rl.env import EngineEnv, sys_config
from rl.config import setup_logging, init_mlflow, end_mlflow, log_metrics, encode_human_intent
from rl.gail import GAILArgs
from rl.bots import BOTS
from rl.config import num_envs as cfg_num_envs, pop_size as cfg_pop_size, steps_per_gen as cfg_steps_per_gen, num_steps as cfg_num_steps, min_expert_frames, expert_max_matches, expert_max_frames, test_bot
from rl.expert_buffer import ExpertBuffer
from Game import PlayerIntent

import os
# Torch intra-op threads alternate with the engine's OpenMP threads (never
# concurrent), so torch can use half the cores without oversubscribing.
torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))

logger = logging.getLogger("rl.autotest")

BOT = BOTS[test_bot()]


def main():
    setup_logging()
    init_mlflow(project="rl-engine", run_name="pb2_gail_run")

    render_env = EngineEnv(render=False, sys_config=sys_config)
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

        # --- PHASE 1: Collect expert data ---
        logger.info("PHASE 1: BOT vs PPO (Collecting Data)")
        render_env.reset()
        cycle_expert_obs = []
        cycle_expert_actions = []

        boss_lstm_state = (
            torch.zeros(champion.gail.boss.lstm.num_layers, 1, champion.gail.boss.lstm.hidden_size).to(device),
            torch.zeros(champion.gail.boss.lstm.num_layers, 1, champion.gail.boss.lstm.hidden_size).to(device),
        )

        frame_skip = render_env.frame_skip
        total_frames = 0
        bot = BOT()

        render_env.p1.damage_dealt_step = 0.0
        render_env.p1.damage_taken_step = 0.0
        render_env.p2.damage_dealt_step = 0.0
        render_env.p2.damage_taken_step = 0.0

        while not render_env.engine.is_done():
            current_obs = render_env._get_obs()

            current_boss_intent, boss_lstm_state = champion.gail.get_boss_intent(current_obs["boss"], boss_lstm_state, render_env.p2)

            bot_mx, bot_my, bot_fire, bot_dash, bot_spell, bot_aim_x, bot_aim_y, bot_attack = bot.act(current_obs["player"], 1.0 / 60.0 * frame_skip)
            current_bot_intent = PlayerIntent(int(bot_mx), int(bot_my), bool(bot_fire), bool(bot_dash), int(bot_spell), float(bot_aim_x), float(bot_aim_y), bool(bot_attack))
            bot_action_enc = encode_human_intent(current_bot_intent, render_env.p1.px, render_env.p1.py)

            cycle_expert_obs.append(current_obs["player"])
            cycle_expert_actions.append(bot_action_enc)

            for _ in range(frame_skip):
                if render_env.engine.is_done(): break
                render_env.engine.step(current_bot_intent, current_boss_intent, 1.0 / 60.0)
                total_frames += 1

        dx = render_env.p1.px - render_env.p2.px
        dy = render_env.p1.py - render_env.p2.py
        log_metrics({
            "eval/match_duration_s": total_frames / 60.0,
            "eval/bot_health": render_env.p1.health,
            "eval/boss_health": render_env.p2.health,
            "eval/bot_damage_dealt": render_env.p1.damage_dealt_step,
            "eval/bot_damage_taken": render_env.p1.damage_taken_step,
            "eval/boss_damage_dealt": render_env.p2.damage_dealt_step,
            "eval/boss_damage_taken": render_env.p2.damage_taken_step,
            "eval/distance_to_opponent": math.sqrt(dx * dx + dy * dy),
        }, step=cycle_num)

        expert_buffer.add_match(cycle_expert_obs, cycle_expert_actions)

        logger.info("Collected %d frames of expert data (total: %d)", len(cycle_expert_obs), len(expert_buffer))

        if len(expert_buffer) < min_expert_frames():
            logger.warning(
                "Not enough expert data (%d < %d), skipping training this cycle",
                len(expert_buffer), min_expert_frames(),
            )
            cycle_num += 1
            continue


        obs_np, act_np, dones_np = expert_buffer.arrays()

        league.apply_learning_rates()

        log_metrics({
            "train/gen_lr": champion.gen_lr,
            "train/disc_lr": champion.disc_lr,
        }, step=cycle_num)

        # --- PHASE 2: Train all generators (GAIL) ---
        logger.info("PHASE 2: Training generators")

        # One shared judge for the whole population: per-agent discriminator
        # scores are not comparable (a weak discriminator inflates its own
        # agent's score, so evolution would select for bad discriminators).
        ref_disc = champion.gail.discriminator

        for agent in league.population:
            agent.gail.env = agent.env
            num_envs = agent.env.num_envs
            persistent_state = agent.get_states(device, num_envs)
            gen_score, gen_damage, persistent_state = agent.gail.train(act_np, obs_np, total_timesteps=cfg_steps_per_gen(), persistent_state=persistent_state, expert_dones=dones_np)

            agent.score = agent.gail.evaluate_generator(ref_disc)

            # Re-reset env — train()/evaluate_generator() left it in an arbitrary state
            obs, _ = agent.env.reset()
            done = np.zeros(num_envs, dtype=bool)
            persistent_state = (obs, done, persistent_state[2], persistent_state[3], persistent_state[4])
            agent.save_states(*persistent_state)

            logger.info("Agent %d score: %.4f (own-disc: %.4f) | damage: %.2f", agent.id, agent.score, gen_score, gen_damage)
            log_metrics({f"train/agent_{agent.id}_gen_damage": gen_damage}, step=cycle_num)

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

        scores = [a.score for a in league.population]
        log_metrics({
            "pop/mean_score": float(np.mean(scores)),
            "pop/std_score": float(np.std(scores)),
            "pop/max_score": float(np.max(scores)),
            "pop/min_score": float(np.min(scores)),
        }, step=cycle_num)

        log_metrics({"cycle/wall_clock_s": time.time() - cycle_start}, step=cycle_num)
        logger.info("Cycle %d complete in %.1fs", cycle_num, time.time() - cycle_start)

        cycle_num += 1

    end_mlflow()


if __name__ == "__main__":
    main()
