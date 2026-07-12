#pragma once
#include <string>
#include <array>
#include <utility>
#include <SDL3/SDL.h>
#include "Structures.h"
#include "Spell.h"
#include "Constants.h"
#include "Stats.h"
#include "Stamina.h"
#include "Equipment.h"

struct Weapon {
    SDL_Texture* texture = nullptr;
    float angle = 0.0f;
    bool is_swinging = false;
    float swing_timer = 0.0f;
};

struct DashTrail {
    float x = 0, y = 0;
    std::pair<int, int> direction = {0, 1};
    int texture_state = 0;
    int animation_index = 0;
    float life = 0.0f;
    float max_life = 0.0f;
};

class Player {
    public:
    Weapon weapon;
    Player(float x, float y, float speed, std::string name);
    ~Player();

    void move(float dt, PlayerIntent intent);
    void draw(SDL_Renderer* renderer);
    void reset(float x, float y);

    bool is_moving = {false};
    bool is_dashing = {false};
    bool is_iframe = {false};

    float dash_timer = 0.0f;
    float dash_cooldown_timer = 0.0f;
    float dash_dir_x = 0.0f;
    float dash_dir_y = 0.0f;

    float getSpeed() const { return speed; }
    const std::string& getName() const { return name; }
    std::pair<int,int> getDirection() const { return direction; }

    float speed;
    float vx = 0, vy = 0;
    float health = max_health;
    float mana = 0;
    float max_mana = 0;
    float mana_regen = 0;
    float spell_cooldown_timers[4] = {};
    std::array<SpellProjectile, max_projectiles> projectiles;

    SDL_FRect box;
    SDL_FRect hitbox;

    bool is_attacking = false;
    bool hit_this_swing = false;
    bool trigger_aoe_tremor = false;
    bool trigger_cast_vfx = false;
    float cast_vfx_angle = 0.0f;
    int combo_stage = 0;
    bool dead = false;
    float death_timer = 0.0f;
    float attack_cooldown_timer = 0.0f;
    float combo_timer = 0.0f;
    float hurt_timer = 0.0f;
    float slow_timer = 0.0f;
    float stun_timer = 0.0f;
    float melee_angle = 0.0f;

    PlayerStats stats;
    Stamina stamina;
    Loadout equipment;
    float max_hp;
    float equip_load_ratio;
    float damage_flash = 0.0f;
    float damage_taken = 0.0f;

    float bleed_timer = 0.0f;
    float bleed_dps = 0.0f;

    static constexpr int max_dash_trails = 10;
    DashTrail dash_trails[max_dash_trails];
    int next_dash_trail_idx = 0;
    float dash_trail_timer = 0.0f;

    float dimes = 0.0f;
    bool owned_weapons[weapon_count] = {true, false, false, false, false};
    int weapon_upgrade_levels[weapon_count] = {};
    int armor_upgrade_levels[3] = {};

    bool is_weapon_owned(WeaponType type) const;
    bool can_afford(float cost) const;
    bool purchase_stat_upgrade(StatType type);
    bool purchase_weapon(WeaponType type);
    bool equip_weapon(WeaponType type);
    bool purchase_weapon_upgrade(int weapon_index);
    bool purchase_armor_upgrade(ArmorSlot slot);

    void load_texture(AnimationState state, SDL_Texture* tex);
    void load_weapon_texture(SDL_Texture* tex);
    void equip_weapon_texture(SDL_Renderer* renderer, const char* tex_file);

    private:
    void advanceFrame(float dt);
    SDL_FRect get_texture_box();
    int get_animation_index() const;

    std::string name;
    std::pair<int,int> direction = {0, 1};
    SDL_Texture* textures[static_cast<int>(AnimationState::Count)] = {};
    Spritesheet* spritesheets[static_cast<int>(AnimationState::Count)] = {};

    SDL_Texture* weapon_texture = nullptr;
    bool is_firing {};
    float anim_timer {};
    float fire_anim_timer {};
    float attack_anim_timer {};
    float fire_cooldown_timer = 0.0f;
    int texture_state {};
};
