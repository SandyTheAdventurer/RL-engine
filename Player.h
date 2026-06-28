#pragma once
#include <string>
#include <utility>
#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
#include "Structures.h"
class Player {
    public:
    Player(float x, float y, float speed, std::string name, Controls controls);
    void move(float dt);
    void load_textures(SDL_Texture* idle, SDL_Texture* walk);
    SDL_FRect get_texture_box();
    SDL_FRect box;
    std::string name;
    SDL_Texture* texture;
    int texture_state = 0;
    
    private:
    float x;
    float y;
    float speed;
    std::pair<int,int> direction = {1, 0};
    Controls controls;
    SDL_Texture* idle_texture;
    SDL_Texture* walk_texture;
    Spritesheet spritesheet;
};