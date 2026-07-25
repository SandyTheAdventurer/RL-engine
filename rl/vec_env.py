import numpy as np
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'build')))
import Game
from Game import MultiEngine
from gymnasium import spaces
import functools
from rl.config import aim_directions, frame_skip as cfg_frame_skip

OBS_DIM = Game.obs_dim

class MultiEngineEnv:
    def __init__(self, num_envs, frame_skip=None):
        self.num_envs = num_envs
        self.frame_skip = frame_skip if frame_skip is not None else cfg_frame_skip()
        self.agents = ["player", "boss"]

        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        self.engine = MultiEngine(config_path)
        self.engine.init_engines(num_envs)

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent):
        return spaces.Box(-np.inf, np.inf, [OBS_DIM], dtype=np.float32)
        
    @functools.lru_cache(maxsize=None)
    def action_space(self, agent):
        return spaces.MultiDiscrete([3, 3, 2, 2, 4, aim_directions(), 2])
        
    def reset(self):
        obs_dict, _ = self.engine.reset()
        return obs_dict, None

    def step(self, actions):
        p1_actions = actions["player"]
        p2_actions = actions["boss"]
        
        obs, rew, done, trunc, info = self.engine.step(p1_actions, p2_actions, 1.0/60.0)
        return obs, rew, done, trunc, info
