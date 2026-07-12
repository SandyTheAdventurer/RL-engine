#pragma once
#include <SDL3/SDL.h>
#include <array>

enum class SpellType {
    Fireball,
    IceShard,
    LightningBolt,
    ArcaneBarrage
};

enum class SpellEffect {
    None,
    Slow,
    Stun
};

struct SpellProfile {
    SpellType type;
    float mana_cost;
    float base_damage;
    float cooldown;
    int projectiles;
    float speed;
    bool has_splash;
    float splash_radius;
    bool piercing;
    SpellEffect effect;
    float effect_duration;
    const char* name;
};

struct SpellProjectile {
    SDL_FRect hitbox;
    float vx, vy;
    float angle;
    float speed;
    SpellType type;
    bool active = false;
};

const SpellProfile& get_spell_profile(SpellType type);
SpellType get_spell_for_reasoning(float reasoning);
void fire_spell_projectile(SpellProjectile& p, float x, float y, float tx, float ty, SpellType type, float speed);
void move_projectile(SpellProjectile& p, float dt);
