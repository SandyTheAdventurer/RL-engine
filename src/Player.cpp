#include "Player.h"
#include "Constants.h"
#include <math.h>

Player::Player(float x, float y, float speed, std::string name)
    : speed(speed),
    name(name)
{
    box = {x, y, playerw, playerh};
    hitbox = {x + playerw / 2 - hitbox_size,  y + playerh / 2 - hitbox_size,
              hitbox_size * 2, hitbox_size * 2};
}

Player::~Player() {
}

void Player::move(float dt, PlayerIntent intent) {
    if (dash_cooldown_timer > 0)
        dash_cooldown_timer = std::fmax(0, dash_cooldown_timer - dt);
    if (fire_cooldown_timer > 0)
        fire_cooldown_timer = std::fmax(0, fire_cooldown_timer - dt);
    if (is_reloading) {
        reload_timer -= dt;
        if (reload_timer <= 0) {
            ammo = max_ammo;
            is_reloading = false;
        }
    }

    if (is_dashing) {
        dash_timer -= dt;

        vx = dash_dir_x * dash_speed;
        vy = -dash_dir_y * dash_speed;
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

        texture = run_texture;
        for (Bullet& b : bullets) { b.move(dt); }
        advanceFrame(dt);
        return;
    }

    if (intent.reload && !is_reloading && !is_dashing && ammo < max_ammo) {
        is_reloading = true;
        reload_timer = reload_time;
    }

    vx = intent.mx * speed;
    vy = intent.my * speed;

    if (intent.dash && !intent.fire && dash_cooldown_timer <= 0) {
        is_dashing = true;
        is_iframe = true;
        dash_timer = dash_blink_duration;
        dash_cooldown_timer = dash_cooldown;
        dash_dir_x = static_cast<float>(direction.first);
        dash_dir_y = static_cast<float>(direction.second);
    }

    if(is_firing){vx = 0; vy = 0;}

    if (!is_firing && (intent.mx != 0 || intent.my != 0))
        direction = {intent.mx, -intent.my};

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

    if(!is_firing){
    hitbox.x = box.x + playerw / 2 - hitbox_size;
    hitbox.y = box.y + playerh / 2 - hitbox_size;}

    if (intent.fire && ammo > 0 && fire_cooldown_timer <= 0 && !is_reloading) {
        for(Bullet& b: bullets) {
            if(b.isLoaded) {
                b.fire(box.x + playerw / 2, box.y + playerh / 2, intent.aim_x, intent.aim_y);
                is_firing = true;
                fire_cooldown_timer = fire_rate;
                ammo--;
                anim_timer = 0;
                fire_anim_timer = 0;
                texture_state = 0;

                float aim_dx = intent.aim_x - (box.x + playerw / 2);
                float aim_dy = (box.y + playerh / 2) - intent.aim_y;
                float angle = std::atan2(aim_dy, aim_dx);
                float a = std::fmod(angle + 2 * M_PI, 2 * M_PI);
                int sector = static_cast<int>(std::floor((a + M_PI / 8.0) / (M_PI / 4.0))) % 8;
                static constexpr std::pair<int,int> dirs[8] = {
                    {1, 0}, {1, 1}, {0, 1}, {-1, 1},
                    {-1, 0}, {-1, -1}, {0, -1}, {1, -1}
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

    if (is_firing)
        texture = shoot_texture;
    else
        texture = (intent.mx == 0 && intent.my == 0) ? idle_texture : walk_texture;

    for(Bullet& b: bullets) {b.move(dt);}
    advanceFrame(dt);
}

void Player::draw(SDL_Renderer* renderer) {
    SDL_FRect src = get_texture_box();
    SDL_RenderTexture(renderer, texture, &src, &box);

    float bar_y = box.y - bar_y_offset;
    SDL_FRect bar_bg = {box.x, bar_y, box.w, bar_h};
    SDL_SetRenderDrawColor(renderer, 60, 60, 60, 255);
    SDL_RenderFillRect(renderer, &bar_bg);

    float ratio = health / max_health;
    SDL_FRect bar_fill = {box.x, bar_y, box.w * ratio, bar_h};
    SDL_SetRenderDrawColor(renderer, 255, 0, 0, 255);
    SDL_RenderFillRect(renderer, &bar_fill);

    float ammo_y = bar_y + bar_h + 3;
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
    if (is_firing) {
        fire_anim_timer += dt;
        if (fire_anim_timer >= fire_spritechange) {
            fire_anim_timer -= fire_spritechange;
            texture_state++;
            if (texture_state >= 15) {
                is_firing = false;
                texture_state = 0;
            }
        }
    } else {
        anim_timer += dt;
        if (anim_timer >= spritechange) {
            anim_timer -= spritechange;
            texture_state = (texture_state + 1) % 15;
        }
    }
}

void Player::load_textures(SDL_Texture* idle, SDL_Texture* walk, SDL_Texture* run, SDL_Texture* shoot, SDL_Texture* bullet)
{
    idle_texture = idle;
    walk_texture = walk;
    run_texture = run;
    shoot_texture = shoot;
    texture = idle;
    for(Bullet& b: bullets){b.load_textures(bullet);}
}

SDL_FRect Player::get_texture_box() {
    return spritesheet.getSrc(dirIndex.at(direction), texture_state);
}

void Player::reset(float x, float y) {
    box = {x, y, playerw, playerh};
    hitbox = {x + playerw / 2 - hitbox_size,  y + playerh / 2 - hitbox_size,
              hitbox_size * 2, hitbox_size * 2};
    is_firing = false;
    is_dashing = false;
    is_iframe = false;
    is_reloading = false;
    dash_timer = 0.0f;
    dash_cooldown_timer = 0.0f;
    reload_timer = 0.0f;
    fire_cooldown_timer = 0.0f;
    ammo = max_ammo;
    health = max_health;
    for(Bullet& b:bullets) {b.isLoaded = true; b.isShot = false;}
}