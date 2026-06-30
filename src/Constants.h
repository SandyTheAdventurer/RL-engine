#pragma once
#include <map>

inline constexpr int screenw {1080};
inline constexpr int screenh {720};
inline constexpr int playerw {150};
inline constexpr int playerh {150};
inline constexpr float playerspeed {200.0f};
inline constexpr int max_health = {1000};
inline constexpr float spritechange {1.0f / 30};
inline constexpr float hitbox_size {24.0f};
inline constexpr float bullet_speed {750.0f};
inline constexpr float bullet_damage {100.0f};
inline constexpr int bulletw {30};
inline constexpr int bulleth {30};
inline constexpr int max_bullets {12};
inline constexpr int font_size {20};
inline constexpr float bar_h {10.0f};
inline constexpr float bar_y_offset {15.0f};

enum class GameState {
    START,
    PLAYING,
    TRAINING,
    END
};

struct FrameInput {
    bool quit = false;
    bool mouse_left_clicked = false;
    bool mouse_right_clicked = false;
    float mouse_x, mouse_y;
};

struct PlayerIntent {
    int mx = 0, my = 0;
    bool fire = false;
    float aim_x = 0, aim_y = 0;
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