#pragma once
#include <string>
#include <array>
#include <utility>
#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
#include "Structures.h"
#include "Bullet.h"
#include "Constants.h"

class Player {
    public:
    Player(float x, float y, float speed, std::string name);

    void move(float dt, PlayerIntent intent);
    void draw(SDL_Renderer* renderer);
    void load_textures(SDL_Texture* idle, SDL_Texture* walk, SDL_Texture* bullet);

    SDL_FRect box;
    SDL_FRect hitbox;

    private:
    void advanceFrame(float dt);
    SDL_FRect get_texture_box();

    float speed;
    std::string name;
    std::pair<int,int> direction = {1, 0};
    SDL_Texture* texture {};
    SDL_Texture* idle_texture {};
    SDL_Texture* walk_texture {};
    Spritesheet spritesheet;
    std::array<Bullet, max_bullets / 2> bullets;

    float anim_timer {};
    int texture_state {};
};