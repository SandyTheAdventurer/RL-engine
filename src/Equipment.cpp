#include "Equipment.h"
#include "Constants.h"
#include <algorithm>

constexpr float SCALE_S = 3.0f;
constexpr float SCALE_A = 2.5f;
constexpr float SCALE_B = 2.0f;
constexpr float SCALE_C = 1.5f;
constexpr float SCALE_D = 1.0f;
constexpr float SCALE_E = 0.5f;

static const WeaponProfile weapon_table[] = {
    {WeaponType::Katana,     12, 15, 0.15f, 1.0f,  StatType::Agility,    SCALE_A, StatType::Strength,   SCALE_E, 4},
    {WeaponType::ShortSword, 14, 10, 0.2f,  0.8f,  StatType::Strength,   SCALE_B, StatType::Agility,    SCALE_D, 5},
    {WeaponType::Daggers,     8,  8, 0.1f,  0.6f,  StatType::Agility,    SCALE_S, StatType::Strength,   SCALE_E, 2},
    {WeaponType::GreatSword, 22, 20, 0.3f,  1.0f,  StatType::Strength,   SCALE_S, StatType::Endurance,  SCALE_D, 10},
    {WeaponType::Shield,      6,  8, 0.3f,  0.5f,  StatType::Endurance,  SCALE_B, StatType::Strength,   SCALE_D, 6},
    {WeaponType::Staff,      10, 20, 0.2f,  0.8f,  StatType::Reasoning,  SCALE_S, StatType::Agility,    SCALE_D, 3},
};

static const ArmorPiece armor_table[5] = {
    {ArmorTier::Cloth,         0.00f, 1.00f, 1.00f, 1.00f, 1},
    {ArmorTier::LightLeather,  0.10f, 0.97f, 0.98f, 0.98f, 3},
    {ArmorTier::MediumChain,   0.20f, 0.93f, 0.95f, 0.95f, 5},
    {ArmorTier::HeavyPlate,    0.35f, 0.88f, 0.90f, 0.90f, 8},
    {ArmorTier::UltraHeavy,    0.50f, 0.80f, 0.82f, 0.82f, 12},
};

const WeaponProfile& get_weapon_profile(WeaponType type) {
    int idx = static_cast<int>(type);
    return weapon_table[idx];
}

const ArmorPiece& get_armor_piece(ArmorSlot slot, ArmorTier tier) {
    int idx = static_cast<int>(tier);
    (void)slot;
    return armor_table[idx];
}

float calc_weapon_damage_bonus(const WeaponProfile& wp, const PlayerStats& stats) {
    float p_stat = get_stat(stats, wp.primary_affinity);
    float s_stat = get_stat(stats, wp.secondary_affinity);
    float p_bonus = 1.0f + wp.primary_scale * (p_stat - default_stat_value) / 100.0f;
    float s_bonus = 1.0f + wp.secondary_scale * (s_stat - default_stat_value) / 100.0f;
    return p_bonus * s_bonus;
}

float calc_max_equip_load(const PlayerStats& stats) {
    return 50.0f + stats.strength * 2.0f + stats.endurance * 3.0f;
}

float calc_total_equip_load(const Loadout& loadout) {
    const WeaponProfile& wp = get_weapon_profile(loadout.weapon);
    float total = wp.weight;
    total += get_armor_piece(ArmorSlot::Head, loadout.head).weight;
    total += get_armor_piece(ArmorSlot::Chest, loadout.chest).weight;
    total += get_armor_piece(ArmorSlot::Legs, loadout.legs).weight;
    return total;
}

float calc_equip_load_ratio(const Loadout& loadout, const PlayerStats& stats) {
    float max_load = calc_max_equip_load(stats);
    if (max_load <= 0.0f) return 0.0f;
    return calc_total_equip_load(loadout) / max_load;
}

float calc_armor_damage_reduction(const Loadout& loadout) {
    float total = 0.0f;
    total += get_armor_piece(ArmorSlot::Head, loadout.head).damage_reduction;
    total += get_armor_piece(ArmorSlot::Chest, loadout.chest).damage_reduction;
    total += get_armor_piece(ArmorSlot::Legs, loadout.legs).damage_reduction;
    return std::min(0.8f, total);
}

float calc_armor_speed_mod(const Loadout& loadout) {
    float mod = 1.0f;
    mod *= get_armor_piece(ArmorSlot::Head, loadout.head).speed_mod;
    mod *= get_armor_piece(ArmorSlot::Chest, loadout.chest).speed_mod;
    mod *= get_armor_piece(ArmorSlot::Legs, loadout.legs).speed_mod;
    return mod;
}

float calc_armor_dash_speed_mod(const Loadout& loadout) {
    float mod = 1.0f;
    mod *= get_armor_piece(ArmorSlot::Head, loadout.head).dash_speed_mod;
    mod *= get_armor_piece(ArmorSlot::Chest, loadout.chest).dash_speed_mod;
    mod *= get_armor_piece(ArmorSlot::Legs, loadout.legs).dash_speed_mod;
    return mod;
}

float calc_armor_dash_dist_mod(const Loadout& loadout) {
    float mod = 1.0f;
    mod *= get_armor_piece(ArmorSlot::Head, loadout.head).dash_dist_mod;
    mod *= get_armor_piece(ArmorSlot::Chest, loadout.chest).dash_dist_mod;
    mod *= get_armor_piece(ArmorSlot::Legs, loadout.legs).dash_dist_mod;
    return mod;
}
