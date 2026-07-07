#pragma once

enum class StatType {
    Strength,
    Vitality,
    Agility,
    Reasoning,
    Endurance
};

struct PlayerStats {
    float strength = 20.0f;
    float vitality = 20.0f;
    float agility = 20.0f;
    float reasoning = 20.0f;
    float endurance = 20.0f;
};

float get_stat(const PlayerStats& stats, StatType type);
float calc_melee_damage_bonus(const PlayerStats& stats);
float calc_bullet_damage_bonus(const PlayerStats& stats);
float calc_move_speed_mod(const PlayerStats& stats);
float calc_max_hp(const PlayerStats& stats);
float calc_dash_speed_mod(const PlayerStats& stats);
float calc_dash_distance_mod(const PlayerStats& stats);
float calc_attack_speed_mod(const PlayerStats& stats);
float calc_damage_negation(const PlayerStats& stats);
float calc_max_stamina(const PlayerStats& stats);
float calc_stamina_regen(const PlayerStats& stats);
float calc_dash_stamina_cost(const PlayerStats& stats);
float calc_melee_stamina_cost(const PlayerStats& stats);
float calc_bullet_speed_mod(const PlayerStats& stats);
