import torch

_original_torch_load = torch.load

def _patched_torch_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _original_torch_load(*args, **kwargs)

torch.load = _patched_torch_load

from sample_factory.enjoy import enjoy
from sample_factory.cfg.arguments import parse_full_cfg, parse_sf_args

from rl.train_shooter import register_shooter_components, add_shooter_env_args, shooter_override_defaults

def main():
    register_shooter_components()
    parser, partial_cfg = parse_sf_args(evaluation=True)
    add_shooter_env_args(parser)
    shooter_override_defaults(partial_cfg.env, parser)
    cfg = parse_full_cfg(parser)
    status = enjoy(cfg)
    return status

if __name__ == "__main__":

    main()
