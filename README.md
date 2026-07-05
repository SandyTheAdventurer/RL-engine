# RL Engine (Name subject to change)

This is an 2D souls-like game with melee + ranged combat, scripted bots, and PPO/PBT reinforcement learning training (more to come!!!).

## Dependencies

- **System**: SDL3, SDL3\_image, SDL3\_ttf, CMake, C++17 compiler, Python 3.11
- **Python** (via `uv pip install -r requirements.txt`): gymnasium, numpy, torch, sample-factory (GitHub master), pybind11, opencv-python, wandb, etc.

CMake will auto-fetch SDL3 from source (no system packages required). You just need:

- **CMake** ≥ 3.20
- **C++17 compiler** (gcc, clang, or MSVC)
- **Python 3.11** with venv module

### Ubuntu / WSL

```sh
sudo apt install build-essential cmake python3.11-dev python3.11-venv

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Arch Linux

```sh
sudo pacman -S gcc cmake python3.11

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (Game only, no RL training — not tested)
Install [Visual Studio Community](https://visualstudio.microsoft.com/vs/community/) with the *Desktop development with C++* workload (or use [MSYS2](https://www.msys2.org/)), and [CMake](https://cmake.org/).

## Build

```sh
cmake -B build -DPython_EXECUTABLE=$PWD/.venv/bin/python3.11
cmake --build build -j$(nproc)
```

The output is `build/Game.cpython-311-<arch>-linux-gnu.so`, a pybind11 module.

## Note on Windows

Sample Factory does not support Windows. RL training (single-agent and PBT) requires a Linux environment. The game engine itself (C++ with SDL3 + pybind11) compiles on Windows, but training will not work there.

## Combat

- **Melee**: 3-hit combo (1.0× / 1.3× / 1.8× damage). Press attack 3 times within the combo window to chain. Firing resets the combo.
- **Shoot**: 6-round magazine, 0.4s fire rate, 1.5s reload. Auto-reloads when empty.
- **Dash**: 100px blink, 0.2s duration, iframe, pass-through. Cannot attack or deal damage while dashing.
- **Reward shaping** (training): hit bonus, ammo penalty, distance urge, kill/death ±25.

## Run

### Human vs bot (standalone)
```sh
python test.py
```

### Human vs PBT-trained model
```sh
python rl/human_vs_pbt.py --experiment_dir=<path_to_experiment>
```

### Train single-agent
```sh
python -m rl.shooter_env --train_dir=./train_dir --experiment=shooter_v1
```

### Train PBT (self-play, 4-policy population)
```sh
python rl/pbt --train_dir=./train_dir --experiment=shooter_pbt
```

### Use SF's built-in enjoy (single-agent)
```sh
python rl/enjoy.py --experiment_dir=<path>
```

### Use SF's built-in enjoy (PBT)
```sh
python rl/enjoy_pbt.py --experiment_dir=<path>
```
## Controls

| Input | Action |
|---|---|
| WASD | Move |
| Left click | Melee attack (mouse direction) |
| Right click | Shoot (mouse aim) |
| Shift | Dash (iframe blink, invincible) |
| R | Reload |

## Credits

- **Knight sprites** — [smallscaleint](https://smallscaleint.itch.io/) (Idle, Walk, Run, CastSpell, Melee, Melee2, MeleeSpin, TakeDamage, Die, and more)