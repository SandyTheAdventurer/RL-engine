import math
import gymnasium as gym
import torch
import numpy as np
from rl.ppo import PPO


class DummyEnv:
    def __init__(self):
        self.env = gym.make("CartPole-v1")

        class Space:
            def __init__(self, shape, nvec):
                self.shape = shape
                self.nvec = nvec

        self.observation_space_ = Space((4,), None)
        self.action_space_ = Space(None, [2])
        self.num_envs = 1

    def observation_space(self, player):
        return self.observation_space_

    def action_space(self, player):
        return self.action_space_

    def _decode_action(self, action, player):
        return action

    def step(self, actions):
        a = actions["player"]
        if isinstance(a, np.ndarray):
            a = int(a[0])

        next_obs, reward, terminated, truncated, info = self.env.step(a)
        done = terminated or truncated

        dones = {"__all__": done}
        return {"player": next_obs, "boss": next_obs}, reward, dones, truncated, info

    def reset(self):
        obs, info = self.env.reset()
        return {"player": obs, "boss": obs}, info


def test_ppo_cartpole():
    env = DummyEnv()

    num_envs = 1
    num_steps = 128

    ppo = PPO(4, [2])
    ppo.init_buffers(num_steps, num_envs)

    optimizer = torch.optim.Adam(ppo.parameters(), lr=1e-3)

    class Args:
        gamma = 0.99
        gae_lambda = 0.95
        num_steps = 128
        num_envs = 1
        batch_size = 128
        num_minibatches = 4
        update_epochs = 4
        norm_adv = True
        clip_coef = 0.2
        clip_vloss = True
        ent_coef = 0.01
        vf_coef = 0.5
        max_grad_norm = 0.5
        target_kl = None

    args = Args()

    lstm_state = (
        torch.zeros(ppo.lstm.num_layers, num_envs, ppo.lstm.hidden_size),
        torch.zeros(ppo.lstm.num_layers, num_envs, ppo.lstm.hidden_size),
    )

    obs, _ = env.reset()
    obs_tensor = torch.tensor(obs["player"], dtype=torch.float32).unsqueeze(0)
    done_tensor = torch.zeros(1)

    episode_rewards = []
    current_reward = 0

    total_timesteps = 3000
    global_step = 0

    while global_step < total_timesteps:
        action, lstm_state = ppo.act(obs_tensor, lstm_state, done_tensor, inference=False)

        action_np = action.cpu().numpy()
        next_obs, reward, dones, trunc, info = env.step({"player": action_np})

        done = dones["__all__"]
        current_reward += reward

        ppo.store_reward([reward])

        obs = next_obs
        obs_tensor = torch.tensor(obs["player"], dtype=torch.float32).unsqueeze(0)
        done_tensor = torch.tensor([float(done)])

        global_step += 1

        if done:
            episode_rewards.append(current_reward)
            current_reward = 0
            obs, _ = env.reset()
            obs_tensor = torch.tensor(obs["player"], dtype=torch.float32).unsqueeze(0)

        if ppo.is_buffer_full():
            metrics = ppo.update(optimizer, args, obs_tensor, done_tensor, lstm_state)

            # Verify all metric keys and finite values
            for key in ["pg_loss", "v_loss", "entropy_loss", "approx_kl", "clipfrac", "explained_var"]:
                assert key in metrics, f"Missing metric key: {key}"
                val = metrics[key]
                if isinstance(val, float):
                    assert math.isfinite(val), f"Metric {key} is not finite: {val}"

            # Buffer should reset after update
            assert ppo.step_idx == 0, "step_idx not reset after update"

    assert len(episode_rewards) >= 5, (
        f"Not enough episodes completed: {len(episode_rewards)} (need >= 5)"
    )

    avg_last_5 = sum(episode_rewards[-5:]) / 5.0
    assert avg_last_5 > 20.0, (
        f"PPO not learning on CartPole: avg last 5 episodes = {avg_last_5:.1f} (expected > 20.0)"
    )
