#include "Engine.h"
#include "Collision.h"
#include <SDL3_image/SDL_image.h>
#include <stdexcept>

Engine::Engine(bool vsync, bool render, Player& p1, Player& p2, int screenw, int screenh)
    : p1(p1), p2(p2), screenw(screenw), screenh(screenh), vsync(vsync), is_render(render)
{
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

        tex_idle   = IMG_LoadTexture(renderer, idle_sheet_path);
        tex_walk   = IMG_LoadTexture(renderer, walk_sheet_path);
        tex_shoot  = IMG_LoadTexture(renderer, shoot_sheet_path);
        tex_bullet = IMG_LoadTexture(renderer, bullet_sheet_path);
        p1.load_textures(tex_idle, tex_walk, tex_shoot, tex_bullet);
        p2.load_textures(tex_idle, tex_walk, tex_shoot, tex_bullet);
    }
}

Engine::~Engine() {
    close();
}

void Engine::reset() {
    p1.reset((screenw / 2.0f) - playerw * 2, (screenh - playerh) / 2.0f);
    p2.reset((screenw / 2.0f) + playerw, (screenh - playerh) / 2.0f);
    done = false;
}

void Engine::step(PlayerIntent& pi1, PlayerIntent& pi2, float dt) {
    p1.move(dt, pi1);
    p2.move(dt, pi2);

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

std::array<float, 70> Engine::observe(const Player& self, const Player& enemy) {
    std::array<float, 70> obs{};
    size_t i = 0;

    obs[i++] = self.health;
    obs[i++] = enemy.health;
    obs[i++] = self.box.x;
    obs[i++] = self.box.y;
    obs[i++] = enemy.box.x;
    obs[i++] = enemy.box.y;
    obs[i++] = self.vx;
    obs[i++] = self.vy;
    obs[i++] = enemy.vx;
    obs[i++] = enemy.vy;

    constexpr int half = max_bullets / 2;

    for (int j = 0; j < half; j++)
        obs[i++] = self.bullets[j].isShot ? 1.0f : 0.0f;
    for (int j = 0; j < half; j++)
        obs[i++] = self.bullets[j].isLoaded ? 1.0f : 0.0f;

    for (int j = 0; j < half; j++) {
        obs[i++] = self.bullets[j].isShot ? self.bullets[j].hitbox.x : -1.0f;
        obs[i++] = self.bullets[j].isShot ? self.bullets[j].hitbox.y : -1.0f;
    }
    for (int j = 0; j < half; j++) {
        obs[i++] = enemy.bullets[j].isShot ? enemy.bullets[j].hitbox.x : -1.0f;
        obs[i++] = enemy.bullets[j].isShot ? enemy.bullets[j].hitbox.y : -1.0f;
    }

    for (int j = 0; j < half; j++) {
        auto vel = self.bullets[j].getVel();
        obs[i++] = self.bullets[j].isShot ? vel[0] : -1.0f;
        obs[i++] = self.bullets[j].isShot ? vel[1] : -1.0f;
    }
    for (int j = 0; j < half; j++) {
        auto vel = enemy.bullets[j].getVel();
        obs[i++] = enemy.bullets[j].isShot ? vel[0] : -1.0f;
        obs[i++] = enemy.bullets[j].isShot ? vel[1] : -1.0f;
    }

    return obs;
}

void Engine::present() {
    if (renderer) SDL_RenderPresent(renderer);
}

void Engine::close() {
    if (renderer) {
        SDL_DestroyTexture(tex_bullet);
        SDL_DestroyTexture(tex_shoot);
        SDL_DestroyTexture(tex_walk);
        SDL_DestroyTexture(tex_idle);
        tex_idle = tex_walk = tex_shoot = tex_bullet = nullptr;

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
