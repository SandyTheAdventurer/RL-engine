import torch
import numpy as np
from torch.utils.data import Dataset
import sys
import os
sys.path.append(os.path.abspath("./build"))
from Game import PlayerIntent

class TanhGaussian(torch.distributions.TransformedDistribution):
    def __init__(self, loc, scale):
        self.base_dist = torch.distributions.Normal(loc, scale)
        # cache_size=0 prevents a known memory leak in PyTorch's TransformedDistribution
        self.transforms = [torch.distributions.transforms.TanhTransform(cache_size=0)]
        super().__init__(self.base_dist, self.transforms)

    @property
    def mean(self):
        return torch.tanh(self.base_dist.mean)

    def entropy(self):
        x = self.rsample((1,))
        return -self.log_prob(x).squeeze(0)

class BCDataset(Dataset):
    def __init__(self, obs, mx, my, fire, aim, weights):
        self.obs = obs
        self.mx = mx
        self.my = my
        self.fire = fire
        self.aim = aim
        self.weights = weights

    def __len__(self):
        return len(self.obs)

    def __getitem__(self, idx):
        return (self.obs[idx], self.mx[idx], self.my[idx],
                self.fire[idx], self.aim[idx], self.weights[idx])

def scale(value: torch.Tensor, min: int, max:int) -> torch.Tensor:
    value = (value + 1) / 2
    return min + value * (max-min)

def flatten_obs(row):

    health = [row['health']]
    enemy_health = [row['enemy_health']]
    x = [row['x']]
    y = [row['y']]
    enemy_x = [row['enemy_x']]
    enemy_y = [row['enemy_y']]
    vx = [row.get('vx', 0.0)]
    vy = [row.get('vy', 0.0)]
    enemy_vx = [row.get('enemy_vx', 0.0)]
    enemy_vy = [row.get('enemy_vy', 0.0)]
    
    bullets_fired = np.atleast_1d(np.array(row['bullets_fired'], dtype=np.float32))
    bullets_reloaded = np.atleast_1d(np.array(row['bullets_reloaded'], dtype=np.float32))
    
    bullets_pos = np.atleast_1d(np.array(row['bullets_pos'], dtype=np.float32).flatten())
    bullets_vel = np.atleast_1d(np.array(row['bullets_vel'], dtype=np.float32).flatten())
    
    obs = np.concatenate([
        health, enemy_health, x, y, enemy_x, enemy_y,
        vx, vy, enemy_vx, enemy_vy,
        bullets_fired, bullets_reloaded, 
        bullets_pos, bullets_vel
    ])
    return obs

def to_tensor(obs, device):
    """Converts a flat numpy array to a batched PyTorch tensor."""
    return torch.tensor(obs, dtype=torch.float32, device=device).unsqueeze(0)

def get_intent() -> PlayerIntent:
    pass