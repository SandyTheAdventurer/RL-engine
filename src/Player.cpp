#include "Player.h"
#include "Constants.h"
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
    if (fire_cooldown_timer > 0)
        fire_cooldown_timer = std::fmax(0, fire_cooldown_timer - dt);
    if (attack_cooldown_timer > 0)
        attack_cooldown_timer = std::fmax(0, attack_cooldown_timer - dt);
    if (hurt_timer > 0)
        hurt_timer = std::fmax(0.0f, hurt_timer - dt);
    stamina.tick(dt, stats);
    bool combo_active = combo_timer > 0;
    if (combo_timer > 0) {
        combo_timer -= dt;
        if (combo_timer <= 0)
            combo_stage = 0;
    }
    if (is_reloading) {
        reload_timer -= dt;
        if (reload_timer <= 0) {
            ammo = max_ammo;
            is_reloading = false;
        }
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

        for (Bullet& b : bullets) { b.move(dt); }
        advanceFrame(dt);
        return;
    }

    if (intent.reload && !is_reloading && !is_dashing && ammo < max_ammo) {
        is_reloading = true;
        reload_timer = reload_time;
    }

    float spd_mod = calc_move_speed_mod(stats) * calc_armor_speed_mod(equipment);
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
                if (combo_active)
                    combo_stage = std::min(combo_stage + 1, max_combo_stage);
                else
                    combo_stage = 0;
                combo_timer = 0;

                weapon.is_swinging = true;
                weapon.combo_step = combo_stage + 1;
                weapon.swing_timer = 0.0f;

                float cx = box.x + box.w / 2.0f;
                float cy = box.y + box.h / 2.0f;
                float aim_dx = intent.aim_x - cx;
                float aim_dy = intent.aim_y - cy;
                melee_angle = std::atan2(aim_dy, aim_dx);
                float a = std::fmod(melee_angle + 2.0f * static_cast<float>(M_PI), 2.0f * static_cast<float>(M_PI)) + 1;

                const float TWO_PI = 2.0f * static_cast<float>(M_PI);
                const float SECTOR_WIDTH = TWO_PI / 8.0f;

                float shifted_a = a + (SECTOR_WIDTH / 2.0f);
                int sector = static_cast<int>(shifted_a / SECTOR_WIDTH) % 8;
                static constexpr std::pair<int,int> mdirs[8] = {{ 1, 0},{ 1,-1},{ 0,-1},{-1,-1},{-1, 0},{-1, 1},{ 0, 1},{ 1, 1}};
                direction = mdirs[sector];
            }
        }

    if (intent.fire && ammo > 0 && fire_cooldown_timer <= 0 && !is_reloading && !is_attacking) {
        for(Bullet& b: bullets) {
            if(b.isLoaded) {
                b.fire(box.x + box.w / 2, box.y + box.h / 2, intent.aim_x, intent.aim_y);
                is_firing = true;
                fire_cooldown_timer = fire_rate;
                ammo--;
                anim_timer = 0;
                fire_anim_timer = 0;
                texture_state = 0;
                combo_stage = 0;
                combo_timer = 0;

                float aim_dx = intent.aim_x - (box.x + box.w / 2);
                float aim_dy = intent.aim_y - (box.y + box.h / 2);
                float angle = std::atan2(aim_dy, aim_dx);
                float a = std::fmod(angle + 2 * M_PI, 2 * M_PI);
                int sector = static_cast<int>(std::floor((a + M_PI / 8.0) / (M_PI / 4.0))) % 8;
                static constexpr std::pair<int,int> dirs[8] = {
                    {1, 0}, {1, -1}, {0, -1}, {-1, -1},
                    {-1, 0}, {-1, 1}, {0, 1}, {1, 1}
                };
                direction = dirs[sector];

                break;
            }
        }
        if (ammo == 0 && !is_reloading) {
            is_reloading = true;
            reload_timer = reload_time;
        }
    }

    for(Bullet& b: bullets) {b.move(dt);}
    advanceFrame(dt);
}

void Player::draw(SDL_Renderer* renderer) {
    SDL_FRect src = get_texture_box();
    int action_idx = get_animation_index();

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

    if (weapon.is_swinging && weapon.texture) {
        float cx = box.x + box.w / 2.0f;
        float cy = box.y + box.h / 2.0f;
        float hand_dist = box.w * 0.25f;
        float hx = cx + std::cos(melee_angle) * hand_dist;
        float hy = cy + std::sin(melee_angle) * hand_dist;
        
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
            weapon.angle, 
            &pivot,
            SDL_FLIP_NONE
        );
    }

    float bar_y = box.y - bar_y_offset;

    SDL_FRect hp_bg = {box.x, bar_y, box.w, bar_h};
    SDL_SetRenderDrawColor(renderer, 60, 60, 60, 255);
    SDL_RenderFillRect(renderer, &hp_bg);
    float hp_ratio = health / max_hp;
    SDL_FRect hp_fill = {box.x, bar_y - 50.0f, box.w * hp_ratio, bar_h};
    SDL_SetRenderDrawColor(renderer, 255, 0, 0, 255);
    SDL_RenderFillRect(renderer, &hp_fill);

    float stam_y = bar_y + bar_h + 2;
    SDL_FRect stam_bg = {box.x, stam_y, box.w, bar_h - 2};
    SDL_SetRenderDrawColor(renderer, 40, 40, 50, 255);
    SDL_RenderFillRect(renderer, &stam_bg);
    float stam_ratio = stamina.current / stamina.max_stamina;
    SDL_FRect stam_fill = {box.x, stam_y, box.w * stam_ratio, bar_h - 2};
    if (stamina.current <= 0.0f) {
        SDL_SetRenderDrawColor(renderer, 255, 100, 100, 255);
    } else {
        SDL_SetRenderDrawColor(renderer, 100, 200, 255, 255);
    }
    SDL_RenderFillRect(renderer, &stam_fill);

    float ammo_y = stam_y + (bar_h - 2) + 2;
    float dot_w = 8;
    float dot_h = 6;
    float dot_gap = 3;
    float total_w = max_ammo * dot_w + (max_ammo - 1) * dot_gap;
    float dot_start = box.x + (box.w - total_w) / 2;

    for (int i = 0; i < max_ammo; i++) {
        SDL_FRect dot = {dot_start + i * (dot_w + dot_gap), ammo_y, dot_w, dot_h};
        if (i < ammo)
            SDL_SetRenderDrawColor(renderer, 255, 200, 0, 255);
        else
            SDL_SetRenderDrawColor(renderer, 60, 60, 60, 255);
        SDL_RenderFillRect(renderer, &dot);
    }

    if (is_reloading) {
        float reload_y = ammo_y + dot_h + 3;
        SDL_FRect reload_bg = {box.x, reload_y, box.w, bar_h};
        SDL_SetRenderDrawColor(renderer, 40, 40, 40, 255);
        SDL_RenderFillRect(renderer, &reload_bg);
        float progress = 1.0f - (reload_timer / reload_time);
        SDL_FRect reload_fill = {box.x, reload_y, box.w * progress, bar_h};
        SDL_SetRenderDrawColor(renderer, 255, 200, 0, 255);
        SDL_RenderFillRect(renderer, &reload_fill);
    }

    for(Bullet& b: bullets) {b.draw(renderer);}
}

void Player::advanceFrame(float dt) {
    int idx = get_animation_index();
    int max_frames = sprite_frame_counts[idx];

    if (is_attacking) {
        weapon.is_swinging = true;
        weapon.swing_timer += dt;

        int anim_idx = get_animation_index();
        float total_frames = sprite_frame_counts[anim_idx];
        float total_time = total_frames * attack_spritechange;
        float progress = total_time > 0.0f ? weapon.swing_timer / total_time : 0.0f;
        progress = std::min(progress, 1.0f);

        float half_arc_deg = melee_half_arc * 180.0f / static_cast<float>(M_PI);
        float swing_deg = 0.0f;
        if (combo_stage == 0) {
            swing_deg = -half_arc_deg + 2.0f * half_arc_deg * progress;
        } else if (combo_stage == 1) {
            swing_deg = half_arc_deg - 2.0f * half_arc_deg * progress;
        } else {
            swing_deg = -half_arc_deg + progress * 360.0f;
        }
        float base_deg = melee_angle * 180.0f / static_cast<float>(M_PI) + 90.0f;
        weapon.angle = base_deg + swing_deg;

        attack_anim_timer += dt;
        if (attack_anim_timer >= attack_spritechange) {
            attack_anim_timer -= attack_spritechange;
            texture_state++;
            if (texture_state >= max_frames) {
                is_attacking = false;
                weapon.is_swinging = false;
                texture_state = 0;
                attack_cooldown_timer = melee_cooldown;
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

void Player::reset(float x, float y) {
    box = {x, y, playerw, playerh};
    hitbox = {x + playerw / 2 - hitbox_size,  y + playerh / 2 - hitbox_size,
              hitbox_size * 2, hitbox_size * 2};
    is_firing = false;
    is_dashing = false;
    is_iframe = false;
    is_reloading = false;
    is_attacking = false;
    hit_this_swing = false;
    combo_stage = 0;
    weapon.is_swinging = false;
    weapon.combo_step = 1;
    weapon.swing_timer = 0.0f;
    weapon.angle = 0.0f;
    dash_timer = 0.0f;
    dash_cooldown_timer = 0.0f;
    reload_timer = 0.0f;
    fire_cooldown_timer = 0.0f;
    attack_cooldown_timer = 0.0f;
    combo_timer = 0.0f;
    hurt_timer = 0.0f;
    melee_hitbox = {0, 0, 0, 0};
    ammo = max_ammo;
    stamina.reset(stats);
    max_hp = calc_max_hp(stats);
    health = max_hp;
    equip_load_ratio = calc_equip_load_ratio(equipment, stats);
    for(Bullet& b:bullets) {b.isLoaded = true; b.isShot = false;}
}