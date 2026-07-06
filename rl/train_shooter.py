from sample_factory.envs.env_utils import register_env
from sample_factory.train import run_rl
from sample_factory.cfg.arguments import parse_full_cfg, parse_sf_args
from rl.shooter_env import ShooterEnv

def make_shooter_env(full_env_name, cfg=None, env_config=None, render_mode=None):
    frame_skip = getattr(cfg, "frame_skip", 4)
    opponent = getattr(cfg, "opponent", "medium")

    if opponent == "none":
        opponent = None

    render = render_mode is not None
    return ShooterEnv(frame_skip=frame_skip, render=render, opponent=opponent)

def register_shooter_components():
    register_env("shooter_v1", make_shooter_env)

def add_shooter_env_args(parser):
    parser.add_argument(
        "--frame_skip",
        default=4,
        type=int,
        help="Number of engine ticks each PlayerIntent is held for per env.step()",
    )

    parser.add_argument(
        "--opponent",
        default="medium",
        choices=["easy", "medium", "hard", "expert", "none", "human"],
        help="Scripted bot (from bots.py) to train against; 'none' = idle opponent",
    )

def shooter_override_defaults(_env_name, parser):
    parser.set_defaults(
        encoder_type="mlp",
        encoder_mlp_layers=[256, 256],
        use_rnn=False,
        recurrence=1,
        rollout=64,
        batch_size=2048,
        num_batches_per_epoch=1,
        ppo_epochs=2,
        ppo_clip_ratio=0.2,
        gamma=0.99,
        gae_lambda=0.95,
        learning_rate=3e-4,
        value_loss_coeff=0.5,
        exploration_loss_coeff=0.003,
        max_grad_norm=4.0,
        normalize_input=True,
        normalize_returns=True,
        reward_scale=1.0,
        num_workers=12,
        num_envs_per_worker=4,
        worker_num_splits=2,
        async_rl=True,
        train_for_env_steps=int(15_000_000),
        save_every_sec=60,
        experiment_summaries_interval=10,
    )

def main():

    register_shooter_components()
    parser, partial_cfg = parse_sf_args()
    add_shooter_env_args(parser)
    shooter_override_defaults(partial_cfg.env, parser)
    cfg = parse_full_cfg(parser)
    status = run_rl(cfg)
    return status

if __name__ == "__main__":

    main()
