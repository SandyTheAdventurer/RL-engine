import sys
import os
import time
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np

_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

from sample_factory.cfg.arguments import parse_full_cfg, parse_sf_args, load_from_checkpoint
from sample_factory.algo.utils.misc import ExperimentStatus
from sample_factory.algo.utils.rl_utils import prepare_and_normalize_obs
from sample_factory.model.actor_critic import create_actor_critic
from sample_factory.model.model_utils import get_rnn_size

import gymnasium as gym

from rl.pbt import register_multi_shooter_components, add_multi_shooter_env_args, multi_shooter_override_defaults
from sample_factory.enjoy import load_state_dict
from rl.pbt import MultiAgentShooterEnv, ENGINE_DT, AIM_DIRECTIONS, AIM_RADIUS, SCREENW, SCREENH

sys.path.append(os.path.abspath("build"))
import Game


def decode_action(action, center_xy):
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


def run_match(engine, human, bot, bot_model, device, rnn_size):
    rnn_states = torch.zeros([1, rnn_size], dtype=torch.float32, device=device)
    clock = time.time()

    while True:
        frame = Game.poll_events()
        if frame.quit:
            return False

        human_intent = Game.get_human_intent(frame)

        obs = engine.observe(bot, human)
        obs_t = torch.from_numpy(obs.copy()).unsqueeze(0).float()
        obs_dict = {"obs": obs_t}
        normalized_obs = prepare_and_normalize_obs(bot_model, obs_dict)
        policy_outputs = bot_model(normalized_obs, rnn_states)
        raw_actions = policy_outputs["actions"]
        rnn_states = policy_outputs["new_rnn_states"]

        act = raw_actions[0].cpu().numpy().astype(int)
        self_center = (obs[4] * SCREENW, obs[5] * SCREENH)
        bot_intent = decode_action(act, self_center)

        engine.step(human_intent, bot_intent, ENGINE_DT)
        engine.render()
        engine.present()

        target = clock + ENGINE_DT
        now = time.time()
        if now < target:
            time.sleep(target - now)
        clock = target

        if engine.is_done():
            Game.Visuals.end_screen(engine)
            while True:
                frame = Game.poll_events()
                if frame.mouse_left_clicked:
                    return False
                if frame.mouse_right_clicked:
                    break
                if frame.quit:
                    return False
            rnn_states = torch.zeros([1, rnn_size], dtype=torch.float32, device=device)
            engine.reset()

    return True

register_multi_shooter_components()
parser, partial_cfg = parse_sf_args(evaluation=True)
add_multi_shooter_env_args(parser)
multi_shooter_override_defaults(partial_cfg.env, parser)
cfg = parse_full_cfg(parser)
cfg = load_from_checkpoint(cfg)

device = torch.device("cpu" if cfg.device == "cpu" else "cuda")

temp_env = MultiAgentShooterEnv(render_mode=None, frame_skip=1)
obs_space = gym.spaces.Dict({"obs": temp_env.observation_space})
actor_critic = create_actor_critic(cfg, obs_space, temp_env.action_space)
actor_critic.eval()
actor_critic.model_to_device(device)
load_state_dict(cfg, actor_critic, device)
temp_env.close()

rnn_size = get_rnn_size(cfg)

human = Game.Player(0, 0, 200.0, "human")
bot = Game.Player(0, 0, 200.0, "bot")
engine = Game.Engine(True, True, human, bot, SCREENW, SCREENH)
Game.Visuals.init(engine, human, bot)

engine.reset()

Game.Visuals.start_screen(engine)
while True:
    frame = Game.poll_events()
    if frame.mouse_left_clicked:
        if not run_match(engine, human, bot, actor_critic, device, rnn_size):
            break
    if frame.quit:
        break

Game.Visuals.shutdown()
engine.close()
print(ExperimentStatus.SUCCESS)