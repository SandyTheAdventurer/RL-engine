#pragma once
#include <SDL3/SDL.h>
#include <array>
#include "Constants.h"
#include "Player.h"

class Engine {
public:
    Engine(bool vsync, bool render, Player& p1, Player& p2, int screenw, int screenh);
    ~Engine();

    void step(PlayerIntent& pi1, PlayerIntent& pi2, float dt);
    void render();
    void present();
    std::array<float, 76> observe(const Player& self, const Player& enemy);
    void reset(float p1_x = -1, float p1_y = -1, float p2_x = -1, float p2_y = -1);
    void close();

    bool is_done() const { return done; }
    Player& player1() { return p1; }
    Player& player2() { return p2; }

    SDL_Renderer* renderer = nullptr;

private:
    SDL_Window* window = nullptr;
    Player& p1;
    Player& p2;
    int screenw, screenh;
    bool vsync;
    bool is_render;
    bool done = false;

    SDL_Texture* tex_idle = nullptr;
    SDL_Texture* tex_walk = nullptr;
    SDL_Texture* tex_run = nullptr;
    SDL_Texture* tex_shoot = nullptr;
    SDL_Texture* tex_bullet = nullptr;
    SDL_Texture* tex_melee1 = nullptr;
    SDL_Texture* tex_melee2 = nullptr;
    SDL_Texture* tex_melee_spin = nullptr;
    SDL_Texture* tex_hurt = nullptr;
};
