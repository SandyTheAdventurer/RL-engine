#pragma once
#include <string>
#include <array>
#include <utility>
#include <SDL3/SDL.h>
#include "Structures.h"
#include "Bullet.h"
#include "Constants.h"
#include "Stats.h"
#include "Stamina.h"
#include "Equipment.h"

struct Weapon {
    SDL_Texture* texture = nullptr;
    float angle = 0.0f;
    bool is_swinging = false;
    int combo_step = 1;
    float swing_timer = 0.0f;
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
    int ammo = max_ammo;
    bool is_reloading = false;
    float reload_timer = 0.0f;
    SDL_FRect box;
    SDL_FRect hitbox;
    std::array<Bullet, max_bullets / 2> bullets;

    bool is_attacking = false;
    bool hit_this_swing = false;
    int combo_stage = 0;
    SDL_FRect melee_hitbox{0,0,0,0};
    float attack_cooldown_timer = 0.0f;
    float combo_timer = 0.0f;
    float hurt_timer = 0.0f;
    float melee_angle = 0.0f;

    PlayerStats stats;
    Stamina stamina;
    Loadout equipment;
    float max_hp;
    float equip_load_ratio;

    void load_texture(AnimationState state, SDL_Texture* tex);
    void load_weapon_texture(SDL_Texture* tex);

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