import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

from rl.ppo import PPO
from rl.env import EngineEnv

class Discriminator(nn.Module):
    def __init__(self, input_dim, hidden_dim=256, lstm_hidden=128):
        super().__init__()
        self.pre_lstm = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU()
        )
        self.lstm = nn.LSTM(hidden_dim, lstm_hidden, batch_first=False)
        self.post_lstm = nn.Sequential(
            nn.Linear(lstm_hidden, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid()
        )
        self.optim = optim.Adam(self.parameters(), lr=3e-4)
    
    def forward(self, obs, action, hx=None, cx=None):
        x = torch.cat([obs, action], dim=-1)
        x = self.pre_lstm(x)
        if hx is None:
            out, (new_hx, new_cx) = self.lstm(x)
        else:
            out, (new_hx, new_cx) = self.lstm(x, (hx, cx))
        out = self.post_lstm(out)
        return out, new_hx, new_cx

class GAILArgs:
    def __init__(self, num_steps, num_envs):
        self.num_steps = num_steps
        self.num_envs = num_envs
        self.batch_size = num_steps * num_envs
        self.num_minibatches = 4
        self.update_epochs = 4
        self.gamma = 0.99
        self.gae_lambda = 0.95
        self.clip_coef = 0.2
        self.ent_coef = 0.01
        self.vf_coef = 0.5
        self.max_grad_norm = 0.5
        self.clip_vloss = True
        self.norm_adv = True

class GAIL:
    def __init__(self, env: EngineEnv, boss_dir: str = None, device="cpu"):
        self.env = env
        self.device = device
        
        obs_dim = env.observation_space("player").shape[0]
        action_nvec = env.action_space("player").nvec
        
        self.generator = PPO(obs_dim, action_nvec).to(device)
        self.boss = PPO(obs_dim, action_nvec).to(device)
        
        if boss_dir:
            self.boss.load(boss_dir, device=device)
            
        self.gen_optimizer = optim.Adam(self.generator.parameters(), lr=2.5e-4, eps=1e-5)
        
        disc_input_dim = obs_dim + len(action_nvec)
        self.discriminator = Discriminator(disc_input_dim, 256).to(device)

    def train(self, expert_actions, expert_obs, total_timesteps, num_steps=128):
        num_envs = getattr(self.env, "num_envs", 1)
        args = GAILArgs(num_steps=num_steps, num_envs=num_envs)
        
        self.generator.init_buffers(num_steps, num_envs=num_envs, device=self.device)
        
        expert_obs = torch.as_tensor(expert_obs, dtype=torch.float32, device=self.device)
        expert_actions = torch.as_tensor(expert_actions, dtype=torch.float32, device=self.device)
        
        while expert_obs.shape[0] <= num_steps:
            expert_obs = torch.cat([expert_obs, expert_obs], dim=0)
            expert_actions = torch.cat([expert_actions, expert_actions], dim=0)
            
        loss_fn = nn.BCELoss()

        gen_lstm_state = (
            torch.zeros(self.generator.lstm.num_layers, num_envs, self.generator.lstm.hidden_size).to(self.device),
            torch.zeros(self.generator.lstm.num_layers, num_envs, self.generator.lstm.hidden_size).to(self.device)
        )
        boss_lstm_state = (
            torch.zeros(self.boss.lstm.num_layers, num_envs, self.boss.lstm.hidden_size).to(self.device),
            torch.zeros(self.boss.lstm.num_layers, num_envs, self.boss.lstm.hidden_size).to(self.device)
        )
        disc_lstm_state = (
            torch.zeros(1, num_envs, 128).to(self.device),
            torch.zeros(1, num_envs, 128).to(self.device)
        )

        obs, _ = self.env.reset()
        done = np.zeros(num_envs, dtype=bool)
        
        global_step = 0
        
        while global_step < total_timesteps:
            p1_obs_tensor = torch.tensor(obs["player"], dtype=torch.float32).to(self.device)
            if p1_obs_tensor.dim() == 1: p1_obs_tensor = p1_obs_tensor.unsqueeze(0)
            
            p2_obs_tensor = torch.tensor(obs["boss"], dtype=torch.float32).to(self.device)
            if p2_obs_tensor.dim() == 1: p2_obs_tensor = p2_obs_tensor.unsqueeze(0)
            
            done_val = done["__all__"] if isinstance(done, dict) and "__all__" in done else done
            if isinstance(done_val, bool) or isinstance(done_val, np.bool_): done_val = [done_val]
            done_tensor = torch.tensor(done_val, dtype=torch.float32).to(self.device)

            action1, gen_lstm_state = self.generator.act(p1_obs_tensor, gen_lstm_state, done_tensor, inference=False)
            action2, boss_lstm_state = self.boss.act(p2_obs_tensor, boss_lstm_state, done_tensor, inference=True)
            
            a1_numpy = action1.cpu().numpy()
            a2_numpy = action2.cpu().numpy()
            if num_envs == 1:
                a1_numpy = a1_numpy[0]
                a2_numpy = a2_numpy[0]
            
            next_obs, rewards, dones, truncs, infos = self.env.step({"player": a1_numpy, "boss": a2_numpy})
            done = dones["__all__"]
            
            with torch.no_grad():
                gen_pred, disc_hx, disc_cx = self.discriminator(
                    p1_obs_tensor.unsqueeze(0), 
                    action1.float().unsqueeze(0),
                    disc_lstm_state[0], disc_lstm_state[1]
                )
                disc_lstm_state = (disc_hx, disc_cx)
                
                gail_reward = -torch.log(1.0 - gen_pred.squeeze() + 1e-8)
            
            self.generator.store_reward(gail_reward)

            obs = next_obs
            
            if isinstance(done, dict):
                is_any_done = done["__all__"]
            else:
                is_any_done = done.any() if isinstance(done, np.ndarray) else done
                
            if is_any_done and num_envs == 1:
                obs, _ = self.env.reset()
                disc_lstm_state = (
                    torch.zeros(1, num_envs, 128).to(self.device),
                    torch.zeros(1, num_envs, 128).to(self.device)
                )
                
            global_step += 1
            
            if self.generator.is_buffer_full():
                start_indices = torch.randint(0, expert_obs.shape[0] - num_steps, (num_envs,))
                batch_expert_obs = torch.stack([expert_obs[i : i + num_steps] for i in start_indices], dim=1)
                batch_expert_actions = torch.stack([expert_actions[i : i + num_steps] for i in start_indices], dim=1)
                batch_expert_labels = torch.ones(num_steps, num_envs, 1, device=self.device)
                
                batch_gen_obs = self.generator.obs_buf
                batch_gen_actions = self.generator.actions_buf
                batch_gen_labels = torch.zeros(num_steps, num_envs, 1, device=self.device)
                
                for _ in range(args.update_epochs):
                    expert_preds, _, _ = self.discriminator(batch_expert_obs, batch_expert_actions)
                    gen_preds, _, _ = self.discriminator(batch_gen_obs, batch_gen_actions)
                    
                    expert_loss = loss_fn(expert_preds, batch_expert_labels)
                    gen_loss = loss_fn(gen_preds, batch_gen_labels)
                    disc_loss = expert_loss + gen_loss
                    
                    self.discriminator.optim.zero_grad()
                    disc_loss.backward()
                    self.discriminator.optim.step()

                next_obs_tensor = torch.tensor(obs["player"], dtype=torch.float32).to(self.device)
                if next_obs_tensor.dim() == 1: next_obs_tensor = next_obs_tensor.unsqueeze(0)
                
                metrics = self.generator.update(self.gen_optimizer, args, next_obs_tensor, done_tensor, gen_lstm_state)
                
                exp_score = expert_preds.mean().item()
                gen_score = gen_preds.mean().item()
                print(f"Step {global_step} | Disc Loss: {disc_loss.item():.4f} (Exp: {exp_score:.2f}, Gen: {gen_score:.2f}) | PPO v_loss: {metrics['v_loss']:.4f}")