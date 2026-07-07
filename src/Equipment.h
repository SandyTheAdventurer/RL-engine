#pragma once
#include "Stats.h"
#include <SDL3/SDL.h>

// Layer slots for compositing (rendered back-to-front)
enum LayerSlot {
    SLOT_BODY,
    SLOT_SHOES,
    SLOT_LEGS,
    SLOT_TORSO,
    SLOT_ARMOR,
    SLOT_HEAD,
    SLOT_FACE,
    SLOT_HAT,
    SLOT_WEAPON,
    SLOT_COUNT
};

enum class WeaponType {
    Katana,
    ShortSword,
    Daggers,
    GreatSword,
    Shield,
    Staff
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
    WeaponType weapon = WeaponType::ShortSword;
    ArmorTier head = ArmorTier::LightLeather;
    ArmorTier chest = ArmorTier::LightLeather;
    ArmorTier legs = ArmorTier::LightLeather;
};

const WeaponProfile& get_weapon_profile(WeaponType type);
const ArmorPiece& get_armor_piece(ArmorSlot slot, ArmorTier tier);
float calc_weapon_damage_bonus(const WeaponProfile& wp, const PlayerStats& stats);
float calc_max_equip_load(const PlayerStats& stats);
float calc_total_equip_load(const Loadout& loadout);
float calc_equip_load_ratio(const Loadout& loadout, const PlayerStats& stats);
float calc_armor_damage_reduction(const Loadout& loadout);
float calc_armor_speed_mod(const Loadout& loadout);
float calc_armor_dash_speed_mod(const Loadout& loadout);
float calc_armor_dash_dist_mod(const Loadout& loadout);
