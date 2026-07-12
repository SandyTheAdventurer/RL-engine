import functools

from build.Game import Engine, Player, PlayerIntent
from gymnasium import spaces
import numpy as np
from pettingzoo.utils.env import ParallelEnv

ENGINE_DT = 1.0 / 60.0
AIM_DIRECTIONS = 16
AIM_RADIUS = 1000.0
OBS_DIM = 88

sys_config = {
    "p1_init_x": -1.0,
    "p1_init_y": -1.0,
    "p1_init_speed": 200.0,
    "p2_init_x": -1.0,
    "p2_init_y": -1.0,
    "p2_init_speed": 200.0,
    "screenw": 1280,
    "screenh": 720}

class EngineEnv(ParallelEnv):
    metadata = {
            "name": "EngineEnv"
        }
    def __init__(self, render, sys_config, frame_skip=4):
        super().__init__()

        self.sys_config = sys_config
        self.frame_skip = frame_skip
        self.possible_agents = ["player", "boss"]
        self.p1 = Player(sys_config["p1_init_x"], sys_config["p1_init_y"], sys_config["p1_init_speed"], "player")
        self.p2 = Player(sys_config["p2_init_x"], sys_config["p2_init_y"], sys_config["p2_init_speed"], "boss")

        self.engine = Engine(render, render, self.p1, self.p2, sys_config["screenw"], sys_config["screenh"])

        self.players = {"player": self.p1, "boss": self.p2}
        self.agents = self.possible_agents[:]
        self._prev_healths = {a: self.players[a].health for a in self.possible_agents}

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent):
        return spaces.Box(-np.inf, np.inf, [OBS_DIM], dtype=np.float32)
    
    @functools.lru_cache(maxsize=None)
    def action_space(self, agent):
        return spaces.MultiDiscrete([3, 3, 2, 2, 2, AIM_DIRECTIONS, 2])
    
    def _get_obs(self):
        return {"player": self.engine.observe(self.p1, self.p2),
                "boss": self.engine.observe(self.p1, self.p2)}
    
    def _decode_action(self, action, player: Player):
        mx = int(action[0]) - 1
        my = int(action[1]) - 1
        fire = bool(action[2])
        dash = bool(action[3])
        spell = bool(action[4])
        angle = int(action[5]) * (2 * np.pi / AIM_DIRECTIONS)
        aimx = player.px + np.cos(angle) * AIM_RADIUS
        aimy = player.py + np.sin(angle) * AIM_RADIUS
        attack = bool(action[6])
        return PlayerIntent(mx, my, fire, dash, spell, aimx, aimy, attack)

    def reset(self, seed = None, options = None):
        self.agents = self.possible_agents[:]
        self.engine.reset(self.sys_config["p1_init_x"], self.sys_config["p1_init_y"], self.sys_config["p2_init_x"], self.sys_config["p2_init_y"])
        self._prev_healths = {a: self.players[a].health for a in self.agents}
        infos = {a: {} for a in self.agents}
        return self._get_obs(), infos
    
    def reward(self, me: str, he: str):
        delta_me = self.players[me].health - self._prev_healths[me]
        delta_he = self.players[he].health - self._prev_healths[he]
        return delta_me - delta_he
    
    def step(self, actions):
        p1_action = self._decode_action(actions["player"], self.p1)
        p2_action = self._decode_action(actions["boss"], self.p2)

        for _ in range(self.frame_skip):
            self.engine.step(p1_action, p2_action, ENGINE_DT)
            if self.engine.is_done():
                break

        obs = self._get_obs()

        rewards = {"player": self.reward("player", "boss"), "boss": self.reward("boss", "player")}
        self._prev_healths = {a: self.players[a].health for a in self.possible_agents}
        
        dones = {"player": self.engine.is_done(), "boss": self.engine.is_done(), "__all__": self.engine.is_done()}
        truncations = {"player": False, "boss": False, "__all__": False}
        infos = {a: {} for a in self.agents}
        return obs, rewards, dones, truncations, infos
    
    def render(self):
        self.engine.render()

    def close(self):
        self.engine.close()