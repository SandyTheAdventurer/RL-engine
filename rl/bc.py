import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.utils.data import DataLoader
try:
    from rl.utils import *
except ImportError:
    from utils import *

class BC(nn.Module):
    def __init__(self, config: dict, device='cpu'):
        super().__init__()
        self.device = torch.device(device)
        self.input_dim = config["input_dim"]
        self.hidden_dim = config["hidden_dim"]
        self.n_layers = config["n_layers"]
        self.batch_size = config["batch_size"]
        self.screenw = config["screenw"]
        self.screenh = config["screenh"]
        
        # Loss weighting from config (with defaults)
        self.w_move = config.get("w_move", 1.0)
        self.w_fire = config.get("w_fire", 5.0)
        self.w_aim = config.get("w_aim", 0.5)
        dropout_rate = config.get("dropout", 0.1)

        act_cls = {'relu': nn.ReLU, 'gelu': nn.GELU}.get(config.get("activation", "relu"), nn.ReLU)

        # Added Dropout to prevent overfitting on expert trajectories
        layers = [
            nn.Linear(self.input_dim, self.hidden_dim), 
            act_cls(),
            nn.Dropout(dropout_rate)
        ]
        for _ in range(self.n_layers):
            layers += [
                nn.Linear(self.hidden_dim, self.hidden_dim), 
                act_cls(),
                nn.Dropout(dropout_rate)
            ]

        self.network = nn.Sequential(*layers)
        self.mx_head = nn.Linear(self.hidden_dim, 3)
        self.my_head = nn.Linear(self.hidden_dim, 3)
        self.fire_head = nn.Linear(self.hidden_dim, 1)
        self.aim_mean = nn.Linear(self.hidden_dim, 2)
        self.aim_log_std = nn.Linear(self.hidden_dim, 2)

        self.optim = torch.optim.Adam(self.parameters(), lr=config['lr'])

        self.to(self.device)

    def preprocess(self, path):
        with open(path) as f:
            raw = pd.read_json(f, lines=True)
        actions = pd.json_normalize(raw["expert_action"])
        
        # Clamped actions to ensure they stay within expected bounds
        mx_vals = np.clip(actions["mx"].values, -1, 1)
        my_vals = np.clip(actions["my"].values, -1, 1)
        fire_vals = actions["fire"].values.astype(np.float32)
        aim_x = np.clip(actions["aim_x"].values / self.screenw * 2 - 1, -1, 1)
        aim_y = np.clip(actions["aim_y"].values / self.screenh * 2 - 1, -1, 1)

        obs_df = pd.json_normalize(raw["self"])
        obs_flat = np.stack(obs_df.apply(flatten_obs, 1).values).astype(np.float32)

        # Original hardcoded normalization retained
        self.norm = np.array([
            1000, 1000, self.screenw, self.screenh, self.screenw, self.screenh, 200, 200,
            *[1]*6, *[1]*6,
            *[self.screenw, self.screenh]*12,
            *[750, 750]*12,
        ], dtype=np.float32)
        obs_flat = np.clip(obs_flat / self.norm, -1, 1)

        health = obs_flat[:, 0]
        prev_health = np.roll(health, 1)
        prev_health[0] = health[0]
        x = obs_flat[:, 2]
        y = obs_flat[:, 3]
        is_reset = (health == 1.0) & (prev_health < 1.0) & \
                   (np.abs(x - 240/self.screenw) < 0.02) & \
                   (np.abs(y - 285/self.screenh) < 0.02)
        boundaries = np.where(is_reset)[0]

        # Keep episode IDs on CPU initially
        self.episode_ids = torch.zeros(len(obs_flat), dtype=torch.int32)
        for b in boundaries:
            self.episode_ids[b:] += 1

        is_active = (mx_vals != 0) | (my_vals != 0) | (fire_vals > 0.5)
        weights = np.where(is_active, 6.0, 1.0).astype(np.float32)

        # Removed .to(self.device) to prevent GPU memory crashes during preprocessing
        self.obs = torch.tensor(obs_flat, dtype=torch.float32)
        self.mx = torch.tensor(mx_vals + 1, dtype=torch.long)
        self.my = torch.tensor(my_vals + 1, dtype=torch.long)
        self.fire = torch.tensor(fire_vals, dtype=torch.float32)
        self.aim = torch.tensor(np.column_stack([aim_x, aim_y]), dtype=torch.float32)
        self.weights = torch.tensor(weights, dtype=torch.float32)

    def forward(self, obs):
        h = self.network(obs)
        return self.mx_head(h), self.my_head(h), self.fire_head(h), \
               self.aim_mean(h), torch.clamp(self.aim_log_std(h), -3, 3)

    def sample(self, obs):
        h = self.network(obs)
        mx_probs = torch.softmax(self.mx_head(h), dim=1)
        my_probs = torch.softmax(self.my_head(h), dim=1)
        fire_prob = torch.sigmoid(self.fire_head(h))
        aim_mu = self.aim_mean(h)
        aim_sigma = torch.exp(torch.clamp(self.aim_log_std(h), -3, 3))

        mx = torch.distributions.Categorical(mx_probs).sample()
        my = torch.distributions.Categorical(my_probs).sample()
        fire = torch.distributions.Bernoulli(fire_prob).sample()
        aim = TanhGaussian(aim_mu, aim_sigma).sample()

        aim_x = scale(aim[..., 0], 0, self.screenw)
        aim_y = scale(aim[..., 1], 0, self.screenh)

        return mx.item(), my.item(), bool(fire.item()), aim_x.item(), aim_y.item()

    def compute_loss(self, batch):
        obs, mx_gt, my_gt, fire_gt, aim_gt, weights = batch
        mx_logits, my_logits, fire_logit, aim_mu, aim_log_sigma = self(obs)

        loss_mx = F.cross_entropy(mx_logits, mx_gt, reduction='none')
        loss_my = F.cross_entropy(my_logits, my_gt, reduction='none')
        loss_fire = F.binary_cross_entropy_with_logits(
            fire_logit.squeeze(1), fire_gt, reduction='none'
        )
        aim_std = torch.exp(aim_log_sigma)
        aim_dist = TanhGaussian(aim_mu, aim_std)
        aim_clamped = torch.clamp(aim_gt, -0.999, 0.999)
        loss_aim = -aim_dist.log_prob(aim_clamped).mean(dim=1)

        # Scaled multi-task loss calculation
        per_frame = (loss_mx + loss_my) * self.w_move + (loss_fire * self.w_fire) + (loss_aim * self.w_aim)
        return (weights * per_frame).mean()

    def learn(self, n_epochs=10, val_split=0.2):
        n_eps = self.episode_ids.max().item() + 1
        if n_eps > 1:
            n_val = max(1, int(n_eps * val_split))
            perm = torch.randperm(n_eps)
            val_eps = set(perm[:n_val].tolist())
            train_mask = torch.tensor([e not in val_eps for e in self.episode_ids.tolist()])
        else:
            n = len(self.obs)
            n_val = int(n * val_split)
            perm = torch.randperm(n)
            train_mask = torch.ones(n, dtype=torch.bool)
            train_mask[perm[:n_val]] = False
        val_mask = ~train_mask

        train_ds = BCDataset(self.obs[train_mask], self.mx[train_mask],
                             self.my[train_mask], self.fire[train_mask],
                             self.aim[train_mask], self.weights[train_mask])
        val_ds = BCDataset(self.obs[val_mask], self.mx[val_mask],
                           self.my[val_mask], self.fire[val_mask],
                           self.aim[val_mask], self.weights[val_mask])

        train_loader = DataLoader(train_ds, self.batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, self.batch_size, shuffle=False)

        for epoch in range(n_epochs):
            self.train()
            train_loss = 0.0
            for batch in train_loader:
                # Move batch to target device dynamically
                batch = [b.to(self.device) for b in batch]
                
                loss = self.compute_loss(batch)
                self.optim.zero_grad()
                loss.backward()
                self.optim.step()
                train_loss += loss.item() * len(batch[0])

            self.eval()
            val_loss = 0.0
            with torch.no_grad():
                for batch in val_loader:
                    # Move batch to target device dynamically
                    batch = [b.to(self.device) for b in batch]
                    
                    loss = self.compute_loss(batch)
                    val_loss += loss.item() * len(batch[0])

            train_loss /= len(train_ds)
            val_loss /= len(val_ds)

            print(f"Epoch {epoch+1:3d}/{n_epochs}  train_loss={train_loss:.4f}  val_loss={val_loss:.4f}")

    def save(self, path):
        torch.save(self.state_dict(), path if path.endswith(".pt") else f"rl/{path}.pt")
    
    def load(self, path):
        self.load_state_dict(torch.load(path))