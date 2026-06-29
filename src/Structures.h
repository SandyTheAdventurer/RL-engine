#pragma once

#include <SDL3/SDL.h>
#include <utility>

struct Controls
{
    SDL_Scancode up;
    SDL_Scancode down;
    SDL_Scancode left;
    SDL_Scancode right;
};

struct Spritesheet
{
    static constexpr int TILE_SIZE = 64;
    static constexpr int COLS = 15;
    static constexpr int ROWS = 8;

    SDL_FRect getSrc(int row, int col) const
    {
        return SDL_FRect{
            col * TILE_SIZE * 1.0f,
            row * TILE_SIZE * 1.0f,
            TILE_SIZE * 1.0f,
            TILE_SIZE * 1.0f
        };
    }

    std::pair<int,int> getIndex(float x, float y) const
    {
        return {
            static_cast<int>(y) / TILE_SIZE,
            static_cast<int>(x) / TILE_SIZE
        };
    }
};