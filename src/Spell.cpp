#include "Spell.h"
#include "Constants.h"
#include <cmath>
#include <cstdio>

static const SpellProfile spell_table[] = {
    {SpellType::Fireball,       15, 15, 0.4f,  1, 500, true,  30, false, SpellEffect::None, 0,    "Fireball"},
    {SpellType::IceShard,       10, 10, 0.3f,  1, 600, false, 0,  true,  SpellEffect::Slow, 2.0f, "IceShard"},
    {SpellType::LightningBolt,  20, 25, 1.0f,  1, 0,   false, 0,  false, SpellEffect::Stun, 0.5f, "Lightning"},
    {SpellType::ArcaneBarrage,  25,  8, 0.6f,  3, 550, false, 0,  false, SpellEffect::None, 0,    "Barrage"},
};

const SpellProfile& get_spell_profile(SpellType type) {
    return spell_table[static_cast<int>(type)];
}

SpellType get_spell_for_reasoning(float reasoning) {
    if (reasoning >= 75.0f) return SpellType::ArcaneBarrage;
    if (reasoning >= 50.0f) return SpellType::LightningBolt;
    if (reasoning >= 25.0f) return SpellType::IceShard;
    return SpellType::Fireball;
}

void fire_spell_projectile(SpellProjectile& p, float x, float y, float tx, float ty, SpellType type, float speed) {
    const float p_size = 20.0f;
    p.hitbox = {x - p_size / 2.0f, y - p_size / 2.0f, p_size, p_size};
    p.type = type;
    p.speed = speed;

    if (speed <= 0.0f) {
        p.vx = 0.0f;
        p.vy = 0.0f;
        p.angle = 0.0f;
        p.active = true;
        return;
    }

    float dx = tx - x;
    float dy = ty - y;
    float dist = std::sqrt(dx * dx + dy * dy);
    if (dist < 1.0f) dist = 1.0f;
    p.vx = dx / dist * speed;
    p.vy = dy / dist * speed;
    p.angle = std::atan2(dy, dx) * 180.0f / static_cast<float>(M_PI);
    p.active = true;
}

void move_projectile(SpellProjectile& p, float dt) {
    if (!p.active) return;
    p.hitbox.x += p.vx * dt;
    p.hitbox.y += p.vy * dt;
    float ps = 20.0f;
    if (p.hitbox.x < -ps || p.hitbox.x > screenw + ps ||
        p.hitbox.y < -ps || p.hitbox.y > screenh + ps) {
        p.active = false;
    }
}
