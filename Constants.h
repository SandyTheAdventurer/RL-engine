#pragma once
#include "Structures.h"
#include <map>

inline constexpr int screenw {1080};
inline constexpr int screenh {720};
inline constexpr int playerw {150};
inline constexpr int playerh {150};
inline constexpr float playerspeed {300.0f};
inline constexpr float spritechange {1.0f / 10};
inline constexpr float hitbox_size {24.0f};

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

inline std::map<std::pair<int,int>, int> dirIndex = {
    {{ 1,-1}, 0},
    {{ 0,-1}, 1},
    {{-1,-1}, 2},
    {{-1, 0}, 3},
    {{-1, 1}, 4},
    {{ 0, 1}, 5},
    {{ 1, 1}, 6},
    {{ 1, 0}, 7}
};