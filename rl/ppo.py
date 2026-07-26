import numpy as np
import torch
import torch.nn as nn
from torch.distributions.categorical import Categorical

from line_profiler import profile

def layer_init(layer, std=np.sqrt(2), bias_const=0.0):
    torch.nn.init.orthogonal_(layer.weight, std)
    torch.nn.init.constant_(layer.bias, bias_const)
    return layer

class PPO(nn.Module):
    def __init__(self, obs_dim, action_nvec):
        super().__init__()
        
        self.network = nn.Sequential(
            layer_init(nn.Linear(obs_dim, 512)),
            nn.ReLU(),
            layer_init(nn.Linear(512, 512)),
            nn.ReLU(),
            layer_init(nn.Linear(512, 512)),
            nn.ReLU(),
        )
        
        self.lstm = nn.LSTM(512, 256)
        for name, param in self.lstm.named_parameters():
            if "bias" in name:
                nn.init.constant_(param, 0)
            elif "weight" in name:
                nn.init.orthogonal_(param, 1.0)
                
        self.action_nvec = tuple(action_nvec)
        self.actor = layer_init(nn.Linear(256, sum(action_nvec)), std=0.01)
        self.critic = layer_init(nn.Linear(256, 1), std=1)
        
        self.step_idx = 0
        self.num_steps = 0
        self.num_envs = 0

        self.device = "cpu" if not torch.cuda.is_available() else "cuda"
        
    def init_buffers(self, num_steps, num_envs, device="cpu"):
        self.num_steps = num_steps
        self.num_envs = num_envs
        self.device = device
        self.step_idx = 0
        
        self.obs_buf = torch.zeros((num_steps, num_envs, self.network[0].in_features)).to(device)
        self.actions_buf = torch.zeros((num_steps, num_envs, len(self.action_nvec))).to(device)
        self.logprobs_buf = torch.zeros((num_steps, num_envs)).to(device)
        self.rewards_buf = torch.zeros((num_steps, num_envs)).to(device)
        self.dones_buf = torch.zeros((num_steps, num_envs)).to(device)
        self.values_buf = torch.zeros((num_steps, num_envs)).to(device)
        
        self.initial_lstm_state = None

    @profile
    def get_states(self, x, lstm_state, done):
        hidden = self.network(x)
        
        batch_size = lstm_state[0].shape[1]
        hidden = hidden.reshape((-1, batch_size, self.lstm.input_size))
        done = done.reshape((-1, batch_size))
        new_hidden = []
        for h, d in zip(hidden, done):
            h, lstm_state = self.lstm(
                h.unsqueeze(0),
                (
                    (1.0 - d).view(1, -1, 1) * lstm_state[0],
                    (1.0 - d).view(1, -1, 1) * lstm_state[1],
                ),
            )
            new_hidden += [h]
        new_hidden = torch.flatten(torch.cat(new_hidden), 0, 1)
        return new_hidden, lstm_state

    @profile
    def get_value(self, x, lstm_state, done):
        hidden, _ = self.get_states(x, lstm_state, done)
        return self.critic(hidden)

    @profile
    def get_action_and_value(self, x, lstm_state, done, action=None):
        hidden, lstm_state = self.get_states(x, lstm_state, done)
        logits = self.actor(hidden)
        
        split_logits = torch.split(logits, self.action_nvec, dim=-1)
        multi_categoricals = [Categorical(logits=logits_i) for logits_i in split_logits]
        
        if action is None:
            action = torch.stack([categorical.sample() for categorical in multi_categoricals], dim=-1)
            
        log_prob = torch.stack([categorical.log_prob(action[..., i]) for i, categorical in enumerate(multi_categoricals)], dim=-1).sum(dim=-1)
        entropy = torch.stack([categorical.entropy() for categorical in multi_categoricals], dim=-1).sum(dim=-1)
            
        return action, log_prob, entropy, self.critic(hidden), lstm_state

    @profile
    def act(self, obs, lstm_state, done, inference=False):
        obs = torch.as_tensor(obs, dtype=torch.float32, device=self.device)
        done = torch.as_tensor(done, dtype=torch.float32, device=self.device)
        
        if inference:
            with torch.no_grad():
                action, log_prob, entropy, value, next_lstm_state = self.get_action_and_value(obs, lstm_state, done)
            return action, next_lstm_state
            
        if self.step_idx == 0:
            self.initial_lstm_state = (lstm_state[0].clone(), lstm_state[1].clone())
            
        with torch.no_grad():
            action, log_prob, entropy, value, next_lstm_state = self.get_action_and_value(obs, lstm_state, done)
            
        self.obs_buf[self.step_idx] = obs
        self.actions_buf[self.step_idx] = action
        self.logprobs_buf[self.step_idx] = log_prob
        self.values_buf[self.step_idx] = value.flatten()
        self.dones_buf[self.step_idx] = done
        
        self.step_idx += 1
        return action, next_lstm_state
        
    def store_reward(self, reward):
        """Call this after stepping the environment to store the reward for the current transition"""
        if self.step_idx > 0:
            self.rewards_buf[self.step_idx - 1] = torch.as_tensor(reward, dtype=torch.float32, device=self.device)
            
    def is_buffer_full(self):
        return self.step_idx >= self.num_steps
        
    @profile
    def update(self, optimizer, args, next_obs, next_done, next_lstm_state):
        assert self.is_buffer_full(), "Buffer is not full yet! Cannot update."
        
        next_obs = torch.as_tensor(next_obs, dtype=torch.float32, device=self.device)
        next_done = torch.as_tensor(next_done, dtype=torch.float32, device=self.device)
        
        with torch.no_grad():
            next_value = self.get_value(next_obs, next_lstm_state, next_done).view(-1)
            advantages = torch.zeros_like(self.rewards_buf).to(self.device)
            nextnonterminal = torch.cat([1.0 - self.dones_buf[1:], (1.0 - next_done).unsqueeze(0)])
            nextvalues = torch.cat([self.values_buf[1:], next_value.unsqueeze(0)])
            deltas = self.rewards_buf + args.gamma * nextvalues * nextnonterminal - self.values_buf
            
            lastgaelam = 0
            for t in reversed(range(args.num_steps)):
                advantages[t] = lastgaelam = deltas[t] + args.gamma * args.gae_lambda * nextnonterminal[t] * lastgaelam
            returns = advantages + self.values_buf

        b_obs = self.obs_buf.reshape((-1, self.obs_buf.shape[-1]))
        b_logprobs = self.logprobs_buf.reshape(-1)
        b_actions = self.actions_buf.reshape((-1, self.actions_buf.shape[-1]))
        b_dones = self.dones_buf.reshape(-1)
        b_advantages = advantages.reshape(-1)
        b_returns = returns.reshape(-1)
        b_values = self.values_buf.reshape(-1)

        clipfracs = []
        envsperbatch = max(1, args.num_envs // args.num_minibatches)
        envinds = np.arange(args.num_envs)
        flatinds = np.arange(args.batch_size).reshape(args.num_steps, args.num_envs)
        
        for epoch in range(args.update_epochs):
            np.random.shuffle(envinds)
            for start in range(0, args.num_envs, envsperbatch):
                end = start + envsperbatch
                mbenvinds = envinds[start:end]
                mb_inds = flatinds[:, mbenvinds].ravel()

                _, newlogprob, entropy, newvalue, _ = self.get_action_and_value(
                    b_obs[mb_inds],
                    (self.initial_lstm_state[0][:, mbenvinds], self.initial_lstm_state[1][:, mbenvinds]),
                    b_dones[mb_inds],
                    b_actions.long()[mb_inds],
                )
                logratio = newlogprob - b_logprobs[mb_inds]
                ratio = logratio.exp()

                with torch.no_grad():
                    approx_kl = ((ratio - 1) - logratio).mean()
                    clipfracs += [((ratio - 1.0).abs() > args.clip_coef).float().mean().item()]

                mb_advantages = b_advantages[mb_inds]
                if args.norm_adv:
                    mb_advantages = (mb_advantages - mb_advantages.mean()) / (mb_advantages.std() + 1e-8)

                pg_loss1 = -mb_advantages * ratio
                pg_loss2 = -mb_advantages * torch.clamp(ratio, 1 - args.clip_coef, 1 + args.clip_coef)
                pg_loss = torch.max(pg_loss1, pg_loss2).mean()

                newvalue = newvalue.view(-1)
                if args.clip_vloss:
                    v_loss_unclipped = (newvalue - b_returns[mb_inds]) ** 2
                    v_clipped = b_values[mb_inds] + torch.clamp(
                        newvalue - b_values[mb_inds],
                        -args.clip_coef,
                        args.clip_coef,
                    )
                    v_loss_clipped = (v_clipped - b_returns[mb_inds]) ** 2
                    v_loss_max = torch.max(v_loss_unclipped, v_loss_clipped)
                    v_loss = 0.5 * v_loss_max.mean()
                else:
                    v_loss = 0.5 * ((newvalue - b_returns[mb_inds]) ** 2).mean()

                entropy_loss = entropy.mean()
                loss = pg_loss - args.ent_coef * entropy_loss + v_loss * args.vf_coef

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.parameters(), args.max_grad_norm)
                optimizer.step()

            if getattr(args, "target_kl", None) is not None and approx_kl > args.target_kl:
                break

        self.step_idx = 0

        var_y = torch.var(b_returns)
        explained_var = np.nan if var_y == 0 else (1 - torch.var(b_returns - b_values) / var_y).item()

        return {
            "v_loss": v_loss.item(),
            "pg_loss": pg_loss.item(),
            "entropy_loss": entropy_loss.item(),
            "approx_kl": approx_kl.item(),
            "clipfrac": np.mean(clipfracs),
            "explained_var": explained_var,
        }

    def load(self, path, device="cpu"):
        self.load_state_dict(torch.load(path, map_location=device, weights_only=True))
