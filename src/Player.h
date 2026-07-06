#pragma once
#include <string>
#include <array>
#include <utility>
#include <SDL3/SDL.h>
#include "Structures.h"
#include "Bullet.h"
#include "Constants.h"

class Player {
    public:
    Player(float x, float y, float speed, std::string name);
    ~Player();

    void move(float dt, PlayerIntent intent);
    void draw(SDL_Renderer* renderer);
    void load_textures(SDL_Texture* idle, SDL_Texture* walk, SDL_Texture* run, SDL_Texture* shoot, SDL_Texture* bullet, SDL_Texture* melee1, SDL_Texture* melee2, SDL_Texture* melee_spin, SDL_Texture* hurt);
    void reset(float x, float y);

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

    private:
    void advanceFrame(float dt);
    SDL_FRect get_texture_box();

    std::string name;
    std::pair<int,int> direction = {1, 0};
    SDL_Texture* texture {};
    SDL_Texture* idle_texture {};
    SDL_Texture* walk_texture {};
    SDL_Texture* run_texture {};
    SDL_Texture* shoot_texture {};
    SDL_Texture* melee1_texture {};
    SDL_Texture* melee2_texture {};
    SDL_Texture* melee_spin_texture {};
    SDL_Texture* hurt_texture {};
    Spritesheet spritesheet;

    bool is_firing {};
    float anim_timer {};
    float fire_anim_timer {};
    float attack_anim_timer {};
    float fire_cooldown_timer = 0.0f;
    int texture_state {};
};