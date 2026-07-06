import math
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import sys
import os

sys.path.append(os.path.abspath("./build"))
import Game
from rl.bots import BOTS

ENGINE_DT = 1.0 / 60.0
AIM_DIRECTIONS = 16
AIM_RADIUS = 1000.0
OBS_DIM = 76
SCREENW, SCREENH = 1280, 720

OBS_SELF_X = 4
OBS_SELF_Y = 5

class ShooterEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, frame_skip: int = 4, render: bool = False, opponent: str = "medium"):
        super().__init__()
        self.frame_skip = max(1, frame_skip)
        self.render_enabled = render
        self.opponent_name = opponent

        self.p1 = Game.Player(0, 0, 200.0, "bot")
        self.p2 = Game.Player(0, 0, 200.0, "agent")
        self.engine = Game.Engine(render, render, self.p1, self.p2, SCREENW, SCREENH)

        self.action_space = spaces.Tuple((
            spaces.Discrete(3),
            spaces.Discrete(3),
            spaces.Discrete(2),
            spaces.Discrete(2),
            spaces.Discrete(2),
            spaces.Discrete(AIM_DIRECTIONS),
        ))
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(OBS_DIM,), dtype=np.float32
        )

        self._self_center = (540.0, 360.0)
        self._prev_self_health = 100.0
        self._prev_enemy_health = 100.0
        self._bot = self._make_bot()
        self._bot_obs = None

    def _decode_action(self, action, center_xy):
        mx = int(action[0]) - 1
        my = int(action[1]) - 1
        fire = bool(action[2])
        dash = bool(action[3])
        attack = bool(action[4])
        bucket = int(action[5])
        angle = bucket * (2.0 * math.pi / AIM_DIRECTIONS)
        cx, cy = center_xy
        aim_x = cx + math.cos(angle) * AIM_RADIUS
        aim_y = cy - math.sin(angle) * AIM_RADIUS
        return Game.PlayerIntent(mx, my, fire, dash, False, aim_x, aim_y, attack)

    def _make_bot(self):
        if self.opponent_name is None:
            return None
        bot_cls = BOTS[self.opponent_name]
        return bot_cls(1080, 720)

    def _opponent_intent(self):
        if self._bot is None:
            return Game.PlayerIntent(0, 0, False, False, False, 0.0, 0.0, False)
        if self.opponent_name == "human":
            return self._bot.act(self._bot_obs, ENGINE_DT)
        mx, my, fire, dash, reload, aim_x, aim_y, attack = self._bot.act(self._bot_obs, ENGINE_DT)
        return Game.PlayerIntent(int(mx), int(my), bool(fire), bool(dash), bool(reload), float(aim_x), float(aim_y), bool(attack))

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.engine.reset()
        self._bot = self._make_bot()
        obs = self.engine.observe(self.p2, self.p1)
        self._self_center = (obs[OBS_SELF_X] * SCREENW, obs[OBS_SELF_Y] * SCREENH)
        self._bot_obs = self.engine.observe(self.p1, self.p2)
        self._prev_self_health = self.p2.health
        self._prev_enemy_health = self.p1.health
        return obs.astype(np.float32), {}

    def step(self, action):
        intent2 = self._decode_action(action, self._self_center)
        for _ in range(self.frame_skip):
            intent1 = self._opponent_intent()
            self.engine.step(intent1, intent2, ENGINE_DT)
            self._bot_obs = self.engine.observe(self.p1, self.p2)
            if self.render_enabled:
                self.engine.render()
                self.engine.present()
            if self.engine.is_done():
                break
        obs = self.engine.observe(self.p2, self.p1)
        self._self_center = (obs[OBS_SELF_X] * SCREENW, obs[OBS_SELF_Y] * SCREENH)
        self_health = self.p2.health
        enemy_health = self.p1.health
        reward = (self._prev_enemy_health - enemy_health) \
                - (self._prev_self_health - self_health) \
                - 0.001
        self._prev_self_health = self_health
        self._prev_enemy_health = enemy_health
        terminated = bool(self.engine.is_done())
        truncated = False
        if terminated:
            if self_health <= 0 and enemy_health > 0:
                reward -= 10.0
            elif enemy_health <= 0 and self_health > 0:
                reward += 10.0
        return obs.astype(np.float32), float(reward), terminated, truncated, {}

    def render(self):
        pass

    def close(self):
        self.engine.close()


from sample_factory.envs.env_utils import register_env
from sample_factory.train import run_rl
from sample_factory.cfg.arguments import parse_full_cfg, parse_sf_args


def make_shooter_env(full_env_name, cfg=None, env_config=None, render_mode=None):
    frame_skip = getattr(cfg, "frame_skip", 4)
    opponent = getattr(cfg, "opponent", "hardened")
    if opponent == "none":
        opponent = None
    render = render_mode is not None
    return ShooterEnv(frame_skip=frame_skip, render=render, opponent=opponent)


def register_shooter_components():
    register_env("shooter_v1", make_shooter_env)


def add_shooter_env_args(parser):
    parser.add_argument("--frame_skip", default=4, type=int,
                        help="Number of engine ticks each PlayerIntent is held for per env.step()")
    parser.add_argument("--opponent", default="medium",
                        choices=["easy", "medium", "hard", "expert", "none", "human"],
                        help="Scripted bot (from bots.py) to train against; 'none' = idle opponent")


def shooter_override_defaults(_env_name, parser):
    parser.set_defaults(
        encoder_type="mlp",
        encoder_mlp_layers=[256, 256, 256],
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
        num_workers=10,
        num_envs_per_worker=2,
        worker_num_splits=2,
        async_rl=True,
        train_for_env_steps=int(15_000_000),
        save_every_sec=60,
        experiment_summaries_interval=10,
    )


def main():
    register_shooter_components()
    parser, partial_cfg = parse_sf_args()
    add_shooter_env_args(parser)
    shooter_override_defaults(partial_cfg.env, parser)
    cfg = parse_full_cfg(parser)
    status = run_rl(cfg)
    return status


if __name__ == "__main__":
    main()
