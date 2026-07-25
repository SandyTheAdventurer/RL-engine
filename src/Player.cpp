#include "Player.h"
#include "Economy.h"
#include "Constants.h"
#include <SDL3_image/SDL_image.h>
#include <vector>
#include <cmath>
#include <cstdio>
#include <algorithm>

static constexpr int animation_count = static_cast<int>(AnimationState::Count);

Player::Player(float x, float y, float speed, std::string name)
    : speed(speed),
    name(name)
{
    box = {x, y, playerw, playerh};
    hitbox = {x + playerw / 2 - hitbox_size,  y + playerh / 2 - hitbox_size,
              hitbox_size * 2, hitbox_size * 2};
    stamina.init(stats);
    max_hp = calc_max_hp(stats);
    health = max_hp;
    max_mana = calc_max_mana(stats);
    mana = max_mana;
    mana_regen = calc_mana_regen(stats);
    equip_load_ratio = calc_equip_load_ratio(equipment, stats);

    for (int i = 0; i < animation_count; ++i) {
        spritesheets[i] = new Spritesheet(128, sprite_frame_counts[i]);
    }
}

Player::~Player() {
    for (int i = 0; i < animation_count; ++i) {
        delete spritesheets[i];
    }
}

void Player::move(float dt, PlayerIntent intent) {
    if (dash_cooldown_timer > 0)
        dash_cooldown_timer = std::fmax(0, dash_cooldown_timer - dt);
    for (int i = 0; i < 4; ++i) {
        if (spell_cooldown_timers[i] > 0)
            spell_cooldown_timers[i] = std::fmax(0, spell_cooldown_timers[i] - dt);
    }
    if (fire_cooldown_timer > 0)
        fire_cooldown_timer = std::fmax(0, fire_cooldown_timer - dt);
    if (attack_cooldown_timer > 0)
        attack_cooldown_timer = std::fmax(0, attack_cooldown_timer - dt);
    if (hurt_timer > 0)
        hurt_timer = std::fmax(0.0f, hurt_timer - dt);
    if (slow_timer > 0)
        slow_timer = std::fmax(0.0f, slow_timer - dt);

    if (dead) {
        int death_frames = sprite_frame_counts[static_cast<int>(AnimationState::Death)];
        if (anim_timer >= death_spritechange) {
            anim_timer -= death_spritechange;
            if (texture_state < death_frames - 1)
                texture_state++;
        }
        return;
    }

    if (stun_timer > 0) {
        stun_timer = std::fmax(0.0f, stun_timer - dt);
        for (auto& p : projectiles) { move_projectile(p, dt); }
        advanceFrame(dt);
        return;
    }

    stamina.tick(dt, stats);

    mana = std::fmin(max_mana, mana + mana_regen * dt);

    bool combo_active = combo_timer > 0;
    if (combo_timer > 0) {
        combo_timer -= dt;
        if (combo_timer <= 0)
            combo_stage = 0;
    }

    if (is_dashing) {
        is_moving = false;
        dash_timer -= dt;

        float ds_mod = calc_dash_speed_mod(stats) * calc_armor_dash_speed_mod(equipment);
        float dd_mod = calc_dash_distance_mod(stats) * calc_armor_dash_dist_mod(equipment);
        vx = dash_dir_x * dash_speed * ds_mod * dd_mod;
        vy = dash_dir_y * dash_speed * ds_mod * dd_mod;
        if (dash_dir_x != 0 && dash_dir_y != 0) {
            vx *= 0.7071f;
            vy *= 0.7071f;
        }

        float nx = box.x + vx * dt;
        if (nx >= 0 && nx + playerw <= screenw)
            box.x = nx;
        float ny = box.y + vy * dt;
        if (ny >= 0 && ny + playerh <= screenh)
            box.y = ny;

        hitbox.x = box.x + playerw / 2 - hitbox_size;
        hitbox.y = box.y + playerh / 2 - hitbox_size;

        if (dash_timer <= 0) {
            is_dashing = false;
            is_iframe = false;
        }

        for (auto& p : projectiles) { move_projectile(p, dt); }
        advanceFrame(dt);
        return;
    }

    float spd_mod = calc_move_speed_mod(stats) * calc_armor_speed_mod(equipment);
    if (slow_timer > 0) spd_mod *= 0.5f;
    vx = intent.mx * speed * spd_mod;
    vy = intent.my * speed * spd_mod;

    if (intent.dash && !intent.fire && !is_attacking && dash_cooldown_timer <= 0) {
        float cost = calc_dash_stamina_cost(stats);
        if (stamina.can_afford(cost)) {
            stamina.spend(cost);
            is_dashing = true;
            is_iframe = true;
            dash_timer = dash_blink_duration;
            dash_cooldown_timer = dash_cooldown;
            dash_dir_x = static_cast<float>(direction.first);
            dash_dir_y = static_cast<float>(direction.second);
        }
    }

    if (is_attacking || is_firing) { vx = 0; vy = 0; }

    is_moving = (!is_attacking && !is_firing && (intent.mx != 0 || intent.my != 0));

    if (!is_attacking && !is_firing && (intent.mx != 0 || intent.my != 0))
        direction = {intent.mx, intent.my};

    if (intent.mx != 0 && intent.my != 0){
        vx *= 0.7071f;
        vy *= 0.7071f;}

    if (intent.mx != 0) {
        float nx = box.x + vx * dt;
        if (nx >= 0 && nx + playerw <= screenw)
           box.x = nx;
    }
    if (intent.my != 0) {
        float ny = box.y + vy * dt;
        if (ny >= 0 && ny + playerh <= screenh)
            box.y = ny;
    }

    if (!is_attacking && !is_firing) {
        hitbox.x = box.x + playerw / 2 - hitbox_size;
        hitbox.y = box.y + playerh / 2 - hitbox_size;
    }

    if (intent.attack && !is_attacking && !is_dashing && attack_cooldown_timer <= 0) {
        float cost = calc_melee_stamina_cost(stats);
        if (stamina.can_afford(cost)) {
            stamina.spend(cost);
            is_attacking = true;
            hit_this_swing = false;
            texture_state = 0;
            attack_anim_timer = 0;
            if (combo_active && combo_stage < max_combo_stage)
                combo_stage = combo_stage + 1;
            else
                combo_stage = 0;
            combo_timer = 0;

            weapon.is_swinging = true;
            weapon.swing_timer = 0.0f;

            float cx = box.x + box.w / 2.0f;
            float cy = box.y + box.h / 2.0f;
            float aim_dx = intent.aim_x - cx;
            float aim_dy = intent.aim_y - cy;
            melee_angle = std::atan2(aim_dy, aim_dx);
            float a = std::fmod(melee_angle + 2.0f * static_cast<float>(M_PI), 2.0f * static_cast<float>(M_PI));

            const float TWO_PI = 2.0f * static_cast<float>(M_PI);
            const float SECTOR_WIDTH = TWO_PI / 8.0f;

            float shifted_a = a + (SECTOR_WIDTH / 2.0f);
            int sector = static_cast<int>(shifted_a / SECTOR_WIDTH) % 8;
            static constexpr std::pair<int,int> mdirs[8] = {{ 1, 0},{ 1,-1},{ 0,-1},{-1,-1},{-1, 0},{-1, 1},{ 0, 1},{ 1, 1}};
            direction = mdirs[sector];
        }
    }

    if (intent.fire && fire_cooldown_timer <= 0 && !is_attacking && stamina.can_afford(fire_stamina_cost)) {
        int spell_idx = std::min(std::max(0, intent.selected_spell), 3);
        SpellType st = static_cast<SpellType>(spell_idx);
        const SpellProfile& sp = get_spell_profile(st);

        SpellType unlocked = get_spell_for_reasoning(stats.reasoning);
        if (static_cast<int>(st) > static_cast<int>(unlocked)) {
            st = unlocked;
            spell_idx = static_cast<int>(unlocked);
        }

        if (mana >= sp.mana_cost && spell_cooldown_timers[spell_idx] <= 0 &&
            stamina.can_afford(fire_stamina_cost)) {
            stamina.spend(fire_stamina_cost);
            mana -= sp.mana_cost;
            spell_cooldown_timers[spell_idx] = sp.cooldown;

            is_firing = true;
            fire_cooldown_timer = 0.2f;
            anim_timer = 0;
            fire_anim_timer = 0;
            texture_state = 0;
            combo_stage = 0;
            combo_timer = 0;

            float cx = box.x + box.w / 2.0f;
            float cy = box.y + box.h / 2.0f;

            float aim_dx = intent.aim_x - cx;
            float aim_dy = intent.aim_y - cy;
            float angle = std::atan2(aim_dy, aim_dx);

            trigger_cast_vfx = true;
            cast_vfx_angle = angle;

            float a = std::fmod(angle + 2 * M_PI, 2 * M_PI);
            int sector = static_cast<int>(std::floor((a + M_PI / 8.0) / (M_PI / 4.0))) % 8;
            static constexpr std::pair<int,int> dirs[8] = {
                {1, 0}, {1, -1}, {0, -1}, {-1, -1},
                {-1, 0}, {-1, 1}, {0, 1}, {1, 1}
            };
            direction = dirs[sector];

            if (sp.projectiles == 1 && sp.speed <= 0.0f) {
                SpellProjectile dummy;
                dummy.type = st;
                dummy.active = true;
                dummy.speed = 0.0f;
                float p_size = 20.0f;
                // Instant strike lands at the aim point, capped to max range;
                // collision then requires the target near the strike point.
                float aim_dist = std::sqrt(aim_dx * aim_dx + aim_dy * aim_dy);
                float range = std::min(aim_dist, 300.0f);
                float sx = cx, sy = cy;
                if (aim_dist > 1.0f) {
                    sx = cx + aim_dx / aim_dist * range;
                    sy = cy + aim_dy / aim_dist * range;
                }
                dummy.hitbox = {sx - p_size / 2.0f, sy - p_size / 2.0f, p_size, p_size};
                dummy.vx = 0; dummy.vy = 0;
                for (auto& p : projectiles) {
                    if (!p.active) { p = dummy; break; }
                }
            } else {
                int count = sp.projectiles;
                float spread_angle = (count > 1) ? 0.2f : 0.0f;
                float start_off = (count - 1) * spread_angle / -2.0f;
                for (int pi = 0; pi < count; ++pi) {
                    for (auto& p : projectiles) {
                        if (!p.active) {
                            float a_off = start_off + pi * spread_angle;
                            float tx = intent.aim_x;
                            float ty = intent.aim_y;
                            if (count > 1) {
                                float aim_angle = std::atan2(aim_dy, aim_dx) + a_off;
                                float dist = std::sqrt(aim_dx * aim_dx + aim_dy * aim_dy);
                                tx = cx + std::cos(aim_angle) * dist;
                                ty = cy + std::sin(aim_angle) * dist;
                            }
                            fire_spell_projectile(p, cx, cy, tx, ty, st, sp.speed);
                            break;
                        }
                    }
                }
            }
        }
    }

    for (auto& p : projectiles) { move_projectile(p, dt); }
    advanceFrame(dt);
}

void Player::draw(SDL_Renderer* renderer) {
    SDL_FRect src = get_texture_box();
    int action_idx = get_animation_index();

    src.y += 2.0f;
    src.h -= 2.0f;

    SDL_Texture* tex = textures[action_idx];
    if (tex) {
        float tw, th;
        SDL_GetTextureSize(tex, &tw, &th);
        if (src.x + src.w > tw || src.y + src.h > th) {
            fprintf(stderr, "WARN: %s sprite src (%.0f,%.0f %.0fx%.0f) exceeds texture (%.0fx%.0f)\n",
                    name.c_str(), src.x, src.y, src.w, src.h, tw, th);
        }
        SDL_RenderTexture(renderer, tex, &src, &box);
    } else {
        fprintf(stderr, "WARN: %s no texture for action_idx=%d\n", name.c_str(), action_idx);
    }

    if (weapon.texture && !dead) {
        float cx = box.x + box.w / 2.0f;
        float cy = box.y + box.h * 0.7f;
        float hand_dist = box.w * 0.25f;
        
        float hx = cx;
        float hy = cy;
        float angle = weapon.angle;
        
        if (weapon.is_swinging) {
            hx = cx + std::cos(melee_angle) * hand_dist;
            hy = cy + std::sin(melee_angle) * hand_dist;
        } else {
            float dir_angle = std::atan2(direction.second, direction.first);
            angle = dir_angle * 180.0f / static_cast<float>(M_PI) + 90.0f;
            
            float bob = 0.0f;
            if (is_moving) {
                float anim_phase = texture_state + (anim_timer / spritechange);
                bob = std::sin(anim_phase * static_cast<float>(M_PI) / 2.0f) * 3.0f;
                angle += std::sin(anim_phase * static_cast<float>(M_PI) / 2.0f) * 15.0f;
            } else if (hurt_timer <= 0.0f && !is_dashing) {
                // slow breathing bob
                float time_ms = SDL_GetTicks() / 1000.0f;
                bob = std::sin(time_ms * 2.0f) * 2.0f;
            }
            
            hx = cx + std::cos(dir_angle) * hand_dist;
            hy = cy + std::sin(dir_angle) * hand_dist + bob;
        }
        
        float weapon_width = 48.0f;
        float weapon_height = 64.0f;
        
        SDL_FPoint pivot;
        pivot.x = weapon_width / 2.0f;
        pivot.y = weapon_height;

        SDL_FRect dstrect = {hx - pivot.x, hy - pivot.y, weapon_width, weapon_height};

        SDL_RenderTextureRotated(
            renderer,
            weapon.texture,
            nullptr,
            &dstrect,
            angle,
            &pivot,
            SDL_FLIP_NONE
        );
    }

    for (auto& p : projectiles) {
        if (p.active && p.speed > 0.0f) {
            SDL_SetRenderDrawColor(renderer, 255, 200, 50, 255);
            SDL_RenderFillRect(renderer, &p.hitbox);
        }
    }
}

void Player::advanceFrame(float dt) {
    int idx = get_animation_index();
    int max_frames = sprite_frame_counts[idx];

    if (is_attacking) {
        weapon.is_swinging = true;
        weapon.swing_timer += dt;

        int anim_idx = get_animation_index();
        float total_frames = sprite_frame_counts[anim_idx];
        
        const WeaponProfile& wp = get_weapon_profile(equipment.weapon);
        float current_attack_spritechange = wp.cooldown;
        
        float total_time = total_frames * current_attack_spritechange;
        float progress = total_time > 0.0f ? weapon.swing_timer / total_time : 0.0f;
        progress = std::min(progress, 1.0f);

        float half_arc_deg = wp.half_arc * 180.0f / static_cast<float>(M_PI);
        float swing_deg = 0.0f;
        
        // Different weapons can have different swing patterns
        if (wp.type == WeaponType::Daggers) {
            // Daggers thrust/short swing
            if (combo_stage == 0) swing_deg = -half_arc_deg + 2.0f * half_arc_deg * progress;
            else if (combo_stage == 1) swing_deg = half_arc_deg - 2.0f * half_arc_deg * progress;
            else swing_deg = -half_arc_deg + 2.0f * half_arc_deg * progress;
        } else if (wp.type == WeaponType::Staff) {
            // Staff spins or swings slowly
            swing_deg = -half_arc_deg + progress * 180.0f;
        } else {
            // Standard weapons (Sword, GreatSword, Axe)
            if (combo_stage == 0) {
                swing_deg = -half_arc_deg + 2.0f * half_arc_deg * progress;
            } else if (combo_stage == 1) {
                swing_deg = half_arc_deg - 2.0f * half_arc_deg * progress;
            } else {
                swing_deg = -half_arc_deg + progress * 360.0f;
            }
        }
        
        float base_deg = melee_angle * 180.0f / static_cast<float>(M_PI) + 90.0f;
        weapon.angle = base_deg + swing_deg;

        attack_anim_timer += dt;
        if (attack_anim_timer >= current_attack_spritechange) {
            attack_anim_timer -= current_attack_spritechange;
            texture_state++;
            if (texture_state >= max_frames) {
                is_attacking = false;
                hit_this_swing = false;
                weapon.is_swinging = false;
                texture_state = 0;
                attack_cooldown_timer = melee_cooldown;
                if (combo_stage < max_combo_stage)
                    combo_timer = combo_window;
            }
        }
    } else {
        weapon.is_swinging = false;
        weapon.swing_timer = 0.0f;
        if (is_firing) {
            fire_anim_timer += dt;
            if (fire_anim_timer >= fire_spritechange) {
                fire_anim_timer -= fire_spritechange;
                texture_state++;
                if (texture_state >= max_frames) {
                    is_firing = false;
                    texture_state = 0;
                }
            }
        } else {
            anim_timer += dt;
            if (anim_timer >= spritechange) {
                anim_timer -= spritechange;
                texture_state = (texture_state + 1) % max_frames;
            }
        }
    }
    if (damage_flash > 0.0f) damage_flash -= dt;
}

void Player::load_texture(AnimationState state, SDL_Texture* tex) {
    textures[static_cast<int>(state)] = tex;
}

void Player::load_weapon_texture(SDL_Texture* tex) {
    weapon_texture = tex;
    weapon.texture = tex;
}

SDL_FRect Player::get_texture_box() {
    int idx = get_animation_index();
    return spritesheets[idx]->getSrc(dirIndex.at(direction), texture_state);
}

int Player::get_animation_index() const {
    if (dead) {
        return static_cast<int>(AnimationState::Death);
    }
    if (hurt_timer > 0.0f) {
        return static_cast<int>(AnimationState::Hurt);
    }
    if (is_attacking) {
        switch (combo_stage) {
            case 0: return static_cast<int>(AnimationState::Melee1);
            case 1: return static_cast<int>(AnimationState::Melee2);
            default: return static_cast<int>(AnimationState::MeleeSpin);
        }
    }
    if (is_firing) {
        return static_cast<int>(AnimationState::CastShoot);
    }
    if (is_dashing) {
        return static_cast<int>(AnimationState::Dash);
    }
    if (is_moving) {
        return static_cast<int>(AnimationState::Walk);
    }
    return static_cast<int>(AnimationState::Idle);
}

bool Player::is_weapon_owned(WeaponType type) const {
    int idx = static_cast<int>(type);
    return idx >= 0 && idx < weapon_count && owned_weapons[idx];
}

bool Player::can_afford(float cost) const {
    return dimes >= cost;
}

bool Player::purchase_stat_upgrade(StatType type) {
    float* stat = nullptr;
    switch (type) {
        case StatType::Strength:   stat = &stats.strength; break;
        case StatType::Vitality:   stat = &stats.vitality; break;
        case StatType::Agility:    stat = &stats.agility; break;
        case StatType::Reasoning:  stat = &stats.reasoning; break;
        case StatType::Endurance:  stat = &stats.endurance; break;
    }
    if (!stat || *stat >= max_stat_value) return false;
    float cost = UpgradeCosts::stat_cost(static_cast<int>(*stat));
    if (!can_afford(cost)) return false;
    dimes -= cost;
    *stat += 1.0f;
    return true;
}

bool Player::purchase_weapon(WeaponType type) {
    int idx = static_cast<int>(type);
    if (idx < 0 || idx >= weapon_count || owned_weapons[idx]) return false;
    float cost = get_weapon_shop_info(type).cost;
    if (!can_afford(cost)) return false;
    dimes -= cost;
    owned_weapons[idx] = true;
    return true;
}

bool Player::equip_weapon(WeaponType type) {
    int idx = static_cast<int>(type);
    if (idx < 0 || idx >= weapon_count || !owned_weapons[idx]) return false;
    if (equipment.weapon == type) return false;
    equipment.weapon = type;
    equip_load_ratio = calc_equip_load_ratio(equipment, stats);
    return true;
}

bool Player::purchase_weapon_upgrade(int weapon_index) {
    if (weapon_index < 0 || weapon_index >= weapon_count) return false;
    if (!owned_weapons[weapon_index]) return false;
    if (weapon_upgrade_levels[weapon_index] >= max_upgrade_level) return false;
    float cost = UpgradeCosts::weapon_cost(weapon_upgrade_levels[weapon_index]);
    if (!can_afford(cost)) return false;
    dimes -= cost;
    weapon_upgrade_levels[weapon_index]++;
    return true;
}

bool Player::purchase_armor_upgrade(ArmorSlot slot) {
    int idx = static_cast<int>(slot);
    if (idx < 0 || idx > 2 || armor_upgrade_levels[idx] >= max_upgrade_level) return false;
    float cost = UpgradeCosts::armor_cost(armor_upgrade_levels[idx]);
    if (!can_afford(cost)) return false;
    dimes -= cost;
    armor_upgrade_levels[idx]++;
    return true;
}

void Player::equip_weapon_texture(SDL_Renderer* renderer, const char* tex_file) {
    std::string path = std::string(asset_dir) + "/weapons/" + tex_file;
    SDL_Texture* tex = IMG_LoadTexture(renderer, path.c_str());
    if (tex) {
        if (weapon_texture) SDL_DestroyTexture(weapon_texture);
        weapon_texture = tex;
        weapon.texture = tex;
    }
}

void Player::reset(float x, float y) {
    box = {x, y, playerw, playerh};
    hitbox = {x + playerw / 2 - hitbox_size,  y + playerh / 2 - hitbox_size,
              hitbox_size * 2, hitbox_size * 2};
    is_firing = false;
    is_dashing = false;
    is_iframe = false;
    is_attacking = false;
    hit_this_swing = false;
    combo_stage = 0;
    dead = false;
    death_timer = 0.0f;
    texture_state = 0;
        weapon.is_swinging = false;
        weapon.swing_timer = 0.0f;
    weapon.angle = 0.0f;
    dash_timer = 0.0f;
    dash_cooldown_timer = 0.0f;
    fire_cooldown_timer = 0.0f;
    attack_cooldown_timer = 0.0f;
    combo_timer = 0.0f;
    hurt_timer = 0.0f;
    slow_timer = 0.0f;
        stun_timer = 0.0f;
        bleed_timer = 0.0f;
        bleed_dps = 0.0f;
        trigger_cast_vfx = false;
        trigger_aoe_tremor = false;
        cast_vfx_angle = 0.0f;
        damage_flash = 0.0f;
        damage_taken = 0.0f;
        is_moving = false;
        vx = 0.0f;
        vy = 0.0f;
        melee_angle = 0.0f;
        stamina.reset(stats);
    max_hp = calc_max_hp(stats);
    health = max_hp;
    max_mana = calc_max_mana(stats);
    mana = max_mana;
    mana_regen = calc_mana_regen(stats);
    equip_load_ratio = calc_equip_load_ratio(equipment, stats);
    for (int i = 0; i < 4; ++i) spell_cooldown_timers[i] = 0.0f;
    for (auto& p : projectiles) p.active = false;
}
