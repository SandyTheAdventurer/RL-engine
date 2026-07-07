#pragma once
#include <array>
#include <map>

inline constexpr int screenw {1280};
inline constexpr int screenh {720};
inline constexpr int playerw {75};
inline constexpr int playerh {75};
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
inline constexpr float max_dist {1468.6f};

inline constexpr float melee_damage = 12.0f;
inline constexpr float melee_range = 10.0f;
inline constexpr float melee_cooldown = 0.2f;
inline constexpr float combo_window = 0.3f;
inline constexpr int max_combo_stage = 2;
inline constexpr float melee_half_arc = 0.7854f;
inline constexpr float melee_outer_r = playerw / 2.0f + melee_range;

inline constexpr float dash_distance = 100.0f;
inline constexpr float dash_blink_duration = 0.2f;
inline constexpr float dash_cooldown = 0.3f;
inline constexpr float dash_speed = dash_distance / dash_blink_duration;

inline constexpr int sprite_frame_count = 24;
inline constexpr int sprite_direction_count = 8;

enum class AnimationState {
    Idle,
    Walk,
    Run,
    CastShoot,
    Melee1,
    Melee2,
    MeleeSpin,
    Hurt,
    Count
};

inline constexpr std::array<const char*, static_cast<int>(AnimationState::Count)> animation_suffixes = {
    "idle",
    "walk",
    "run",
    "cast_shoot",
    "melee_1",
    "melee_2",
    "melee_spin",
    "hurt"
};

inline constexpr std::array<const char*, 6> weapon_sheet_names = {
    "katana",
    "short_sword",
    "daggers",
    "great_sword",
    "shield",
    "staff"
};

inline constexpr std::array<const char*, 5> armor_tier_names = {
    "Cloth",
    "LightLeather",
    "MediumChain",
    "HeavyPlate",
    "UltraHeavy"
};

inline constexpr std::array<const char*, 3> armor_slot_names = {
    "head",
    "chest",
    "legs"
};

inline constexpr const char* generated_base_dir = {"assets/Base_Character"};
inline constexpr const char* generated_weapon_dir = {"assets/Weapons"};
inline constexpr const char* generated_armor_dir = {"assets/Armor"};
inline constexpr const char* generated_projectile_path = {"assets/Projectiles/bullet_projectile.png"};

inline constexpr float melee_combo_multipliers[3] = {1.0f, 1.3f, 1.8f};
inline constexpr float base_max_stamina = 100.0f;
inline constexpr float base_stamina_regen = 40.0f;
inline constexpr float stamina_regen_delay = 0.5f;
inline constexpr float dash_stamina_cost = 30.0f;
inline constexpr float melee_stamina_cost = 20.0f;
inline constexpr float default_stat_value = 20.0f;
inline constexpr float max_stat_value = 99.0f;
inline constexpr int obs_dim = 83;

struct PlayerStats;

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