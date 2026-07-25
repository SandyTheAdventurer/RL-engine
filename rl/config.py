import json
import os
import sys
import logging
import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config.json")

_cfg = None

def _load():
    global _cfg
    if _cfg is None:
        with open(_CONFIG_PATH) as f:
            _cfg = json.load(f)
    return _cfg

def get(key, default=None):
    return _load().get(key, default)

def screenw():       return get("screenw", 1280)
def screenh():       return get("screenh", 720)
def playerspeed():   return get("playerspeed", 200.0)
def aim_directions(): return get("aim_directions", 16)
def aim_radius():    return get("aim_radius", 1000.0)
def frame_skip():    return get("frame_skip", 4)
def test_bot():      return get("test_bot", "hard")
def num_envs():      return get("num_envs", 16)
def pop_size():      return get("pop_size", 4)
def steps_per_gen(): return get("steps_per_gen", 2048)
def num_steps():     return get("num_steps", 64)
def min_expert_frames(): return get("min_expert_frames", 512)
def max_expert_frames(): return get("max_expert_frames", 512)
def disc_lr():       return get("disc_lr", 1e-4)
def gen_lr():        return get("gen_lr", 2.5e-4)
def gen_lr_range():  return (get("gen_lr_range_min", 1e-5), get("gen_lr_range_max", 1e-3))
def disc_lr_range(): return (get("disc_lr_range_min", 1e-5), get("disc_lr_range_max", 1e-3))
def num_minibatches(): return get("num_minibatches", 4)
def update_epochs():   return get("update_epochs", 4)
def gamma():         return get("gamma", 0.99)
def gae_lambda():    return get("gae_lambda", 0.95)
def clip_coef():     return get("clip_coef", 0.2)
def ent_coef():      return get("ent_coef", 0.01)
def vf_coef():       return get("vf_coef", 0.5)
def max_grad_norm(): return get("max_grad_norm", 0.5)
def reward_alpha():   return get("reward_alpha", 0.5)
def label_smoothing(): return get("label_smoothing", 0.1)
def disc_grad_norm(): return get("disc_grad_norm", 1.0)

# ---------------------------------------------------------------------------
# Logging / MLFlow
# ---------------------------------------------------------------------------
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

_run_active = False
_active_run_id = None
_mlflow_client = None

def setup_logging(level=logging.INFO):
    fmt = "[%(asctime)s] [%(name)s] %(levelname)s: %(message)s"
    datefmt = "%H:%M:%S"
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

def init_mlflow(project="rl-engine", run_name="run"):
    global _run_active, _active_run_id, _mlflow_client
    if not MLFLOW_AVAILABLE:
        return
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "mlflow.db")
    mlflow.set_tracking_uri(f"sqlite:///{db_path}")
    mlflow.set_experiment(project)
    run = mlflow.start_run(run_name=run_name, nested=False)
    _active_run_id = run.info.run_id
    _mlflow_client = mlflow.MlflowClient()
    _run_active = True

def end_mlflow():
    global _run_active, _active_run_id, _mlflow_client
    if not MLFLOW_AVAILABLE or not _run_active:
        return
    mlflow.end_run()
    _run_active = False
    _active_run_id = None
    _mlflow_client = None

def log_metrics(metrics: dict, step: int = None):
    if not MLFLOW_AVAILABLE or not _run_active:
        return
    mlflow.log_metrics(metrics, step=step)

# ---------------------------------------------------------------------------
# Intent encoding
# ---------------------------------------------------------------------------
def encode_human_intent(intent, player):
    mx = intent.mx + 1
    my = intent.my + 1
    fire = 1 if intent.fire else 0
    dash = 1 if intent.dash else 0
    spell = 1 if intent.selected_spell else 0

    dx = intent.aim_x - player.px
    dy = intent.aim_y - player.py
    angle = np.arctan2(dy, dx)
    if angle < 0:
        angle += 2 * np.pi

    _dirs = aim_directions()
    aim_bin = int(round(angle / (2 * np.pi / _dirs)))
    if aim_bin >= _dirs:
        aim_bin = _dirs - 1

    attack = 1 if intent.attack else 0
    return np.array([mx, my, fire, dash, spell, aim_bin, attack], dtype=np.float32)

# ---------------------------------------------------------------------------
# Running observation normalisation (Welford's online algorithm)
# ---------------------------------------------------------------------------
class RunningMeanStd:
    """Tracks running mean/variance with Welford's algorithm."""

    def __init__(self, shape=(), device="cpu"):
        import torch
        self.mean = torch.zeros(shape, dtype=torch.float32, device=device)
        self.var = torch.ones(shape, dtype=torch.float32, device=device)
        self.inv_std = torch.ones(shape, dtype=torch.float32, device=device)
        self.count = 1e-4

    def update(self, x):
        """x: tensor of shape (batch, *shape) or (*shape)."""
        batch = x.reshape(-1, *self.mean.shape) if x.dim() > len(self.mean.shape) else x.unsqueeze(0)
        batch_mean = batch.mean(dim=0)
        batch_var = batch.var(dim=0, unbiased=False)
        batch_count = batch.shape[0]
        self._update_from_moments(batch_mean, batch_var, batch_count)

    def _update_from_moments(self, batch_mean, batch_var, batch_count):
        import torch
        delta = batch_mean - self.mean
        total = self.count + batch_count
        new_mean = self.mean + delta * batch_count / total
        m_a = self.var * self.count
        m_b = batch_var * batch_count
        m2 = m_a + m_b + delta.pow(2) * self.count * batch_count / total
        self.mean = new_mean
        self.var = m2 / total
        self.count = total
        self.inv_std = torch.clamp(self.var, min=1e-8).rsqrt()

    def normalize(self, x, clip=5.0):
        """Normalise tensor x using tracked statistics, clip to [-clip, clip]."""
        import torch
        return torch.clamp((x - self.mean) * self.inv_std, -clip, clip)

    def update_and_normalize(self, x, clip=5.0):
        """Update running stats from x, then return normalized x."""
        import torch
        batch = x.reshape(-1, *self.mean.shape) if x.dim() > len(self.mean.shape) else x.unsqueeze(0)
        batch_mean = batch.mean(dim=0)
        batch_var = batch.var(dim=0, unbiased=False)
        batch_count = batch.shape[0]
        self._update_from_moments(batch_mean, batch_var, batch_count)
        return torch.clamp((x - self.mean) * self.inv_std, -clip, clip)

    def state_dict(self):
        return {"mean": self.mean.clone(), "var": self.var.clone(), "count": float(self.count)}

    def load_state_dict(self, d):
        import torch
        self.mean = d["mean"].clone() if isinstance(d["mean"], torch.Tensor) else torch.tensor(d["mean"], dtype=torch.float32)
        self.var = d["var"].clone() if isinstance(d["var"], torch.Tensor) else torch.tensor(d["var"], dtype=torch.float32)
        self.count = float(d["count"])
        self.inv_std = torch.clamp(self.var, min=1e-8).rsqrt()
