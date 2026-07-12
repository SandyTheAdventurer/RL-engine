import numpy as np
from rl.env import sys_config, OBS_DIM, AIM_DIRECTIONS
from build.Game import MultiEngine
from gymnasium import spaces
import functools

class MultiEngineEnv:
    def __init__(self, num_envs, frame_skip=4):
        self.num_envs = num_envs
        self.frame_skip = frame_skip
        self.agents = ["player", "boss"]
        
        self.engine = MultiEngine(
            num_envs, frame_skip,
            sys_config["p1_init_x"], sys_config["p1_init_y"], sys_config["p1_init_speed"],
            sys_config["p2_init_x"], sys_config["p2_init_y"], sys_config["p2_init_speed"],
            sys_config["screenw"], sys_config["screenh"]
        )

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent):
        return spaces.Box(-np.inf, np.inf, [OBS_DIM], dtype=np.float32)
        
    @functools.lru_cache(maxsize=None)
    def action_space(self, agent):
        return spaces.MultiDiscrete([3, 3, 2, 2, 2, AIM_DIRECTIONS, 2])
        
    def reset(self):
        obs_dict, _ = self.engine.reset()
        return obs_dict, None

    def step(self, actions):
        p1_actions = actions["player"]
        p2_actions = actions["boss"]
        
        obs, rew, done, trunc, info = self.engine.step(p1_actions, p2_actions, 1.0/60.0)
        return obs, rew, done, trunc, info
