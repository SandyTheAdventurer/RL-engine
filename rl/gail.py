import logging
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

from rl.ppo import PPO, layer_init, evaluate_rnn_sequence
from rl.env import EngineEnv
from rl.config import disc_lr, gen_lr, num_steps as cfg_num_steps, num_minibatches, update_epochs, gamma, gae_lambda, clip_coef, ent_coef, vf_coef, max_grad_norm, reward_alpha, label_smoothing, disc_grad_norm, RunningMeanStd

logger = logging.getLogger("rl.gail")

class Discriminator(nn.Module):
    def __init__(self, input_dim, hidden_dim=512, lstm_hidden=256):
        super().__init__()
        self.pre_lstm = nn.Sequential(
            layer_init(nn.Linear(input_dim, hidden_dim)),
            nn.ReLU(),
            layer_init(nn.Linear(hidden_dim, hidden_dim)),
            nn.ReLU()
        )
        self.lstm = nn.LSTM(hidden_dim, lstm_hidden, batch_first=False)
        self.post_lstm = nn.Sequential(
            layer_init(nn.Linear(lstm_hidden, hidden_dim)),
            nn.ReLU(),
            layer_init(nn.Linear(hidden_dim, 1)),
            nn.Sigmoid()
        )
        self.optim = optim.Adam(self.parameters(), lr=disc_lr())
    
    def forward(self, obs, action, hx=None, cx=None, done=None):
        x = torch.cat([obs, action], dim=-1)
        x = self.pre_lstm(x)
        
        is_batch_only = (x.dim() == 2)
        if is_batch_only:
            x = x.unsqueeze(0)
            if done is not None and done.dim() == 1:
                done = done.unsqueeze(0)
                
        batch_size = x.shape[1]
        
        if hx is None:
            hx = torch.zeros(self.lstm.num_layers, batch_size, self.lstm.hidden_size, device=x.device)
            cx = torch.zeros(self.lstm.num_layers, batch_size, self.lstm.hidden_size, device=x.device)

        if done is not None:
            if done.dim() == 1:
                done = done.view(1, -1)
            out, (hx, cx) = evaluate_rnn_sequence(self.lstm, x, (hx, cx), done)
        else:
            out, (hx, cx) = self.lstm(x, (hx, cx))

        out = self.post_lstm(out)
        
        if is_batch_only:
            out = out.squeeze(0)
            
        return out, hx, cx

class GAILArgs:
    def __init__(self, num_steps, num_envs, ent_coef_val=None):
        self.num_steps = num_steps
        self.num_envs = num_envs
        self.batch_size = num_steps * num_envs
        self.num_minibatches = num_minibatches()
        self.update_epochs = update_epochs()
        self.gamma = gamma()
        self.gae_lambda = gae_lambda()
        self.clip_coef = clip_coef()
        self.ent_coef = ent_coef_val if ent_coef_val is not None else ent_coef()
        self.vf_coef = vf_coef()
        self.max_grad_norm = max_grad_norm()
        self.clip_vloss = True
        self.norm_adv = True

class GAIL:
    def __init__(self, env: EngineEnv, boss_dir: str = None, device="cpu"):
        self.env = env
        self.device = device
        
        obs_dim = env.observation_space("player").shape[0]
        self.action_nvec = env.action_space("player").nvec
        self.action_dim = sum(self.action_nvec)
        self.action_offsets = torch.tensor(np.cumsum([0] + list(self.action_nvec[:-1])), device=device)
        
        self.generator = PPO(obs_dim, self.action_nvec).to(device)
        # Increase BOSS PPO neural network power (deeper MLP, wider layers, and stacked LSTMs)
        self.boss = PPO(obs_dim, self.action_nvec, hidden_dim=1024, lstm_hidden=512, num_mlp_layers=4, lstm_layers=2).to(device)
        
        if boss_dir:
            self.boss.load(boss_dir, device=device)
            
        self.gen_optimizer = optim.Adam(self.generator.parameters(), lr=gen_lr(), eps=1e-5)
        self.boss_optimizer = optim.Adam(self.boss.parameters(), lr=gen_lr(), eps=1e-5)
        
        num_envs = getattr(self.env, "num_envs", 1)
        self.boss.init_buffers(128, num_envs=num_envs, device=device)
        
        disc_input_dim = obs_dim + self.action_dim
        self.discriminator = Discriminator(disc_input_dim, 512).to(device)

        self.obs_normalizer = RunningMeanStd(shape=(obs_dim,), device=device)
        self.reward_alpha = reward_alpha()
        self.ent_coef = ent_coef()

    def _one_hot_encode(self, actions, out_buffer=None):
        if out_buffer is None:
            out_buffer = torch.zeros(actions.shape[:-1] + (self.action_dim,), dtype=torch.float32, device=actions.device)
        else:
            out_buffer.zero_()
            
        flat_actions = (actions.long() + self.action_offsets).view(-1, actions.shape[-1])
        out_buffer.view(-1, self.action_dim).scatter_(1, flat_actions, 1.0)
        return out_buffer

    def get_boss_intent(self, obs, lstm_state, player, done=False):
        obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0).to(self.device)
        obs_tensor = self.obs_normalizer.normalize(obs_tensor)
        done_tensor = torch.tensor([done], dtype=torch.float32).to(self.device)
        action_tensor, new_lstm_state = self.boss.act(obs_tensor, lstm_state, done_tensor, inference=True)
        action = action_tensor.cpu().numpy()[0]
        intent = self.env._decode_action(action, player)
        return intent, new_lstm_state

    def save_normalizer(self):
        return self.obs_normalizer.state_dict()

    def load_normalizer(self, d):
        self.obs_normalizer.load_state_dict(d)

    def train(self, expert_actions, expert_obs, total_timesteps, persistent_state, num_steps=None, expert_dones=None):
        if num_steps is None:
            num_steps = cfg_num_steps()

        num_envs = getattr(self.env, "num_envs", 1)

        # Adapt num_steps to available expert data (prevents silent 0-score returns)
        if len(expert_obs) == 0:
            logger.warning("No expert data collected — skipping training")
            return 0.0, 0.0, persistent_state
        if len(expert_obs) < num_steps:
            logger.warning("Expert data shorter than num_steps (%d < %d), adapting", len(expert_obs), num_steps)
            num_steps = max(32, len(expert_obs))

        args = GAILArgs(num_steps=num_steps, num_envs=num_envs, ent_coef_val=getattr(self, "ent_coef", None))
        
        self.generator.init_buffers(num_steps, num_envs=num_envs, device=self.device)
        
        if total_timesteps < num_steps:
            return 0.0, 0.0, persistent_state
            
        expert_obs = torch.as_tensor(expert_obs, dtype=torch.float32, device=self.device)
        expert_actions = torch.as_tensor(expert_actions, dtype=torch.float32, device=self.device)
        if expert_dones is not None:
            expert_dones = torch.as_tensor(expert_dones, dtype=torch.float32, device=self.device)
            
        loss_fn = nn.BCELoss()
        _label_smooth = label_smoothing()
        _reward_alpha = getattr(self, "reward_alpha", reward_alpha())

        obs, done, gen_lstm_state, boss_lstm_state, disc_lstm_state = persistent_state

        
        # Pre-allocate tensors for hot loop
        p1_obs_tensor = torch.empty((num_envs, expert_obs.shape[1]), dtype=torch.float32, device=self.device)
        p2_obs_tensor = torch.empty((num_envs, expert_obs.shape[1]), dtype=torch.float32, device=self.device)
        done_tensor = torch.empty((num_envs,), dtype=torch.float32, device=self.device)
        game_reward_buf = torch.empty((num_envs,), dtype=torch.float32, device=self.device)
        single_env = num_envs == 1
        
        # Pre-allocate one-hot buffers
        encoded_action_buf = torch.empty((1, num_envs, self.action_dim), dtype=torch.float32, device=self.device)
        encoded_expert_buf = torch.empty((num_steps, num_envs, self.action_dim), dtype=torch.float32, device=self.device)
        encoded_gen_buf = torch.empty((num_steps, num_envs, self.action_dim), dtype=torch.float32, device=self.device)
        
        global_step = 0
        gen_score = 0.0
        gen_score_history = []
        total_gen_damage_dealt = 0.0
        total_gen_damage_taken = 0.0
        total_episodes = 0.0
        disc_initial_lstm_state = None
        
        while global_step < total_timesteps:
            if self.generator.step_idx == 0:
                disc_initial_lstm_state = (disc_lstm_state[0].clone(), disc_lstm_state[1].clone())
                
            raw_p1 = torch.as_tensor(obs["player"], dtype=torch.float32, device=self.device)
            raw_p2 = torch.as_tensor(obs["boss"], dtype=torch.float32, device=self.device)
            p1_obs_tensor.copy_(self.obs_normalizer.update_and_normalize(raw_p1))
            p2_obs_tensor.copy_(self.obs_normalizer.update_and_normalize(raw_p2))
            done_tensor.copy_(torch.as_tensor(done))

            action1, gen_lstm_state = self.generator.act(p1_obs_tensor, gen_lstm_state, done_tensor, inference=False)
            action2, boss_lstm_state = self.boss.act(p2_obs_tensor, boss_lstm_state, done_tensor, inference=True)
            
            a1_numpy = action1.cpu().numpy()
            a2_numpy = action2.cpu().numpy()
            if single_env:
                a1_numpy = a1_numpy[0]
                a2_numpy = a2_numpy[0]
            
            next_obs, rewards, dones, truncs, infos = self.env.step({"player": a1_numpy, "boss": a2_numpy})
            done = dones["__all__"] if isinstance(dones, dict) else dones
            
            if isinstance(done, np.ndarray) or isinstance(done, torch.Tensor):
                total_episodes += float(np.sum(done))
            elif done:
                total_episodes += 1.0
            
            if "player" in infos and "damage_dealt" in infos["player"]:
                p_dmg = infos["player"]["damage_dealt"]
                if isinstance(p_dmg, np.ndarray) or isinstance(p_dmg, torch.Tensor):
                    total_gen_damage_dealt += float(np.sum(p_dmg))
                else:
                    total_gen_damage_dealt += float(p_dmg)
            if "player" in infos and "damage_taken" in infos["player"]:
                p_dmg_taken = infos["player"]["damage_taken"]
                if isinstance(p_dmg_taken, np.ndarray) or isinstance(p_dmg_taken, torch.Tensor):
                    total_gen_damage_taken += float(np.sum(p_dmg_taken))
                else:
                    total_gen_damage_taken += float(p_dmg_taken)
            
            with torch.no_grad():
                encoded_action = self._one_hot_encode(action1.unsqueeze(0), out_buffer=encoded_action_buf)
                gen_pred, disc_hx, disc_cx = self.discriminator(
                    p1_obs_tensor.unsqueeze(0), 
                    encoded_action,
                    disc_lstm_state[0], disc_lstm_state[1],
                    done=done_tensor
                )
                disc_lstm_state = (disc_hx, disc_cx)
                
                d_prob = gen_pred.squeeze()
                # Symmetrical logit reward formulation (log(D) - log(1 - D)) avoids gradient saturation
                gail_reward = torch.log(d_prob + 1e-8) - torch.log(1.0 - d_prob + 1e-8)
                player_reward = rewards["player"] if isinstance(rewards, dict) else rewards
                game_reward_buf.copy_(torch.as_tensor(player_reward))
                gail_reward = _reward_alpha * gail_reward + (1.0 - _reward_alpha) * game_reward_buf
            
            self.generator.store_reward(gail_reward)

            obs = next_obs
            
            if single_env and done:
                obs, _ = self.env.reset()
                disc_lstm_state = (
                    torch.zeros(1, num_envs, self.discriminator.lstm.hidden_size).to(self.device),
                    torch.zeros(1, num_envs, self.discriminator.lstm.hidden_size).to(self.device)
                )
                
            global_step += 1
            
            if self.generator.is_buffer_full():
                high = max(1, expert_obs.shape[0] - num_steps + 1)
                start_indices = torch.randint(0, high, (num_envs,))
                batch_expert_obs = torch.stack([expert_obs[i : i + num_steps] for i in start_indices], dim=1)
                batch_expert_obs = self.obs_normalizer.normalize(batch_expert_obs)
                batch_expert_actions = torch.stack([expert_actions[i : i + num_steps] for i in start_indices], dim=1)
                batch_expert_labels = torch.full((num_steps, num_envs, 1), 1.0 - _label_smooth, device=self.device)
                
                batch_gen_obs = self.generator.obs_buf
                batch_gen_actions = self.generator.actions_buf
                batch_gen_labels = torch.full((num_steps, num_envs, 1), _label_smooth, device=self.device)
                
                batch_gen_dones = self.generator.dones_buf
                if expert_dones is not None:
                    batch_expert_dones = torch.stack([expert_dones[i : i + num_steps] for i in start_indices], dim=1)
                else:
                    batch_expert_dones = torch.zeros_like(batch_gen_dones)
                
                encoded_expert_actions = self._one_hot_encode(batch_expert_actions, out_buffer=encoded_expert_buf)
                encoded_gen_actions = self._one_hot_encode(batch_gen_actions, out_buffer=encoded_gen_buf)
                
                for _ in range(args.update_epochs):
                    expert_preds, _, _ = self.discriminator(batch_expert_obs, encoded_expert_actions, done=batch_expert_dones)
                    gen_preds, _, _ = self.discriminator(batch_gen_obs, encoded_gen_actions, 
                                                         hx=disc_initial_lstm_state[0], 
                                                         cx=disc_initial_lstm_state[1], 
                                                         done=batch_gen_dones)
                    
                    expert_loss = loss_fn(expert_preds, batch_expert_labels)
                    gen_loss = loss_fn(gen_preds, batch_gen_labels)
                    disc_loss = expert_loss + gen_loss
                    
                    self.discriminator.optim.zero_grad()
                    disc_loss.backward()
                    nn.utils.clip_grad_norm_(self.discriminator.parameters(), disc_grad_norm())
                    self.discriminator.optim.step()

                next_obs_tensor = self.obs_normalizer.normalize(
                    torch.tensor(obs["player"], dtype=torch.float32, device=self.device)
                )
                if next_obs_tensor.dim() == 1: next_obs_tensor = next_obs_tensor.unsqueeze(0)

                next_done_val = done["__all__"] if isinstance(done, dict) and "__all__" in done else done
                if isinstance(next_done_val, bool) or isinstance(next_done_val, np.bool_): next_done_val = [next_done_val]
                next_done_tensor = torch.tensor(next_done_val, dtype=torch.float32).to(self.device)

                metrics = self.generator.update(self.gen_optimizer, args, next_obs_tensor, next_done_tensor, gen_lstm_state)
                
                exp_score = expert_preds.mean().item()
                gen_score = gen_preds.mean().item()
                gen_score_history.append(gen_score)
                logger.debug("Step %d | Disc Loss: %.4f (Exp: %.2f, Gen: %.2f) | PPO v_loss: %.4f | EV: %.4f", global_step, disc_loss.item(), exp_score, gen_score, metrics['v_loss'], metrics.get('explained_var', 0.0))

        gen_score = np.mean(gen_score_history) if len(gen_score_history) > 0 else 0.0
        episodes_completed = max(total_episodes, 1.0)
        avg_gen_damage = total_gen_damage_dealt / episodes_completed
        gen_damage_ratio = total_gen_damage_dealt / (total_gen_damage_dealt + total_gen_damage_taken + 1e-8)
        return gen_score, gen_damage_ratio, avg_gen_damage, (obs, done, gen_lstm_state, boss_lstm_state, disc_lstm_state)