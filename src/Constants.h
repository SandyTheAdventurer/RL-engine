#pragma once
#include <map>

inline constexpr int screenw {1080};
inline constexpr int screenh {720};
inline constexpr int playerw {150};
inline constexpr int playerh {150};
inline constexpr float playerspeed {200.0f};
inline constexpr int max_health = {100};
inline constexpr float spritechange {1.0f / 30};
inline constexpr float fire_spritechange {1.0f / 60};
inline constexpr float attack_spritechange {1.0f / 25};
inline constexpr float hurt_flash_duration = 0.12f;
inline constexpr float hitbox_size {24.0f};
inline constexpr float bullet_speed {750.0f};

inline constexpr int bulletw {30};
inline constexpr int bulleth {30};
inline constexpr int max_bullets {12};
inline constexpr int max_ammo {6};
inline constexpr float fire_rate {0.4f};
inline constexpr float reload_time {1.5f};
inline constexpr int font_size {20};
inline constexpr float bar_h {10.0f};
inline constexpr float bar_y_offset {15.0f};
inline constexpr float max_dist {1298.0f};

inline constexpr float melee_damage = 12.0f;
inline constexpr float melee_range = 65.0f;
inline constexpr float melee_cooldown = 0.2f;
inline constexpr float combo_window = 0.4f;
inline constexpr int max_combo_stage = 2;

inline constexpr float dash_distance = 100.0f;
inline constexpr float dash_blink_duration = 0.2f;
inline constexpr float dash_cooldown = 0.3f;
inline constexpr float dash_speed = dash_distance / dash_blink_duration;

inline constexpr const char* idle_sheet_path = {"assets/1Knight/Idle_Shadowless.png"};
inline constexpr const char* walk_sheet_path = {"assets/1Knight/Walk_Shadowless.png"};
inline constexpr const char* run_sheet_path = {"assets/1Knight/Run_Shadowless.png"};
inline constexpr const char* shoot_sheet_path = {"assets/1Knight/CastSpell_Shadowless.png"};
inline constexpr const char* bullet_sheet_path = {"assets/bullet.png"};
inline constexpr const char* melee1_sheet_path = {"assets/1Knight/Melee_Shadowless.png"};
inline constexpr const char* melee2_sheet_path = {"assets/1Knight/Melee2_Shadowless.png"};
inline constexpr const char* melee_spin_sheet_path = {"assets/1Knight/MeleeSpin_Shadowless.png"};
inline constexpr const char* hurt_sheet_path = {"assets/1Knight/TakeDamage_Shadowless.png"};

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
    float mouse_x = 0, mouse_y = 0;
};

struct PlayerIntent {
    int mx = 0, my = 0;
    bool fire = false;
    bool dash = false;
    bool reload = false;
    float aim_x = 0, aim_y = 0;
    bool attack = false;
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