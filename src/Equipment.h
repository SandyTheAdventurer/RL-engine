#pragma once
#include "Stats.h"
#include "Constants.h"
#include <SDL3/SDL.h>

enum class WeaponType {
    Sword,
    Daggers,
    GreatSword,
    Staff,
    Axe
};

enum class ArmorSlot {
    Head,
    Chest,
    Legs
};

enum class ArmorTier {
    Cloth,
    LightLeather,
    MediumChain,
    HeavyPlate,
    UltraHeavy
};

struct WeaponProfile {
    WeaponType type;
    float base_damage;
    float range;
    float cooldown;
    float half_arc;
    StatType primary_affinity;
    float primary_scale;
    StatType secondary_affinity;
    float secondary_scale;
    float weight;
};

struct ArmorPiece {
    ArmorTier tier;
    float damage_reduction;
    float speed_mod;
    float dash_speed_mod;
    float dash_dist_mod;
    float weight;
};

struct Loadout {
    WeaponType weapon = WeaponType::Sword;
    ArmorTier head = ArmorTier::LightLeather;
    ArmorTier chest = ArmorTier::LightLeather;
    ArmorTier legs = ArmorTier::LightLeather;
};

struct WeaponShopInfo {
    WeaponType type;
    const char* name;
    float cost;
    const char* desc;
    const char* tex_file;
};

const WeaponShopInfo& get_weapon_shop_info(WeaponType type);
const WeaponProfile& get_weapon_profile(WeaponType type);
const ArmorPiece& get_armor_piece(ArmorSlot slot, ArmorTier tier);
float calc_weapon_damage_bonus(const WeaponProfile& wp, const PlayerStats& stats);
float calc_upgraded_weapon_damage(const WeaponProfile& wp, const PlayerStats& stats, int upgrade_level);
float calc_upgraded_armor_reduction(const Loadout& loadout, const int upgrade_levels[3]);
float calc_max_equip_load(const PlayerStats& stats);
float calc_total_equip_load(const Loadout& loadout);
float calc_equip_load_ratio(const Loadout& loadout, const PlayerStats& stats);
float calc_armor_speed_mod(const Loadout& loadout);
float calc_armor_dash_speed_mod(const Loadout& loadout);
float calc_armor_dash_dist_mod(const Loadout& loadout);
