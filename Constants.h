#pragma once
#include "Controls.h"
inline constexpr int screenw {1080};
inline constexpr int screenh {720};
inline constexpr int playerw {100};
inline constexpr int playerh {100};
inline constexpr float playerspeed {300.0f};

inline struct Controls HumanControls{
    SDL_SCANCODE_W,
    SDL_SCANCODE_S,
    SDL_SCANCODE_A,
    SDL_SCANCODE_D
};

inline struct Controls BotControls{
    SDL_SCANCODE_UP,
    SDL_SCANCODE_DOWN,
    SDL_SCANCODE_LEFT,
    SDL_SCANCODE_RIGHT
};