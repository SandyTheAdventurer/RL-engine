import gymnasium as gym
import torch
import numpy as np
from rl.gail import GAIL


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


def generate_expert_data(env, num_steps=500):
    obs_list = []
    actions_list = []

    obs, _ = env.reset()

    for _ in range(num_steps):
        obs_player = obs["player"]

        angle = obs_player[2]
        angular_vel = obs_player[3]

        if angle + angular_vel > 0:
            action = 1
        else:
            action = 0

        obs_list.append(obs_player)
        actions_list.append([action])

        next_obs, _, dones, _, _ = env.step({"player": action, "boss": 0})

        if dones["__all__"]:
            obs, _ = env.reset()
        else:
            obs = next_obs

    return np.array(obs_list), np.array(actions_list)


def test_gail_cartpole():
    env = DummyEnv()
    device = "cpu"

    expert_obs, expert_actions = generate_expert_data(env, num_steps=1000)
    assert len(expert_obs) == 1000, f"Expected 1000 expert obs, got {len(expert_obs)}"
    assert len(expert_actions) == 1000, f"Expected 1000 expert actions, got {len(expert_actions)}"
    assert expert_obs.shape[1] == 4, f"Expert obs dim wrong: {expert_obs.shape}"

    gail = GAIL(env, device=device)

    # Verify GAIL components exist and have correct shapes
    assert gail.generator is not None
    assert gail.boss is not None
    assert gail.discriminator is not None
    assert gail.obs_normalizer is not None

    obs, _ = env.reset()
    done = np.zeros(1, dtype=bool)

    gen_lstm = (
        torch.zeros(gail.generator.lstm.num_layers, 1, gail.generator.lstm.hidden_size).to(device),
        torch.zeros(gail.generator.lstm.num_layers, 1, gail.generator.lstm.hidden_size).to(device),
    )
    boss_lstm = (
        torch.zeros(gail.boss.lstm.num_layers, 1, gail.boss.lstm.hidden_size).to(device),
        torch.zeros(gail.boss.lstm.num_layers, 1, gail.boss.lstm.hidden_size).to(device),
    )
    disc_lstm = (
        torch.zeros(gail.discriminator.lstm.num_layers, 1, gail.discriminator.lstm.hidden_size).to(device),
        torch.zeros(gail.discriminator.lstm.num_layers, 1, gail.discriminator.lstm.hidden_size).to(device),
    )

    persistent_state = (obs, done, gen_lstm, boss_lstm, disc_lstm)

    # Snapshot parameters before training
    gen_params_before = {n: p.clone() for n, p in gail.generator.named_parameters()}
    disc_params_before = {n: p.clone() for n, p in gail.discriminator.named_parameters()}

    # Train — gail.train returns (gen_score, avg_gen_damage, state)
    result = gail.train(
        expert_actions, expert_obs, total_timesteps=300,
        persistent_state=persistent_state, num_steps=128,
    )

    assert isinstance(result, tuple), f"Expected tuple return, got {type(result)}"
    assert len(result) == 3, f"Expected 3-tuple (gen_score, avg_gen_damage, state), got {len(result)}"

    gen_score, avg_gen_damage, new_state = result

    # Validate gen_score
    assert isinstance(gen_score, float), f"gen_score should be float, got {type(gen_score)}"
    assert 0.0 <= gen_score <= 1.0, f"gen_score out of [0,1] range: {gen_score}"

    # Validate avg_gen_damage
    assert isinstance(avg_gen_damage, float), f"avg_gen_damage should be float, got {type(avg_gen_damage)}"
    assert avg_gen_damage >= 0.0, f"avg_gen_damage is negative: {avg_gen_damage}"

    # Validate returned state structure
    assert isinstance(new_state, tuple), "new_state should be a tuple"
    assert len(new_state) == 5, f"new_state should have 5 elements, got {len(new_state)}"

    obs_state, done_state, gen_lstm_state, boss_lstm_state, disc_lstm_state = new_state
    assert isinstance(obs_state, dict), "obs_state should be a dict"
    assert "player" in obs_state, "obs_state missing 'player' key"
    assert isinstance(gen_lstm_state, tuple) and len(gen_lstm_state) == 2
    assert isinstance(boss_lstm_state, tuple) and len(boss_lstm_state) == 2
    assert isinstance(disc_lstm_state, tuple) and len(disc_lstm_state) == 2

    # Verify generator parameters changed
    gen_changed = False
    for name, p in gail.generator.named_parameters():
        if not torch.equal(p, gen_params_before[name]):
            gen_changed = True
            break
    assert gen_changed, "Generator parameters did not change after GAIL training"

    # Verify discriminator parameters changed
    disc_changed = False
    for name, p in gail.discriminator.named_parameters():
        if not torch.equal(p, disc_params_before[name]):
            disc_changed = True
            break
    assert disc_changed, "Discriminator parameters did not change after GAIL training"
