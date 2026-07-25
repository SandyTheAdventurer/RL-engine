import math
import torch
from rl.ppo import PPO
from rl.gail import Discriminator


def test_ppo_forward_backward():
    obs_dim = 4
    action_nvec = [2]
    num_steps = 10
    num_envs = 2

    ppo = PPO(obs_dim, action_nvec)
    ppo.init_buffers(num_steps, num_envs)

    assert ppo.num_steps == num_steps
    assert ppo.num_envs == num_envs
    assert ppo.step_idx == 0

    lstm_state = (
        torch.zeros(ppo.lstm.num_layers, num_envs, ppo.lstm.hidden_size),
        torch.zeros(ppo.lstm.num_layers, num_envs, ppo.lstm.hidden_size),
    )

    for t in range(num_steps):
        obs = torch.randn(num_envs, obs_dim)
        done = torch.zeros(num_envs)
        action, lstm_state = ppo.act(obs, lstm_state, done, inference=False)
        ppo.store_reward(torch.ones(num_envs))

    assert ppo.is_buffer_full()
    assert ppo.step_idx == num_steps
    assert ppo.initial_lstm_state is not None

    # Verify buffer contents are populated
    assert ppo.obs_buf.sum() != 0, "obs_buf is empty"
    assert ppo.actions_buf.sum() != 0, "actions_buf is empty"
    assert ppo.logprobs_buf.sum() != 0, "logprobs_buf is empty"
    assert ppo.rewards_buf.sum() != 0, "rewards_buf is empty"
    assert ppo.values_buf.sum() != 0, "values_buf is empty"

    # Test inference mode does not modify buffer
    pre_step_idx = ppo.step_idx
    pre_obs_buf = ppo.obs_buf.clone()
    inf_action, _ = ppo.act(
        torch.randn(num_envs, obs_dim), lstm_state, torch.zeros(num_envs), inference=True
    )
    assert ppo.step_idx == pre_step_idx, "inference mode modified step_idx"
    assert torch.equal(ppo.obs_buf, pre_obs_buf), "inference mode modified obs_buf"
    assert inf_action.shape == (num_steps, num_envs) or inf_action.shape == (num_envs, len(action_nvec))

    next_obs = torch.randn(num_envs, obs_dim)
    next_done = torch.zeros(num_envs)

    class Args:
        gamma = 0.99
        gae_lambda = 0.95
        num_steps = 10
        num_envs = 2
        batch_size = 20
        num_minibatches = 2
        update_epochs = 1
        norm_adv = True
        clip_coef = 0.2
        clip_vloss = True
        ent_coef = 0.01
        vf_coef = 0.5
        max_grad_norm = 0.5
        target_kl = None

    optimizer = torch.optim.Adam(ppo.parameters(), lr=1e-3)

    before_params = {name: p.clone() for name, p in ppo.named_parameters()}

    metrics = ppo.update(optimizer, Args(), next_obs, next_done, lstm_state)

    # Verify all expected metric keys exist
    expected_keys = {"pg_loss", "v_loss", "entropy_loss", "approx_kl", "clipfrac", "explained_var"}
    assert expected_keys.issubset(metrics.keys()), f"Missing metric keys: {expected_keys - metrics.keys()}"

    # Verify metric values are finite
    for key in expected_keys:
        val = metrics[key]
        if isinstance(val, float):
            assert math.isfinite(val), f"Metric {key} is not finite: {val}"
        elif isinstance(val, torch.Tensor):
            assert torch.isfinite(val).all(), f"Metric {key} contains non-finite values"

    # v_loss should be non-negative (squared error)
    assert metrics["v_loss"] >= 0, f"v_loss is negative: {metrics['v_loss']}"

    # clipfrac should be in [0, 1]
    assert 0.0 <= metrics["clipfrac"] <= 1.0, f"clipfrac out of range: {metrics['clipfrac']}"

    # Buffer should be reset after update
    assert ppo.step_idx == 0, "step_idx not reset after update"

    # Verify ALL parameter groups changed (network + actor + critic)
    changed_count = 0
    total_count = 0
    for name, p in ppo.named_parameters():
        total_count += 1
        if not torch.equal(p, before_params[name]):
            changed_count += 1

    assert changed_count > 0, "No parameters changed after update"
    assert changed_count == total_count, (
        f"Only {changed_count}/{total_count} parameter groups changed after update"
    )


def test_discriminator_forward_backward():
    obs_dim = 4
    action_dim = 2
    disc = Discriminator(obs_dim + action_dim, hidden_dim=64, lstm_hidden=32)

    seq_len = 10
    batch_size = 2

    obs = torch.randn(seq_len, batch_size, obs_dim)
    actions = torch.randn(seq_len, batch_size, action_dim)

    # Test without hx/cx (auto-init zeros)
    out, hx, cx = disc(obs, actions)
    assert out.shape == (seq_len, batch_size, 1)
    assert hx.shape == (disc.lstm.num_layers, batch_size, disc.lstm.hidden_size)
    assert cx.shape == (disc.lstm.num_layers, batch_size, disc.lstm.hidden_size)

    # Output should be in [0, 1] (sigmoid)
    assert (out >= 0).all() and (out <= 1).all(), f"Discriminator output not in [0,1]: min={out.min():.4f}, max={out.max():.4f}"

    # hx/cx should have been updated from zeros
    assert hx.abs().sum() > 0, "hx is all zeros after forward"
    assert cx.abs().sum() > 0, "cx is all zeros after forward"

    # Test with explicit hx/cx input
    hx_init = torch.randn(disc.lstm.num_layers, batch_size, disc.lstm.hidden_size)
    cx_init = torch.randn(disc.lstm.num_layers, batch_size, disc.lstm.hidden_size)
    out2, hx2, cx2 = disc(obs, actions, hx=hx_init, cx=cx_init)
    assert out2.shape == (seq_len, batch_size, 1)
    # Hidden state should differ from initial input
    assert not torch.equal(hx2, hx_init), "hx unchanged after forward with explicit state"

    # Test with done flags (masking midway)
    done = torch.zeros(seq_len, batch_size)
    done[5, :] = 1.0

    out_done, hx_done, cx_done = disc(obs, actions, done=done)
    assert out_done.shape == (seq_len, batch_size, 1)
    assert (out_done >= 0).all() and (out_done <= 1).all()

    # Forward without done for comparison — outputs should differ after t=5
    out_nodone, hx_nodone, cx_nodone = disc(obs, actions, done=torch.zeros(seq_len, batch_size))
    # After the done reset at t=5, the outputs at t=5+ should differ from the no-done case
    diff_after_done = (out_done[6:] - out_nodone[6:]).abs().sum()
    assert diff_after_done > 0, "Done masking had no effect on output after done timestep"

    # Test single-sample forward (batch_size=1, no seq dim)
    single_obs = torch.randn(1, obs_dim)
    single_actions = torch.randn(1, action_dim)
    out_single, hx_s, cx_s = disc(single_obs, single_actions)
    assert out_single.shape == (1, 1)
    assert (out_single >= 0).all() and (out_single <= 1).all()

    # Backward pass — all parameter groups should get gradients
    target = torch.ones_like(out_done)
    loss = torch.nn.functional.binary_cross_entropy(out_done, target)

    disc.optim.zero_grad()
    loss.backward()
    disc.optim.step()

    assert disc.pre_lstm[0].weight.grad is not None, "pre_lstm gradient is None"
    assert disc.pre_lstm[2].weight.grad is not None, "pre_lstm[2] gradient is None"
    assert disc.lstm.weight_ih_l0.grad is not None, "lstm weight_ih gradient is None"
    assert disc.lstm.weight_hh_l0.grad is not None, "lstm weight_hh gradient is None"
    assert disc.post_lstm[2].weight.grad is not None, "post_lstm gradient is None"
