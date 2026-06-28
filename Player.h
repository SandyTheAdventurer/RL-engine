#pragma once
#include <string>
#include <SDL3/SDL.h>
#include "Controls.h"

class Player {
    public:
    Player(float x, float y, float speed, std::string name, Controls controls);
    void move(float dt);
    SDL_FRect box;
    std::string name;

private:
    float x;
    float y;
    float speed;
    Controls controls;
};