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
    {WeaponType::Sword,     12, 15, 0.15f, 1.0f,  StatType::Agility,    SCALE_A, StatType::Strength,   SCALE_E, 4},
    {WeaponType::Daggers,    8,  8, 0.1f,  0.6f,  StatType::Agility,    SCALE_S, StatType::Strength,   SCALE_E, 2},
    {WeaponType::GreatSword,22, 20, 0.3f,  1.0f,  StatType::Strength,   SCALE_S, StatType::Endurance,  SCALE_D, 10},
    {WeaponType::Staff,     10, 20, 0.2f,  0.8f,  StatType::Reasoning,  SCALE_S, StatType::Agility,    SCALE_D, 3},
    {WeaponType::Axe,       18, 16, 0.25f, 0.9f,  StatType::Strength,   SCALE_S, StatType::Endurance,  SCALE_C, 7},
};

static const ArmorPiece armor_table[5] = {
    {ArmorTier::Cloth,         0.00f, 1.00f, 1.00f, 1.00f, 1},
    {ArmorTier::LightLeather,  0.10f, 0.97f, 0.98f, 0.98f, 3},
    {ArmorTier::MediumChain,   0.20f, 0.93f, 0.95f, 0.95f, 5},
    {ArmorTier::HeavyPlate,    0.35f, 0.88f, 0.90f, 0.90f, 8},
    {ArmorTier::UltraHeavy,    0.50f, 0.80f, 0.82f, 0.82f, 12},
};

static const WeaponShopInfo weapon_shop[weapon_count] = {
    {WeaponType::Sword,     "Sword",     0.0f,   "Balanced, AGI scaling",          "weapon_r0_c1.png"},
    {WeaponType::Daggers,   "Daggers",   80.0f,  "Fast attacks, high AGI scaling",  "dagger_short.png"},
    {WeaponType::GreatSword,"GreatSword",150.0f, "Slow heavy hits, STR scaling",    "weapon_r0_c2.png"},
    {WeaponType::Staff,     "Staff",     120.0f, "REA scaling, good for casters",   "weapon_r3_c0.png"},
    {WeaponType::Axe,       "Axe",       100.0f, "Heavy STR weapon, slow but strong","weapon_r1_c2.png"},
};

const WeaponShopInfo& get_weapon_shop_info(WeaponType type) {
    int idx = static_cast<int>(type);
    return weapon_shop[idx];
}

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

float calc_upgraded_weapon_damage(const WeaponProfile& wp, const PlayerStats& stats, int upgrade_level) {
    float base_mult = calc_weapon_damage_bonus(wp, stats);
    float upgrade_mult = 1.0f + upgrade_level * upgrade_weapon_damage_per_level;
    return wp.base_damage * base_mult * upgrade_mult;
}

float calc_upgraded_armor_reduction(const Loadout& loadout, const int upgrade_levels[3]) {
    float total = 0.0f;
    ArmorSlot slots[3] = {ArmorSlot::Head, ArmorSlot::Chest, ArmorSlot::Legs};
    for (int i = 0; i < 3; ++i) {
        ArmorTier tier;
        switch (slots[i]) {
            case ArmorSlot::Head:  tier = loadout.head; break;
            case ArmorSlot::Chest: tier = loadout.chest; break;
            case ArmorSlot::Legs:  tier = loadout.legs; break;
        }
        float base = get_armor_piece(slots[i], tier).damage_reduction;
        float bonus = upgrade_levels[i] * upgrade_armor_reduction_per_level;
        total += base + bonus;
    }
    return std::min(0.8f, total);
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
