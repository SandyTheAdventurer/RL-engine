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
OBS_DIM = 72

OBS_SELF_X = 2
OBS_SELF_Y = 3

class ShooterEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, frame_skip: int = 4, render: bool = False, opponent: str = "masterpiece"):
        super().__init__()
        self.frame_skip = max(1, frame_skip)
        self.render_enabled = render
        self.opponent_name = opponent

        self.p1 = Game.Player(0, 0, 200.0, "bot")
        self.p2 = Game.Player(0, 0, 200.0, "agent")
        self.engine = Game.Engine(render, render, self.p1, self.p2, 1080, 720)

        self.action_space = spaces.Tuple((
            spaces.Discrete(3),
            spaces.Discrete(3),
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
        bucket = int(action[4])
        angle = bucket * (2.0 * math.pi / AIM_DIRECTIONS)
        cx, cy = center_xy
        aim_x = cx + math.cos(angle) * AIM_RADIUS
        aim_y = cy - math.sin(angle) * AIM_RADIUS
        return Game.PlayerIntent(mx, my, fire, dash, aim_x, aim_y)

    def _make_bot(self):
        if self.opponent_name is None:
            return None
        bot_cls = BOTS[self.opponent_name]
        return bot_cls(1080, 720)

    def _opponent_intent(self):
        if self._bot is None:
            return Game.PlayerIntent(0, 0, False, 0.0, 0.0)
        if self.opponent_name == "human":
            return self._bot.act(self._bot_obs, ENGINE_DT)
        mx, my, fire, dash, reload, aim_x, aim_y = self._bot.act(self._bot_obs, ENGINE_DT)
        return Game.PlayerIntent(int(mx), int(my), bool(fire), bool(dash), bool(reload), float(aim_x), float(aim_y))

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.engine.reset()
        self._bot = self._make_bot()
        obs = self.engine.observe(self.p2, self.p1)
        self._self_center = (obs[OBS_SELF_X], obs[OBS_SELF_Y])
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
        self._self_center = (obs[OBS_SELF_X], obs[OBS_SELF_Y])
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
