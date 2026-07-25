#include "Collision.h"
#include "Player.h"
#include "Constants.h"
#include "Equipment.h"
#include "Engine.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>

bool aabb(const SDL_FRect& a, const SDL_FRect& b) {
    return a.x < b.x + b.w && a.x + a.w > b.x &&
           a.y < b.y + b.h && a.y + a.h > b.y;
}

void check_players_collision(Player* human, Player* bot) {
    if (human->is_dashing || bot->is_dashing) return;
    if (aabb(human->hitbox, bot->hitbox)) {
        float overlap_x = (human->hitbox.w + bot->hitbox.w) / 2.0f - std::abs(human->hitbox.x - bot->hitbox.x);
        float overlap_y = (human->hitbox.h + bot->hitbox.h) / 2.0f - std::abs(human->hitbox.y - bot->hitbox.y);

        float push_x = overlap_x / 2;
        float push_y = overlap_y / 2;

        if (overlap_x < overlap_y) {
            if (human->hitbox.x < bot->hitbox.x) {
                human->box.x -= push_x;
                bot->box.x += push_x;
            } else {
                human->box.x += push_x;
                bot->box.x -= push_x;
            }
        } else {
            if (human->hitbox.y < bot->hitbox.y) {
                human->box.y -= push_y;
                bot->box.y += push_y;
            } else {
                human->box.y += push_y;
                bot->box.y -= push_y;
            }
        }
        human->box.x = std::clamp(human->box.x, 0.0f, float(screenw - playerw));
        human->box.y = std::clamp(human->box.y, 0.0f, float(screenh - playerh));
        bot->box.x = std::clamp(bot->box.x, 0.0f, float(screenw - playerw));
        bot->box.y = std::clamp(bot->box.y, 0.0f, float(screenh - playerh));

        human->hitbox.x = human->box.x + playerw / 2 - hitbox_size;
        human->hitbox.y = human->box.y + playerh / 2 - hitbox_size;
        bot->hitbox.x = bot->box.x + playerw / 2 - hitbox_size;
        bot->hitbox.y = bot->box.y + playerh / 2 - hitbox_size;
    }
}

static bool point_in_sector(float px, float py, float cx, float cy, float angle, float half_arc, float outer_r) {
    float dx = px - cx;
    float dy = py - cy;
    float dist = std::sqrt(dx*dx + dy*dy);
    if (dist < 0 || dist > outer_r) return false;
    float a = std::atan2(dy, dx);
    float diff = a - angle;
    while (diff > static_cast<float>(M_PI)) diff -= 2.0f * static_cast<float>(M_PI);
    while (diff < -static_cast<float>(M_PI)) diff += 2.0f * static_cast<float>(M_PI);
    return std::abs(diff) <= half_arc;
}

void check_melee_collision(Player* p1, Player* p2, Engine* engine) {
    auto process_aoe = [&engine](Player* attacker, Player* target) {
        if (attacker->trigger_aoe_tremor) {
            attacker->trigger_aoe_tremor = false;
            float cx = attacker->box.x + playerw / 2.0f;
            float cy = attacker->box.y + playerh / 2.0f;
            float e_cx = target->box.x + playerw / 2.0f;
            float e_cy = target->box.y + playerh / 2.0f;
            float dist = std::sqrt((cx - e_cx)*(cx - e_cx) + (cy - e_cy)*(cy - e_cy));
            if (dist <= 150.0f && !target->is_dashing) {
                float wpn_bonus = calc_weapon_damage_bonus(get_weapon_profile(attacker->equipment.weapon), attacker->stats);
                float dmg = 25.0f * wpn_bonus;
                target->health -= dmg;
                target->hurt_timer = hurt_flash_duration;
                target->damage_taken = dmg;
                target->damage_taken_step += dmg;
                attacker->damage_dealt_step += dmg;
                target->damage_flash = 1.5f;
                target->stun_timer = 0.5f;
                if (engine) engine->push_vfx(cx, cy, 30, ParticleType::Blood, {136, 8, 8, 255});
            }
        }
    };
    process_aoe(p1, p2);
    process_aoe(p2, p1);

    if (p1->is_attacking && !p1->hit_this_swing && !p1->is_dashing && !p2->is_dashing) {
        float cx = p1->box.x + playerw / 2.0f;
        float cy = p1->box.y + playerh / 2.0f;
        SDL_FRect& hb = p2->hitbox;
        bool hit = point_in_sector(hb.x, hb.y, cx, cy, p1->melee_angle, melee_half_arc, melee_outer_r) ||
                   point_in_sector(hb.x + hb.w, hb.y, cx, cy, p1->melee_angle, melee_half_arc, melee_outer_r) ||
                   point_in_sector(hb.x, hb.y + hb.h, cx, cy, p1->melee_angle, melee_half_arc, melee_outer_r) ||
                   point_in_sector(hb.x + hb.w, hb.y + hb.h, cx, cy, p1->melee_angle, melee_half_arc, melee_outer_r);
        if (hit) {
            float mult = melee_combo_multipliers[p1->combo_stage];
            const WeaponProfile& wp = get_weapon_profile(p1->equipment.weapon);
            float wpn_bonus = calc_weapon_damage_bonus(wp, p1->stats);
            float upgrade_mult = 1.0f + p1->weapon_upgrade_levels[static_cast<int>(p1->equipment.weapon)] * upgrade_weapon_damage_per_level;
            float negation = calc_upgraded_armor_reduction(p2->equipment, p2->armor_upgrade_levels) + calc_damage_negation(p2->stats);
            negation = std::min(0.8f, std::max(-0.5f, negation));
            float dmg = wp.base_damage * mult * wpn_bonus * upgrade_mult * (1.0f - negation);
            p2->health -= dmg;
            p2->hurt_timer = hurt_flash_duration;
            p2->damage_taken = dmg;
            p2->damage_taken_step += dmg;
            p1->damage_dealt_step += dmg;
            p2->damage_flash = 1.5f;
            p1->hit_this_swing = true;
            if (wp.type == WeaponType::Daggers) {
                p2->bleed_timer = 3.0f;
                p2->bleed_dps = dmg * 0.4f;
                if (engine) engine->push_vfx(p2->box.x + playerw/2, p2->box.y + playerh/2, 10, ParticleType::Spark, {255, 200, 100, 255});
            } else {
                if (engine) engine->push_vfx(p2->box.x + playerw/2, p2->box.y + playerh/2, 10, ParticleType::Blood, {136, 8, 8, 255});
            }
            if (wp.type == WeaponType::Axe || wp.type == WeaponType::GreatSword)
                p1->trigger_aoe_tremor = true;
        }
    }
    if (p2->is_attacking && !p2->hit_this_swing && !p2->is_dashing && !p1->is_dashing) {
        float cx = p2->box.x + playerw / 2.0f;
        float cy = p2->box.y + playerh / 2.0f;
        SDL_FRect& hb = p1->hitbox;
        bool hit = point_in_sector(hb.x, hb.y, cx, cy, p2->melee_angle, melee_half_arc, melee_outer_r) ||
                   point_in_sector(hb.x + hb.w, hb.y, cx, cy, p2->melee_angle, melee_half_arc, melee_outer_r) ||
                   point_in_sector(hb.x, hb.y + hb.h, cx, cy, p2->melee_angle, melee_half_arc, melee_outer_r) ||
                   point_in_sector(hb.x + hb.w, hb.y + hb.h, cx, cy, p2->melee_angle, melee_half_arc, melee_outer_r);
        if (hit) {
            float mult = melee_combo_multipliers[p2->combo_stage];
            const WeaponProfile& wp = get_weapon_profile(p2->equipment.weapon);
            float wpn_bonus = calc_weapon_damage_bonus(wp, p2->stats);
            float upgrade_mult = 1.0f + p2->weapon_upgrade_levels[static_cast<int>(p2->equipment.weapon)] * upgrade_weapon_damage_per_level;
            float negation = calc_upgraded_armor_reduction(p1->equipment, p1->armor_upgrade_levels) + calc_damage_negation(p1->stats);
            negation = std::min(0.8f, std::max(-0.5f, negation));
            float dmg = wp.base_damage * mult * wpn_bonus * upgrade_mult * (1.0f - negation);
            p1->health -= dmg;
            p1->hurt_timer = hurt_flash_duration;
            p1->damage_taken = dmg;
            p1->damage_taken_step += dmg;
            p2->damage_dealt_step += dmg;
            p1->damage_flash = 1.5f;
            p2->hit_this_swing = true;
            if (wp.type == WeaponType::Daggers) {
                p1->bleed_timer = 3.0f;
                p1->bleed_dps = dmg * 0.4f;
                if (engine) engine->push_vfx(p1->box.x + playerw/2, p1->box.y + playerh/2, 10, ParticleType::Spark, {255, 200, 100, 255});
            } else {
                if (engine) engine->push_vfx(p1->box.x + playerw/2, p1->box.y + playerh/2, 10, ParticleType::Blood, {136, 8, 8, 255});
            }
            if (wp.type == WeaponType::Axe || wp.type == WeaponType::GreatSword)
                p2->trigger_aoe_tremor = true;
        }
    }
}

static void apply_spell_damage(Player* caster, Player* target, const SpellProfile& sp, Engine* engine) {
    float rea_bonus = 1.0f + (caster->stats.reasoning - default_stat_value) * 0.01f;
    float negation = calc_upgraded_armor_reduction(target->equipment, target->armor_upgrade_levels) + calc_damage_negation(target->stats);
    negation = std::min(0.8f, std::max(-0.5f, negation));
    float dmg = sp.base_damage * rea_bonus * (1.0f - negation);
    target->health -= dmg;
    target->hurt_timer = hurt_flash_duration;
    target->damage_taken = dmg;
    target->damage_taken_step += dmg;
    caster->damage_dealt_step += dmg;
    target->damage_flash = 1.5f;

    if (sp.effect == SpellEffect::Slow)
        target->slow_timer = std::max(target->slow_timer, sp.effect_duration);
    else if (sp.effect == SpellEffect::Stun)
        target->stun_timer = std::max(target->stun_timer, sp.effect_duration);

    if (engine) engine->push_vfx(target->box.x + playerw/2, target->box.y + playerh/2, 15, ParticleType::Magic, {100, 100, 255, 255});
}

void check_spell_collision(Player* caster, Player* target, Engine* engine) {
    for (auto& p : caster->projectiles) {
        if (!p.active) continue;
        if (caster->is_dashing) continue;
        if (target->is_dashing) continue;

        const SpellProfile& sp = get_spell_profile(p.type);

        if (sp.speed <= 0.0f) {
            SDL_FRect strike = p.hitbox;
            float pad = 40.0f;
            strike.x -= pad; strike.y -= pad;
            strike.w += 2 * pad; strike.h += 2 * pad;
            if (aabb(strike, target->hitbox))
                apply_spell_damage(caster, target, sp, engine);
            p.active = false;
            continue;
        }

        if (aabb(p.hitbox, target->hitbox)) {
            apply_spell_damage(caster, target, sp, engine);

            if (sp.piercing) {
                p.hitbox.x += p.vx * 5.0f;
                p.hitbox.y += p.vy * 5.0f;
            } else {
                p.active = false;
            }
        }
    }
}
