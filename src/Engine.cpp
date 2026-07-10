#include "Engine.h"
#include "Collision.h"
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <SDL3_image/SDL_image.h>
#include <string>
#include <cstdio>
#include <stdexcept>

static constexpr int animation_count = static_cast<int>(AnimationState::Count);

Engine::Engine(bool vsync, bool render, Player& p1, Player& p2, int screenw, int screenh)
    : p1(p1), p2(p2), screenw(screenw), screenh(screenh), vsync(vsync), is_render(render)
{
    std::srand(static_cast<unsigned>(std::time(nullptr)));
    if (is_render) {
        if (!SDL_Init(SDL_INIT_VIDEO)) {
            throw std::runtime_error("Failed to initialize SDL video");
        }
        window = SDL_CreateWindow("RL Engine", screenw, screenh, 0);
        if (!window) {
            SDL_Quit();
            throw std::runtime_error("Failed to create window");
        }
        renderer = SDL_CreateRenderer(window, nullptr);
        if (!renderer) {
            SDL_DestroyWindow(window);
            window = nullptr;
            SDL_Quit();
            throw std::runtime_error("Failed to create renderer");
        }
        SDL_SetRenderVSync(renderer, vsync ? 1 : 0);

        for (int i = 0; i < animation_count; ++i) {
            std::string path = std::string(asset_dir) + "/" + animation_suffixes[i] + "/" + animation_suffixes[i] + ".png";
            tex_textures[i] = IMG_LoadTexture(renderer, path.c_str());
            if (!tex_textures[i]) {
                fprintf(stderr, "ERROR: Failed to load texture %s: %s\n", path.c_str(), SDL_GetError());
            } else {
                float tw, th;
                SDL_GetTextureSize(tex_textures[i], &tw, &th);
                fprintf(stderr, "OK: Loaded %s (%.0fx%.0f)\n", path.c_str(), tw, th);
            }
        }
        tex_bullet = IMG_LoadTexture(renderer, "assets/cast/cast.png");
        if (tex_bullet) {
            float tw, th;
            SDL_GetTextureSize(tex_bullet, &tw, &th);
            fprintf(stderr, "OK: Loaded bullet texture (%.0fx%.0f)\n", tw, th);
        } else {
            fprintf(stderr, "ERROR: Failed to load bullet texture %s\n", SDL_GetError());
        }

        static constexpr const char* weapon_files[6] = {
            "weapon_r0_c1.png",  // Katana -> stone sword
            "weapon_r0_c0.png",  // ShortSword -> wood sword
            "weapon_r6_c1.png",  // Daggers -> small blade
            "weapon_r0_c2.png",  // GreatSword -> gold sword
            "weapon_r7_c0.png",  // Shield
            "weapon_r3_c0.png",  // Staff -> yellow staff
        };
        for (int i = 0; i < 6; ++i) {
            std::string path = std::string(asset_dir) + "/weapons/" + weapon_files[i];
            tex_weapons[i] = IMG_LoadTexture(renderer, path.c_str());
        }

        for (int i = 0; i < animation_count; ++i) {
            p1.load_texture(static_cast<AnimationState>(i), tex_textures[i]);
            p2.load_texture(static_cast<AnimationState>(i), tex_textures[i]);
        }
        p1.load_weapon_texture(tex_weapons[static_cast<int>(p1.equipment.weapon)]);
        p2.load_weapon_texture(tex_weapons[static_cast<int>(p2.equipment.weapon)]);

        for (Bullet& b : p1.bullets) { b.load_textures(tex_bullet); }
        for (Bullet& b : p2.bullets) { b.load_textures(tex_bullet); }
    }
}

Engine::~Engine() {
    close();
}

void Engine::reset(float p1_x, float p1_y, float p2_x, float p2_y) {
    if (p1_x < 0) p1_x = (screenw / 2.0f) - playerw * 2;
    if (p1_y < 0) p1_y = (screenh - playerh) / 2.0f;
    if (p2_x < 0) p2_x = (screenw / 2.0f) + playerw;
    if (p2_y < 0) p2_y = (screenh - playerh) / 2.0f;
    p1.reset(p1_x, p1_y);
    p2.reset(p2_x, p2_y);
    done = false;
}

void Engine::step(PlayerIntent& pi1, PlayerIntent& pi2, float dt) {
    p1.move(dt, pi1);
    p2.move(dt, pi2);

    check_melee_collision(&p1, &p2);
    check_players_collision(&p1, &p2);
    check_bullet_collision(&p1, &p2);

    if (p1.health <= 0 || p2.health <= 0) {
        done = true;
    }
}

void Engine::render() {
    if (!renderer) return;

    SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
    SDL_RenderClear(renderer);
    p1.draw(renderer);
    p2.draw(renderer);
}

std::array<float, obs_dim> Engine::observe(const Player& self, const Player& enemy) {
    std::array<float, obs_dim> obs{};
    size_t i = 0;

    float self_cx = self.box.x + playerw / 2.0f;
    float self_cy = self.box.y + playerh / 2.0f;
    float enemy_cx = enemy.box.x + playerw / 2.0f;
    float enemy_cy = enemy.box.y + playerh / 2.0f;

    obs[i++] = self.health / self.max_hp;
    obs[i++] = static_cast<float>(self.ammo) / max_ammo;
    obs[i++] = self.is_reloading ? 1.0f : 0.0f;
    obs[i++] = self.is_dashing ? 1.0f : 0.0f;
    obs[i++] = self_cx / screenw;
    obs[i++] = self_cy / screenh;
    obs[i++] = self.vx / playerspeed;
    obs[i++] = self.vy / playerspeed;

    obs[i++] = enemy.health / enemy.max_hp;
    obs[i++] = (enemy_cx - self_cx) / screenw;
    obs[i++] = (enemy_cy - self_cy) / screenh;
    obs[i++] = enemy.vx / playerspeed;
    obs[i++] = enemy.vy / playerspeed;

    constexpr int half = max_bullets / 2;
    constexpr float sentinel = -2.0f;

    for (int j = 0; j < half; j++) {
        const Bullet& b = self.bullets[j];
        if (b.isShot) {
            float bx = b.hitbox.x + bulletw / 2.0f;
            float by = b.hitbox.y + bulleth / 2.0f;
            auto vel = b.getVel();
            obs[i++] = 1.0f;
            obs[i++] = (bx - self_cx) / screenw;
            obs[i++] = (by - self_cy) / screenh;
            obs[i++] = vel[0] / bullet_speed;
            obs[i++] = vel[1] / bullet_speed;
        } else {
            obs[i++] = 0.0f;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
        }
    }
    for (int j = 0; j < half; j++) {
        const Bullet& b = enemy.bullets[j];
        if (b.isShot) {
            float bx = b.hitbox.x + bulletw / 2.0f;
            float by = b.hitbox.y + bulleth / 2.0f;
            auto vel = b.getVel();
            obs[i++] = 1.0f;
            obs[i++] = (bx - self_cx) / screenw;
            obs[i++] = (by - self_cy) / screenh;
            obs[i++] = vel[0] / bullet_speed;
            obs[i++] = vel[1] / bullet_speed;
        } else {
            obs[i++] = 0.0f;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
        }
    }

    float dx = enemy_cx - self_cx;
    float dy = enemy_cy - self_cy;
    obs[i++] = std::sqrt(dx * dx + dy * dy) / max_dist;

    obs[i++] = self.is_attacking ? 1.0f : 0.0f;
    obs[i++] = static_cast<float>(self.combo_stage) / max_combo_stage;

    obs[i++] = self.stats.strength / max_stat_value;
    obs[i++] = self.stats.vitality / max_stat_value;
    obs[i++] = self.stats.agility / max_stat_value;
    obs[i++] = self.stats.reasoning / max_stat_value;
    obs[i++] = self.stats.endurance / max_stat_value;
    obs[i++] = self.stamina.current / self.stamina.max_stamina;
    obs[i++] = self.equip_load_ratio;

    return obs;
}

void Engine::present() {
    if (renderer) SDL_RenderPresent(renderer);
}

void Engine::close() {
    if (renderer) {
        for (int i = 0; i < animation_count; ++i) {
            SDL_DestroyTexture(tex_textures[i]);
        }
        for (int i = 0; i < 6; ++i) {
            SDL_DestroyTexture(tex_weapons[i]);
        }
        SDL_DestroyTexture(tex_bullet);

        SDL_DestroyRenderer(renderer);
        renderer = nullptr;
    }
    if (window) {
        SDL_DestroyWindow(window);
        window = nullptr;
    }
    if (is_render) {
        SDL_Quit();
    }
}