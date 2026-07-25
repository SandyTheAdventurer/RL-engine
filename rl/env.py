import functools
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'build')))
import Game
from Game import Engine, Player, PlayerIntent
from gymnasium import spaces
import numpy as np
from pettingzoo.utils.env import ParallelEnv
from rl.config import screenw, screenh, playerspeed, aim_directions, aim_radius, frame_skip as _cfg_frame_skip, win_bonus as _cfg_win_bonus

ENGINE_DT = 1.0 / 60.0
OBS_DIM = Game.obs_dim
TIME_PENALTY = -0.01
WIN_BONUS = _cfg_win_bonus()

def make_sys_config():
    sw, sh, sp = screenw(), screenh(), playerspeed()
    return {
        "p1_init_x": -1.0, "p1_init_y": -1.0, "p1_init_speed": sp,
        "p2_init_x": -1.0, "p2_init_y": -1.0, "p2_init_speed": sp,
        "screenw": sw, "screenh": sh,
    }

sys_config = make_sys_config()

class EngineEnv(ParallelEnv):
    metadata = {
            "name": "EngineEnv"
        }
    def __init__(self, render, sys_config, frame_skip=None):
        super().__init__()

        self.sys_config = sys_config
        self.frame_skip = frame_skip if frame_skip is not None else _cfg_frame_skip()
        self.possible_agents = ["player", "boss"]
        self.p1 = Player(sys_config["p1_init_x"], sys_config["p1_init_y"], sys_config["p1_init_speed"], "player")
        self.p2 = Player(sys_config["p2_init_x"], sys_config["p2_init_y"], sys_config["p2_init_speed"], "boss")

        self.engine = Engine(render, render, self.p1, self.p2, sys_config["screenw"], sys_config["screenh"])

        self.players = {"player": self.p1, "boss": self.p2}
        self.agents = self.possible_agents[:]

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent):
        return spaces.Box(-np.inf, np.inf, [OBS_DIM], dtype=np.float32)
    
    @functools.lru_cache(maxsize=None)
    def action_space(self, agent):
        return spaces.MultiDiscrete([3, 3, 2, 2, 4, aim_directions(), 2])

    def _get_obs(self):
        return {"player": self.engine.observe(self.p1, self.p2),
                "boss": self.engine.observe(self.p2, self.p1)}

    def _decode_action(self, action, player: Player):
        mx = int(action[0]) - 1
        my = int(action[1]) - 1
        fire = bool(action[2])
        dash = bool(action[3])
        # selected_spell 0-3; the engine's reasoning gate still clamps what fires
        spell = int(action[4])
        _aim_dirs = aim_directions()
        _aim_rad = aim_radius()
        angle = int(action[5]) * (2 * np.pi / _aim_dirs)
        aimx = player.px + np.cos(angle) * _aim_rad
        aimy = player.py + np.sin(angle) * _aim_rad
        attack = bool(action[6])
        return PlayerIntent(mx, my, fire, dash, spell, aimx, aimy, attack)

    def reset(self, seed = None, options = None):
        self.agents = self.possible_agents[:]
        self.engine.reset(self.sys_config["p1_init_x"], self.sys_config["p1_init_y"], self.sys_config["p2_init_x"], self.sys_config["p2_init_y"])
        self.p1.damage_dealt_step = 0.0
        self.p1.damage_taken_step = 0.0
        self.p2.damage_dealt_step = 0.0
        self.p2.damage_taken_step = 0.0
        infos = {a: {} for a in self.agents}
        return self._get_obs(), infos
    
    def reward(self, me: str, he: str):
        base_reward = self.players[me].damage_dealt_step - self.players[me].damage_taken_step
        return base_reward + TIME_PENALTY
    
    def step(self, actions):
        p1_action = self._decode_action(actions["player"], self.p1)
        p2_action = self._decode_action(actions["boss"], self.p2)

        self.p1.damage_dealt_step = 0.0
        self.p1.damage_taken_step = 0.0
        self.p2.damage_dealt_step = 0.0
        self.p2.damage_taken_step = 0.0

        for _ in range(self.frame_skip):
            self.engine.step(p1_action, p2_action, ENGINE_DT)
            if self.engine.is_done():
                break

        obs = self._get_obs()

        rewards = {"player": self.reward("player", "boss"), "boss": self.reward("boss", "player")}
        
        dones = {"player": self.engine.is_done(), "boss": self.engine.is_done(), "__all__": self.engine.is_done()}
        
        if self.engine.is_done():
            if self.p1.health > 0 and self.p2.health <= 0:
                rewards["player"] += WIN_BONUS
                rewards["boss"] -= WIN_BONUS
            elif self.p2.health > 0 and self.p1.health <= 0:
                rewards["boss"] += WIN_BONUS
                rewards["player"] -= WIN_BONUS

        truncations = {"player": False, "boss": False, "__all__": False}
        infos = {
            "player": {"damage_dealt": self.p1.damage_dealt_step, "damage_taken": self.p1.damage_taken_step},
            "boss": {"damage_dealt": self.p2.damage_dealt_step, "damage_taken": self.p2.damage_taken_step},
        }
        return obs, rewards, dones, truncations, infos
    
    def render(self):
        self.engine.render()

    def close(self):
        self.engine.close()
