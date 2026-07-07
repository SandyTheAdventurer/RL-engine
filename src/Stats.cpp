#include "Stats.h"
#include "Constants.h"
#include <algorithm>

float get_stat(const PlayerStats& stats, StatType type) {
    switch (type) {
        case StatType::Strength:   return stats.strength;
        case StatType::Vitality:   return stats.vitality;
        case StatType::Agility:    return stats.agility;
        case StatType::Reasoning:  return stats.reasoning;
        case StatType::Endurance:  return stats.endurance;
    }
    return 0.0f;
}

float calc_melee_damage_bonus(const PlayerStats& stats) {
    return 1.0f + (stats.strength - default_stat_value) * 0.01f;
}

float calc_bullet_damage_bonus(const PlayerStats& stats) {
    return 1.0f + (stats.reasoning - default_stat_value) * 0.01f;
}

float calc_move_speed_mod(const PlayerStats& stats) {
    float agility_bonus = (stats.agility - default_stat_value) * 0.003f;
    float vitality_penalty = (stats.vitality - default_stat_value) * -0.002f;
    return std::max(0.5f, 1.0f + agility_bonus + vitality_penalty);
}

float calc_max_hp(const PlayerStats& stats) {
    float vit_bonus = (stats.vitality - default_stat_value) * 3.0f;
    float rea_penalty = (stats.reasoning - default_stat_value) * -1.0f;
    return std::max(50.0f, static_cast<float>(max_health) + vit_bonus + rea_penalty);
}

float calc_dash_speed_mod(const PlayerStats& stats) {
    return 1.0f + (stats.agility - default_stat_value) * 0.005f;
}

float calc_dash_distance_mod(const PlayerStats& stats) {
    float agility_bonus = (stats.agility - default_stat_value) * 0.003f;
    float endurance_penalty = (stats.endurance - default_stat_value) * -0.002f;
    return std::max(0.5f, 1.0f + agility_bonus + endurance_penalty);
}

float calc_attack_speed_mod(const PlayerStats& stats) {
    return 1.0f + (stats.strength - default_stat_value) * 0.005f;
}

float calc_damage_negation(const PlayerStats& stats) {
    float endurance_bonus = (stats.endurance - default_stat_value) * 0.005f;
    float agility_penalty = (stats.agility - default_stat_value) * -0.003f;
    return std::max(-0.5f, std::min(0.8f, endurance_bonus + agility_penalty));
}

float calc_max_stamina(const PlayerStats& stats) {
    return base_max_stamina + (stats.endurance - default_stat_value) * 10.0f;
}

float calc_stamina_regen(const PlayerStats& stats) {
    return base_stamina_regen * (1.0f + (stats.endurance - default_stat_value) * 0.01f);
}

float calc_dash_stamina_cost(const PlayerStats& stats) {
    return std::max(10.0f, dash_stamina_cost - (stats.agility - default_stat_value) * 0.2f);
}

float calc_melee_stamina_cost(const PlayerStats& stats) {
    return melee_stamina_cost + (stats.strength - default_stat_value) * 0.2f;
}

float calc_bullet_speed_mod(const PlayerStats& stats) {
    return 1.0f + (stats.agility - default_stat_value) * 0.002f;
}
