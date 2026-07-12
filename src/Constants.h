#pragma once
#include <array>
#include <map>

inline constexpr int screenw {1280};
inline constexpr int screenh {720};
inline constexpr int playerw {75};
inline constexpr int playerh {75};
inline constexpr float playerspeed {200.0f};
inline constexpr int max_health = {100};
inline constexpr float spritechange {1.0f / 8.0f};
inline constexpr float fire_spritechange {1.0f / 10.0f};
inline constexpr float attack_spritechange {1.0f / 10.0f};
inline constexpr float hurt_flash_duration = 0.12f;
inline constexpr float death_spritechange {1.0f / 6.0f};
inline constexpr float death_duration = 4.0f * death_spritechange;
inline constexpr float hitbox_size {24.0f};
inline constexpr float spell_speed {500.0f};

inline constexpr int font_size {20};
inline constexpr float bar_h {10.0f};
inline constexpr float max_dist {1468.6f};

inline constexpr float melee_damage = 12.0f;
inline constexpr float melee_range = 10.0f;
inline constexpr float melee_cooldown = 0.2f;
inline constexpr float combo_window = 0.8f;
inline constexpr int max_combo_stage = 2;
inline constexpr float melee_half_arc = 0.7854f;
inline constexpr float melee_outer_r = playerw / 2.0f + melee_range;

inline constexpr float dash_distance = 100.0f;
inline constexpr float dash_blink_duration = 0.2f;
inline constexpr float dash_cooldown = 0.3f;
inline constexpr float dash_speed = dash_distance / dash_blink_duration;

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
    Dash,
    Death,
    Count
};

inline constexpr std::array<const char*, static_cast<int>(AnimationState::Count)> animation_suffixes = {
    "idle",
    "walk",
    "run",
    "cast",
    "slash",
    "slash2",
    "slash3",
    "hurt",
    "dash",
    "death"
};

inline constexpr std::array<int, static_cast<int>(AnimationState::Count)> sprite_frame_counts = {
    4,  // Idle
    4,  // Walk
    4,  // Run
    4,  // CastShoot
    4,  // Melee1 (slash)
    4,  // Melee2 (slash2)
    4,  // MeleeSpin (slash3)
    4,  // Hurt
    4,  // Dash
    4,  // Death
};

inline constexpr int weapon_count = 5;

inline constexpr std::array<const char*, weapon_count> weapon_sheet_names = {
    "Sword",
    "Dagger",
    "GoldSword",
    "Staff",
    "Axe"
};

inline constexpr std::array<const char*, 5> armor_tier_names = {
    "Cloth",
    "Leather",
    "Chain",
    "Plate",
    "Heavy"
};

inline constexpr std::array<const char*, 3> armor_slot_names = {
    "head",
    "chest",
    "legs"
};

inline constexpr const char* asset_dir = {"assets"};

inline constexpr float melee_combo_multipliers[3] = {1.0f, 1.3f, 1.8f};
inline constexpr float base_max_stamina = 150.0f;
inline constexpr float base_stamina_regen = 40.0f;
inline constexpr float stamina_regen_delay = 0.5f;
inline constexpr float dash_stamina_cost = 30.0f;
inline constexpr float melee_stamina_cost = 20.0f;
inline constexpr float default_stat_value = 10.0f;
inline constexpr float max_stat_value = 99.0f;
inline constexpr float fire_stamina_cost = 10.0f;
inline constexpr int obs_dim = 88;
inline constexpr int qm_obs_dim = 64;

inline constexpr float qm_dimes_normalizer = 500.0f;
inline constexpr float qm_cost_normalizer = 500.0f;
inline constexpr float qm_teff_normalizer = 300.0f;
inline constexpr float qm_hp_normalizer = 200.0f;

inline constexpr float player_projectile_speed = 500.0f;
inline constexpr int max_projectiles = 12;

enum class MenuResult {
    NONE,
    PLAY,
    QUIT,
    RESTART
};

struct PlayerStats;

inline constexpr float economy_distance_threshold = 200.0f;
inline constexpr float economy_damage_window = 3.0f;
inline constexpr float economy_perfect_dodge_window = 2.0f;

inline constexpr float economy_base_payout = 100.0f;
inline constexpr float economy_par_time = 90.0f;
inline constexpr float economy_lambda = 0.01f;
inline constexpr float economy_min_multiplier = 0.2f;

inline constexpr float economy_pity_alpha = 0.5f;
inline constexpr float economy_pity_beta = 5.0f;
inline constexpr float economy_pity_gamma = 10.0f;

inline constexpr float economy_drop_fraction = 0.5f;
inline constexpr float economy_decay_start_time = 10.0f;
inline constexpr float economy_collect_radius = 50.0f;

inline constexpr int max_stat_upgrade_cost = 300;
inline constexpr float upgrade_base_stat_cost = 20.0f;
inline constexpr float upgrade_stat_growth = 1.0f; // cost = base * (level - 19)
inline constexpr float upgrade_base_weapon_cost = 50.0f;
inline constexpr float upgrade_weapon_growth = 1.3f;
inline constexpr float upgrade_base_armor_cost = 40.0f;
inline constexpr float upgrade_armor_growth = 1.25f;
inline constexpr float upgrade_weapon_damage_per_level = 0.1f;
inline constexpr float upgrade_armor_reduction_per_level = 0.02f;
inline constexpr int max_upgrade_level = 10;

inline constexpr float weapon_shop_prices[weapon_count] = {
    0.0f,   // Sword - free starter
    80.0f,  // Daggers
    150.0f, // GreatSword
    120.0f, // Staff
    100.0f  // Axe
};

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
    int pressed_key = -1;
};

struct LevelUpIntent {
    int stat_up = -1;
    int buy_weapon = -1;
    int equip_weapon = -1;
    int weapon_upgrade_index = -1;
    int armor_upgrade = -1;
};

struct PlayerIntent {
    int mx = 0, my = 0;
    bool fire = false;
    bool dash = false;
    int selected_spell = 0;
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
