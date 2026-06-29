#pragma once
#include <SDL3/SDL.h>

class Bullet {
    public:
    void draw(SDL_Renderer* renderer);
    void move(float dt);
    void load_textures(SDL_Texture* bullet);
    void fire(float x, float y, float tx, float ty);
    bool isLoaded = true;
    bool isShot = false;
    SDL_FRect hitbox;
    
    private:
    float angle;
    float vx;
    float vy;
    SDL_Texture* texture;
};