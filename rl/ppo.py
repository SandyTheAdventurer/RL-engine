import math

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from rl.utils import *
except ImportError:
    from utils import *


class PPORolloutWorker:
    """Manages environment transitions, reward calculation, and trajectory buffering.

    Note: this class does NOT trigger training updates itself. Callers should
    call `worker.maybe_update()` after each `step()` (or check
    `worker.ready_for_update()` and call `agent.update(worker)` /
    `worker.clear()` manually). Keeping the update trigger out of `step()`
    means "collect a transition" and "run a gradient step" are separate,
    testable operations instead of one hiding inside the other.
    """

    def __init__(self, agent, update_interval=500):
        self.agent = agent
        self.update_interval = update_interval

        self.episode_reward = 0
        self.clear()
        self.reset_step_state()

    # -- buffer management (formerly PPOBuffer) ------------------------------

    def clear(self):
        self.obs = []
        self.mx = []
        self.my = []
        self.fire = []
        self.aim = []
        self.log_probs = []
        self.rewards = []
        self.dones = []
        self.values = []

    def add(self, obs, mx, my, fire, aim, log_prob, reward, done, value):
        self.obs.append(obs.detach())
        self.mx.append(mx.detach())
        self.my.append(my.detach())
        self.fire.append(fire.detach())
        self.aim.append(aim.detach())
        self.log_probs.append(log_prob.detach())
        self.rewards.append(reward)
        self.dones.append(done)
        self.values.append(value.detach())

    def get(self):
        return (
            torch.stack(self.obs),
            torch.stack(self.mx),
            torch.stack(self.my),
            torch.stack(self.fire),
            torch.stack(self.aim),
            torch.stack(self.log_probs),
            torch.tensor(self.rewards, dtype=torch.float32),
            torch.tensor(self.dones, dtype=torch.float32),
            torch.stack(self.values).float(),
        )

    def __len__(self):
        return len(self.obs)

    def ready_for_update(self):
        return len(self) >= self.update_interval

    # -- rollout stepping -----------------------------------------------

    def reset_step_state(self):
        self.prev_obs = None
        self.prev_mx = None
        self.prev_my = None
        self.prev_fire = None
        self.prev_aim = None
        self.prev_log_prob = None
        self.prev_value = None
        self.prev_human_health = None
        self.prev_bot_health = None

    def step(self, obs_t, health, enemy_health):
        """Processes a single step, calculates reward, appends the previous
        transition to the buffer, and returns new actions. Does not train --
        call `maybe_update()` (or check `ready_for_update()`) separately."""
        reward = 0
        if self.prev_human_health is not None:
            reward = (health - self.prev_human_health)
            reward += (self.prev_bot_health - enemy_health)

        done = health <= 0 or enemy_health <= 0

        # Store transition
        if self.prev_obs is not None:
            aim_clamped = torch.clamp(self.prev_aim, -0.999, 0.999)
            self.add(
                self.prev_obs.squeeze(0), self.prev_mx, self.prev_my,
                self.prev_fire, aim_clamped, self.prev_log_prob,
                reward, done, self.prev_value
            )

        self.episode_reward += reward

        # Reset state on game over
        if done:
            self.reset_step_state()
        else:
            self.prev_human_health = health
            self.prev_bot_health = enemy_health

        # Get next action
        mx, my, fire, aim, log_prob, value = self.agent.get_action(obs_t)

        # Cache state for the next transition
        self.prev_obs = obs_t
        self.prev_mx = mx
        self.prev_my = my
        self.prev_fire = fire
        self.prev_aim = aim
        self.prev_log_prob = log_prob.detach()
        self.prev_value = value.detach()

        return mx, my, fire, aim

    def maybe_update(self):
        """Runs a PPO update and clears the buffer if enough transitions have
        been collected. Returns the stats dict, or None if not ready yet."""
        if not self.ready_for_update():
            return None
        stats = self.agent.update(self)
        print(f"PPO update: reward={self.episode_reward:.1f} loss={stats['loss']:.4f}")
        self.clear()
        self.episode_reward = 0
        return stats

class PPO(nn.Module):
    def __init__(self, config, device='cpu'):
        super().__init__()
        self.device = torch.device(device)
        self.input_dim = config["input_dim"]
        self.hidden_dim = config["hidden_dim"]
        self.n_layers = config["n_layers"]
        self.screenw = config["screenw"]
        self.screenh = config["screenh"]
        self.gamma = config.get("gamma", 0.99)
        self.lam = config.get("lam", 0.95)
        self.clip_epsilon = config.get("clip_epsilon", 0.2)
        self.n_epochs = config.get("n_epochs", 10)
        self.entropy_coef = config.get("entropy_coef", 0.01)
        self.vf_coef = config.get("vf_coef", 0.5)
        self.max_grad_norm = config.get("max_grad_norm", 0.5)
        self.batch_size = config.get("batch_size", 64)

        self.clip_value_loss = config.get("clip_value_loss", True)
        self.target_kl = config.get("target_kl", None)
        self.total_updates = config.get("total_updates", None)

        self.update_counter = 0

        act_cls = {'relu': nn.ReLU, 'gelu': nn.GELU}.get(config.get("activation", "relu"), nn.ReLU)

        layers = [nn.Linear(self.input_dim, self.hidden_dim), act_cls()]
        for _ in range(self.n_layers):
            layers += [nn.Linear(self.hidden_dim, self.hidden_dim), act_cls()]

        self.network = nn.Sequential(*layers)
        
        self.mx_head = nn.Linear(self.hidden_dim, 3)
        self.my_head = nn.Linear(self.hidden_dim, 3)
        self.fire_head = nn.Linear(self.hidden_dim, 1)
        self.aim_mean = nn.Linear(self.hidden_dim, 2)
        
        self.aim_log_std = nn.Parameter(torch.zeros(2)) 
        
        self.value_head = nn.Linear(self.hidden_dim, 1)

        norm_array = [
            1000, 1000, self.screenw, self.screenh, self.screenw, self.screenh,
            200, 200, 200, 200,
            *[1]*6, *[1]*6,
            *[self.screenw, self.screenh]*12,
            *[750, 750]*12,
        ]
        
        assert len(norm_array) == self.input_dim, \
            f"Norm array length ({len(norm_array)}) does not match input_dim ({self.input_dim})"
            
        self.register_buffer("obs_norm", torch.tensor(norm_array, dtype=torch.float32))

        if config.get("init_weights", True):
            self._init_weights()

        self.optim = torch.optim.Adam(self.parameters(), lr=config['lr'])

        self.lr_scheduler = None
        if self.total_updates is not None:
            self.lr_scheduler = torch.optim.lr_scheduler.LambdaLR(
                self.optim,
                lr_lambda=lambda step: max(0.0, 1.0 - step / self.total_updates),
            )

        self.to(self.device)

    def _init_weights(self):
        for m in self.network:
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=math.sqrt(2))
                nn.init.constant_(m.bias, 0.0)

        for head, gain in (
            (self.mx_head, 0.01),
            (self.my_head, 0.01),
            (self.fire_head, 0.01),
            (self.aim_mean, 0.01),
            (self.value_head, 1.0),
        ):
            nn.init.orthogonal_(head.weight, gain=gain)
            nn.init.constant_(head.bias, 0.0)

    def normalize_obs(self, obs):
        obs_scaled = obs / self.obs_norm
        return torch.clamp(obs_scaled, min=-1.0, max=1.0)

    def forward(self, obs):
        obs = obs.to(self.device)
        obs = self.normalize_obs(obs)
        h = self.network(obs)
        
        mx = self.mx_head(h)
        my = self.my_head(h)
        fire = self.fire_head(h).squeeze(-1)
        
        aim_mu = self.aim_mean(h)
        aim_ls = self.aim_log_std.expand_as(aim_mu) 
        
        val = self.value_head(h).squeeze(-1)
        
        return mx, my, fire, aim_mu, aim_ls, val

    @torch.no_grad()
    def get_action(self, obs):
        mx_logits, my_logits, fire_logit, aim_mu, aim_log_sigma, value = self(obs)

        mx_dist = torch.distributions.Categorical(logits=mx_logits)
        my_dist = torch.distributions.Categorical(logits=my_logits)
        fire_dist = torch.distributions.Bernoulli(logits=fire_logit)
        
        aim_std = torch.exp(aim_log_sigma)
        aim_dist = TanhGaussian(aim_mu, aim_std)

        mx = mx_dist.sample()
        my = my_dist.sample()
        fire = fire_dist.sample()
        aim = aim_dist.sample()

        log_prob = (
            mx_dist.log_prob(mx)
            + my_dist.log_prob(my)
            + fire_dist.log_prob(fire)
            + aim_dist.log_prob(aim).sum(dim=-1)
        )

        return mx, my, fire, aim, log_prob, value

    def evaluate(self, obs, mx, my, fire, aim):
        mx_logits, my_logits, fire_logit, aim_mu, aim_log_sigma, value = self(obs)

        mx_dist = torch.distributions.Categorical(logits=mx_logits)
        my_dist = torch.distributions.Categorical(logits=my_logits)
        fire_dist = torch.distributions.Bernoulli(logits=fire_logit)
        
        aim_std = torch.exp(aim_log_sigma)
        aim_dist = TanhGaussian(aim_mu, aim_std)

        log_prob = (
            mx_dist.log_prob(mx)
            + my_dist.log_prob(my)
            + fire_dist.log_prob(fire)
            + aim_dist.log_prob(aim).sum(dim=-1)
        )

        entropy = (
            mx_dist.entropy()
            + my_dist.entropy()
            + fire_dist.entropy()
            + aim_dist.entropy().sum(dim=-1)
        )

        return log_prob, entropy, value

    def compute_gae(self, rewards, dones, values, last_value=0.0):
        T = len(rewards)
        last_value = torch.as_tensor(last_value, dtype=values.dtype, device=values.device)

        advantages = torch.zeros_like(values)
        gae = torch.zeros_like(values[0])
        for t in reversed(range(T)):
            next_val = last_value if t == T - 1 else values[t + 1]
            next_non_terminal = 1.0 - dones[t]
            delta = rewards[t] + self.gamma * next_val * next_non_terminal - values[t]
            gae = delta + self.gamma * self.lam * next_non_terminal * gae
            advantages[t] = gae

        returns = advantages + values
        return advantages, returns

    def update(self, buffer, last_value=0.0):
        obs, mx, my, fire, aim, old_log_probs, rewards, dones, values = buffer.get()

        advantages, returns = self.compute_gae(rewards, dones, values, last_value=last_value)
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        obs = obs.to(self.device)
        mx = mx.to(self.device)
        my = my.to(self.device)
        fire = fire.to(self.device)
        aim = aim.to(self.device)
        old_log_probs = old_log_probs.to(self.device)
        advantages = advantages.to(self.device)
        returns = returns.to(self.device)
        old_values = values.to(self.device)

        n = len(obs)
        stats = {
            "policy_loss": 0.0,
            "value_loss": 0.0,
            "entropy": 0.0,
            "approx_kl": 0.0,
            "clip_fraction": 0.0,
            "loss": 0.0,
        }
        n_updates = 0
        stopped_early = False

        for epoch in range(self.n_epochs):
            if stopped_early:
                break

            indices = torch.randperm(n, device=self.device)
            for start in range(0, n, self.batch_size):
                end = min(start + self.batch_size, n)
                idx = indices[start:end]

                batch_obs = obs[idx]
                batch_mx = mx[idx]
                batch_my = my[idx]
                batch_fire = fire[idx]
                batch_aim = aim[idx]
                batch_old = old_log_probs[idx]
                batch_adv = advantages[idx]
                batch_ret = returns[idx]
                batch_old_val = old_values[idx]

                log_probs, entropy, pred_values = self.evaluate(
                    batch_obs, batch_mx, batch_my, batch_fire, batch_aim
                )

                log_ratio = log_probs - batch_old
                ratio = torch.exp(log_ratio)
                clipped = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon)
                policy_loss = -torch.min(ratio * batch_adv, clipped * batch_adv).mean()

                if self.clip_value_loss:
                    value_pred_clipped = batch_old_val + torch.clamp(
                        pred_values - batch_old_val, -self.clip_epsilon, self.clip_epsilon
                    )
                    value_loss_unclipped = (pred_values - batch_ret) ** 2
                    value_loss_clipped = (value_pred_clipped - batch_ret) ** 2
                    value_loss = torch.max(value_loss_unclipped, value_loss_clipped).mean()
                else:
                    value_loss = F.mse_loss(pred_values, batch_ret)

                entropy_mean = entropy.mean()
                loss = policy_loss + self.vf_coef * value_loss - self.entropy_coef * entropy_mean

                self.optim.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.parameters(), self.max_grad_norm)
                self.optim.step()

                with torch.no_grad():
                    approx_kl = ((ratio - 1) - log_ratio).mean()
                    clip_fraction = (torch.abs(ratio - 1) > self.clip_epsilon).float().mean()

                stats["policy_loss"] += policy_loss.item()
                stats["value_loss"] += value_loss.item()
                stats["entropy"] += entropy_mean.item()
                stats["approx_kl"] += approx_kl.item()
                stats["clip_fraction"] += clip_fraction.item()
                stats["loss"] += loss.item()
                n_updates += 1

                if self.target_kl is not None and approx_kl.item() > self.target_kl:
                    stopped_early = True
                    break

        for k in stats:
            stats[k] /= max(1, n_updates)
        stats["n_updates"] = n_updates
        stats["stopped_early"] = stopped_early

        self.update_counter += 1
        if self.lr_scheduler is not None:
            self.lr_scheduler.step()

        return stats

    def save(self, path):
        torch.save(
            {
                "model_state_dict": self.state_dict(),
                "optim_state_dict": self.optim.state_dict(),
                "update_counter": self.update_counter,
            },
            path,
        )

    def load(self, path, map_location=None):
        ckpt = torch.load(path, map_location=map_location or self.device)
        self.load_state_dict(ckpt["model_state_dict"])
        self.optim.load_state_dict(ckpt["optim_state_dict"])
        self.update_counter = ckpt.get("update_counter", 0)