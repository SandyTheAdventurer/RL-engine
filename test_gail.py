import numpy as np
import torch
from rl.env import EngineEnv, sys_config
from rl.vec_env import MultiEngineEnv
from rl.gail import GAIL, GAILArgs
from build.Game import get_human_intent, poll_events, MenuResult, Visuals
import time
import copy
import random
import os
import concurrent.futures

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import torch
torch.set_num_threads(1)

NUM_ENVS = 4
POP_SIZE = 4
STEPS_PER_GEN = 256

def encode_human_intent(intent, player):
    mx = intent.mx + 1
    my = intent.my + 1
    fire = 1 if intent.fire else 0
    dash = 1 if intent.dash else 0
    spell = 1 if intent.selected_spell else 0
    
    dx = intent.aim_x - player.px
    dy = intent.aim_y - player.py
    angle = np.arctan2(dy, dx)
    if angle < 0:
        angle += 2 * np.pi
    
    aim_bin = int(round(angle / (2 * np.pi / 16)))
    if aim_bin >= 16:
        aim_bin = 15 
        
    attack = 1 if intent.attack else 0
    
    return np.array([mx, my, fire, dash, spell, aim_bin, attack], dtype=np.float32)

def play_and_collect(env, gail_system):
    print("\n--- PHASE 1: Human vs PPO (Collecting Data) ---")
    env.reset()
    expert_obs = []
    expert_actions = []
    
    boss_lstm_state = (
        torch.zeros(gail_system.boss.lstm.num_layers, 1, gail_system.boss.lstm.hidden_size).to(gail_system.device),
        torch.zeros(gail_system.boss.lstm.num_layers, 1, gail_system.boss.lstm.hidden_size).to(gail_system.device)
    )
    
    clock = time.time()
    frames_since_decision = 0
    frame_skip = env.frame_skip
    
    agg_mx, agg_my = 0, 0
    agg_fire, agg_dash, agg_spell, agg_attack = False, False, False, False
    agg_aim_x, agg_aim_y = 0.0, 0.0
    
    current_obs = None
    current_boss_intent = None
    
    while not env.engine.is_done():
        frame_input = poll_events()
        if frame_input.quit:
            return None, None
            
        human_intent = get_human_intent(frame_input)
        
        if human_intent.mx != 0: agg_mx = human_intent.mx
        if human_intent.my != 0: agg_my = human_intent.my
        agg_fire = agg_fire or human_intent.fire
        agg_dash = agg_dash or human_intent.dash
        agg_spell = agg_spell or (human_intent.selected_spell > 0)
        agg_attack = agg_attack or human_intent.attack
        agg_aim_x = human_intent.aim_x
        agg_aim_y = human_intent.aim_y
        
        if frames_since_decision == 0:
            current_obs = env._get_obs()
            
            p2_obs_tensor = torch.tensor(current_obs["boss"], dtype=torch.float32).unsqueeze(0).to(gail_system.device)
            done_tensor = torch.tensor([False], dtype=torch.float32).to(gail_system.device)
            boss_action_tensor, boss_lstm_state = gail_system.boss.act(p2_obs_tensor, boss_lstm_state, done_tensor, inference=True)
            boss_action = boss_action_tensor.cpu().numpy()[0]
            
            current_boss_intent = env._decode_action(boss_action, env.p2)
            
        env.engine.step(human_intent, current_boss_intent, 1.0 / 60.0)
        env.engine.render()
        Visuals.hud(env.engine)
        env.engine.present()
        
        frames_since_decision += 1
        
        if frames_since_decision >= frame_skip:
            from build.Game import PlayerIntent
            fake_intent = PlayerIntent(
                int(agg_mx), int(agg_my), bool(agg_fire), bool(agg_dash), 
                int(agg_spell), float(agg_aim_x), float(agg_aim_y), bool(agg_attack)
            )
            human_action = encode_human_intent(fake_intent, env.p1)
            
            expert_obs.append(current_obs["player"])
            expert_actions.append(human_action)
            
            frames_since_decision = 0
            agg_mx, agg_my = 0, 0
            agg_fire, agg_dash, agg_spell, agg_attack = False, False, False, False
            
        target = clock + (1.0 / 60.0)
        now = time.time()
        if now < target:
            time.sleep(target - now)
        clock = target
        
    print(f"Collected {len(expert_obs)} frames of expert data!")
    return np.array(expert_obs), np.array(expert_actions)

def create_vec_env():
    return MultiEngineEnv(num_envs=NUM_ENVS, frame_skip=4)

def train_boss_vectorized(env, gail_system, total_timesteps, num_steps=128):
    num_envs = env.num_envs
    args = GAILArgs(num_steps=num_steps, num_envs=num_envs)
    gail_system.boss.init_buffers(num_steps, num_envs=num_envs, device=gail_system.device)
    
    boss_optimizer = torch.optim.Adam(gail_system.boss.parameters(), lr=gail_system.boss_lr if hasattr(gail_system, 'boss_lr') else 2.5e-4, eps=1e-5)
    
    gen_lstm_state = (
        torch.zeros(gail_system.generator.lstm.num_layers, num_envs, gail_system.generator.lstm.hidden_size).to(gail_system.device),
        torch.zeros(gail_system.generator.lstm.num_layers, num_envs, gail_system.generator.lstm.hidden_size).to(gail_system.device)
    )
    boss_lstm_state = (
        torch.zeros(gail_system.boss.lstm.num_layers, num_envs, gail_system.boss.lstm.hidden_size).to(gail_system.device),
        torch.zeros(gail_system.boss.lstm.num_layers, num_envs, gail_system.boss.lstm.hidden_size).to(gail_system.device)
    )
    
    obs, _ = env.reset()
    done = np.zeros(num_envs, dtype=bool)
    global_step = 0
    final_avg_reward = 0.0
    
    while global_step < total_timesteps:
        p1_obs = torch.tensor(obs["player"], dtype=torch.float32).to(gail_system.device)
        p2_obs = torch.tensor(obs["boss"], dtype=torch.float32).to(gail_system.device)
        done_val = done["__all__"] if isinstance(done, dict) and "__all__" in done else done
        if isinstance(done_val, bool) or isinstance(done_val, np.bool_): done_val = [done_val]
        done_tensor = torch.tensor(done_val, dtype=torch.float32).to(gail_system.device)
        
        with torch.no_grad():
            action1, gen_lstm_state = gail_system.generator.act(p1_obs, gen_lstm_state, done_tensor, inference=True)
        action2, boss_lstm_state = gail_system.boss.act(p2_obs, boss_lstm_state, done_tensor, inference=False)
        
        obs, rewards, dones, _, _ = env.step({"player": action1.cpu().numpy(), "boss": action2.cpu().numpy()})
        done = dones["__all__"]
        
        gail_system.boss.rewards_buf[gail_system.boss.step_idx] = torch.tensor(rewards["boss"], dtype=torch.float32).to(gail_system.device)
        gail_system.boss.step_idx += 1
        
        if gail_system.boss.is_buffer_full():
            final_avg_reward = gail_system.boss.rewards_buf.mean().item()
            next_obs = torch.tensor(obs["boss"], dtype=torch.float32).to(gail_system.device)
            next_done = torch.tensor(done if not isinstance(done, dict) else done["__all__"], dtype=torch.float32).to(gail_system.device)
            metrics = gail_system.boss.update(boss_optimizer, args, next_obs, next_done, boss_lstm_state)
            print(f"Boss Step {global_step} | Avg Reward: {final_avg_reward:.4f} | PPO v_loss: {metrics['v_loss']:.4f}")
            
        global_step += 1
        
    return final_avg_reward

def main():
    render_env = EngineEnv(render=True, sys_config=sys_config)
    Visuals.init(render_env.engine, render_env.p1, render_env.p2)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    from rl.pb2_league import PB2League
    league = PB2League(pop_size=POP_SIZE, num_envs=NUM_ENVS, device=device)
    
    try:
        global_expert_obs = list(np.load("expert_obs.npy"))
        global_expert_actions = list(np.load("expert_actions.npy"))
        print(f"Loaded {len(global_expert_obs)} past expert frames!")
    except FileNotFoundError:
        global_expert_obs = []
        global_expert_actions = []

    cycle_num = 1
    while True:
        champion = league.get_champion()
        champion.gail.env = render_env
        
        print(f"\n========== CYCLE {cycle_num} ==========")
        print(f"Challenging Champion {champion.id} (Score: {champion.score:.2f}, GenLR: {champion.gen_lr:.2e}, DiscLR: {champion.disc_lr:.2e})")
        
        start_play = False
        while True:
            frame = poll_events()
            if frame.quit: return
            result = Visuals.start_menu(render_env.engine, frame)
            if result == MenuResult.PLAY:
                start_play = True
                break
            elif result == MenuResult.QUIT: return
                
        if not start_play: break
            
        expert_obs, expert_actions = play_and_collect(render_env, champion.gail)
        if expert_obs is None: break
            
        global_expert_obs.extend(expert_obs)
        global_expert_actions.extend(expert_actions)
        np.save("expert_obs.npy", np.array(global_expert_obs))
        np.save("expert_actions.npy", np.array(global_expert_actions))
        
        print("\n--- PHASE 2 & 3: EVOLVING THE POPULATION ---")
        print("Training in background. You can move your mouse on the Level Up screen, but must wait to Continue...")
        
        obs_np = np.array(global_expert_obs)
        act_np = np.array(global_expert_actions)
        
        league.apply_learning_rates()
        
        def train_single_agent(agent):
            print(f"-> Agent {agent.id} (GenLR: {agent.gen_lr:.2e}, DiscLR: {agent.disc_lr:.2e}) started training...")
            agent.gail.env = agent.env
            agent.gail.train(act_np, obs_np, total_timesteps=STEPS_PER_GEN)
            agent.score = train_boss_vectorized(agent.env, agent.gail, total_timesteps=STEPS_PER_GEN)
            print(f"-> Agent {agent.id} Finished! Boss Score: {agent.score:.4f}")
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=POP_SIZE) as executor:
            futures = [executor.submit(train_single_agent, agent) for agent in league.population]
            
            training_done = False
            
            while True:
                frame = poll_events()
                if frame.quit: return
                
                if not training_done and all(f.done() for f in futures):
                    training_done = True
                    league.evolve()
                    print("\nPB2 Evolution Complete! You may now click CONTINUE on the Level Up screen!")
                
                result = Visuals.end_menu(render_env.engine, frame)
                
                if result == MenuResult.RESTART:
                    if training_done:
                        break
                    else:
                        print("Still training... please wait!")
                        
                elif result == MenuResult.QUIT:
                    return
                    
                time.sleep(1.0 / 60.0)
                
        cycle_num += 1

if __name__ == "__main__":
    main()
