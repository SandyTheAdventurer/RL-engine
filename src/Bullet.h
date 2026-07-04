#pragma once
#include <SDL3/SDL.h>
#include <array>

class Bullet {
    public:
    void draw(SDL_Renderer* renderer);
    void move(float dt);
    void load_textures(SDL_Texture* bullet);
    void fire(float x, float y, float tx, float ty);
    float getVx() const { return vx; }
    float getVy() const { return vy; }

    bool isLoaded = true;
    bool isShot = false;
    std::array<float, 2> getVel() const;
    SDL_FRect hitbox;

    private:
    float angle;
    float vx;
    float vy;
    SDL_Texture* texture;
};
