import math
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import sys
import os

sys.path.append(os.path.abspath("./build"))
import Game

ENGINE_DT = 1.0 / 60.0
AIM_DIRECTIONS = 16
AIM_RADIUS = 1000.0
OBS_DIM = 76
SCREENW, SCREENH = 1280, 720
NUM_AGENTS = 2

OBS_SELF_X = 4
OBS_SELF_Y = 5


class MultiAgentShooterEnv(gym.Env):


    metadata = {"render_modes": ["human"]}

    is_multiagent = True

    def __init__(
        self,
        full_env_name: str = None,
        cfg=None,
        env_config=None,
        render_mode: str = None,
        frame_skip: int = 4,
    ):
        super().__init__()
        self.name = full_env_name
        self.cfg = cfg
        self.env_config = env_config
        self.render_mode = render_mode

        self.frame_skip = max(1, frame_skip)
        self.render_enabled = render_mode == "human"

        self.num_agents = NUM_AGENTS

        self.p1 = Game.Player(0, 0, 200.0, "p1")
        self.p2 = Game.Player(0, 0, 200.0, "p2")
        self.engine = Game.Engine(self.render_enabled, self.render_enabled, self.p1, self.p2, SCREENW, SCREENH)

        single_action_space = spaces.Tuple((
            spaces.Discrete(3),
            spaces.Discrete(3),
            spaces.Discrete(2),
            spaces.Discrete(2),
            spaces.Discrete(2),
            spaces.Discrete(2),
            spaces.Discrete(AIM_DIRECTIONS),
        ))
        single_obs_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(OBS_DIM,), dtype=np.float32
        )

        self.action_space = single_action_space
        self.observation_space = single_obs_space

        self._self_centers = [(540.0, 360.0), (540.0, 360.0)]
        self._prev_health = [100.0, 100.0]
        self._prev_ammo = [self.p1.ammo, self.p2.ammo]

    def _decode_action(self, action, center_xy):
        mx = int(action[0]) - 1
        my = int(action[1]) - 1
        fire = bool(action[2])
        dash = bool(action[3])
        reload = bool(action[4])
        attack = bool(action[5])
        bucket = int(action[6])
        angle = bucket * (2.0 * math.pi / AIM_DIRECTIONS)
        cx, cy = center_xy
        aim_x = cx + math.cos(angle) * AIM_RADIUS
        aim_y = cy - math.sin(angle) * AIM_RADIUS
        return Game.PlayerIntent(mx, my, fire, dash, reload, aim_x, aim_y, attack)

    def _observe_both(self):
        obs1 = self.engine.observe(self.p1, self.p2).astype(np.float32)
        obs2 = self.engine.observe(self.p2, self.p1).astype(np.float32)
        self._self_centers[0] = (obs1[OBS_SELF_X] * SCREENW, obs1[OBS_SELF_Y] * SCREENH)
        self._self_centers[1] = (obs2[OBS_SELF_X] * SCREENW, obs2[OBS_SELF_Y] * SCREENH)
        return [obs1, obs2]

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.engine.reset()
        obs = self._observe_both()
        self._prev_health = [self.p1.health, self.p2.health]
        self._prev_ammo = [self.p1.ammo, self.p2.ammo]
        infos = [{}, {}]
        return obs, infos

    def step(self, actions):
        intent1 = self._decode_action(actions[0], self._self_centers[0])
        intent2 = self._decode_action(actions[1], self._self_centers[1])

        for _ in range(self.frame_skip):
            self.engine.step(intent1, intent2, ENGINE_DT)
            if self.render_enabled:
                self.engine.render()
                self.engine.present()
            if self.engine.is_done():
                break

        obs = self._observe_both()
        h1, h2 = self.p1.health, self.p2.health
        prev_h1, prev_h2 = self._prev_health
        dmg1_dealt = prev_h2 - h2
        dmg1_taken = prev_h1 - h1

        reward1 = dmg1_dealt - dmg1_taken - 0.005
        reward2 = dmg1_taken - dmg1_dealt - 0.005

        a1, a2 = self.p1.ammo, self.p2.ammo
        prev_a1, prev_a2 = self._prev_ammo
        reward1 -= 0.05 * max(0, prev_a1 - a1)
        reward2 -= 0.05 * max(0, prev_a2 - a2)
        self._prev_ammo = [a1, a2]

        dist_norm1 = obs[0][73]
        dist_norm2 = obs[1][73]
        reward1 += 0.003 * (1.0 - dist_norm1)
        reward2 += 0.003 * (1.0 - dist_norm2)

        if dmg1_dealt > 0:
            reward1 += 0.5
        if dmg1_taken > 0:
            reward2 += 0.5

        self._prev_health = [h1, h2]

        terminated = bool(self.engine.is_done())
        truncated = False

        if terminated:
            if h1 <= 0 and h2 > 0:
                reward1 -= 25.0
                reward2 += 25.0
            elif h2 <= 0 and h1 > 0:
                reward2 -= 25.0
                reward1 += 25.0

        rewards = [float(reward1), float(reward2)]
        infos = [{}, {}]

        # Both players share one episode clock (the match ends for both of
        # them at once), so terminated/truncated are identical across
        # agents here. If your engine can ever end the match for one
        # player but not the other, look at Sample Factory's "inactive
        # agents" feature instead of always terminating both.
        terminated_l = [terminated, terminated]
        truncated_l = [truncated, truncated]

        if terminated or truncated:
            # Provide true_objective so PBT optimises for winning matches
            # rather than for maxing the shaped damage reward.
            if h1 <= 0 and h2 > 0:
                infos[0]["true_objective"] = -1.0
                infos[1]["true_objective"] = +1.0
            elif h2 <= 0 and h1 > 0:
                infos[0]["true_objective"] = +1.0
                infos[1]["true_objective"] = -1.0
            else:
                infos[0]["true_objective"] = 0.0
                infos[1]["true_objective"] = 0.0

            # Sample Factory's multi-agent contract requires auto-reset:
            # return the first observation of the next episode rather than
            # the terminal observation, since nothing acts on the latter.
            obs, _reset_infos = self.reset()

        return obs, rewards, terminated_l, truncated_l, infos

    def render(self):
        pass

    def close(self):
        self.engine.close()


import os

from sample_factory.envs.env_utils import register_env
from sample_factory.train import run_rl
from sample_factory.cfg.arguments import parse_full_cfg, parse_sf_args
from sample_factory.algo.utils.misc import ExperimentStatus
from sample_factory.export_onnx import export_onnx


def make_multi_shooter_env(full_env_name, cfg=None, env_config=None, render_mode=None):
    frame_skip = getattr(cfg, "frame_skip", 4)
    render = render_mode is not None
    return MultiAgentShooterEnv(
        full_env_name=full_env_name,
        cfg=cfg,
        env_config=env_config,
        render_mode=render_mode,
        frame_skip=frame_skip,
    )


def register_multi_shooter_components():
    register_env("shooter_multi_v1", make_multi_shooter_env)


def add_multi_shooter_env_args(parser):
    parser.add_argument("--frame_skip", default=4, type=int,
                        help="Number of engine ticks each PlayerIntent is held for per env.step()")


def multi_shooter_override_defaults(_env_name, parser):
    parser.set_defaults(
        encoder_type="mlp",
        encoder_mlp_layers=[256, 256, 256],
        use_rnn=True,
        rollout=64,
        batch_size=2048,
        num_batches_per_epoch=1,
        ppo_epochs=2,
        ppo_clip_ratio=0.2,
        gamma=0.99,
        gae_lambda=0.95,
        learning_rate=3e-4,
        value_loss_coeff=0.5,
        exploration_loss_coeff=0.003,
        max_grad_norm=4.0,
        normalize_input=True,
        normalize_returns=True,
        reward_scale=1.0,
        num_workers=6,
        num_envs_per_worker=2,
        async_rl=True,
        train_for_env_steps=int(50_000_000),
        save_every_sec=60,
        experiment_summaries_interval=10,
        num_policies=2,
        with_pbt=True,
        pbt_period_env_steps=5_000_000,
        pbt_start_mutation=10_000_000,
        pbt_replace_reward_gap=0.05,
        pbt_replace_reward_gap_absolute=5.0,
        pbt_mix_policies_in_one_env=True,
    )


def auto_export(cfg):
    num_policies = getattr(cfg, "num_policies", 1)
    for policy_idx in range(num_policies):
        export_cfg = cfg.clone() if hasattr(cfg, "clone") else cfg
        export_cfg.policy_index = policy_idx
        onnx_path = os.path.join(cfg.experiment_dir, f"policy_{policy_idx}.onnx")
        print(f"Exporting policy {policy_idx} to {onnx_path} ...")
        status = export_onnx(export_cfg, onnx_path)
        if status != ExperimentStatus.SUCCESS:
            print(f"  Failed to export policy {policy_idx}")
        else:
            print(f"  Done: {onnx_path}")


def main():
    register_multi_shooter_components()
    parser, partial_cfg = parse_sf_args()
    add_multi_shooter_env_args(parser)
    multi_shooter_override_defaults(partial_cfg.env, parser)
    cfg = parse_full_cfg(parser)
    status = run_rl(cfg)
    if status == ExperimentStatus.SUCCESS:
        auto_export(cfg)
    return status


if __name__ == "__main__":
    main()