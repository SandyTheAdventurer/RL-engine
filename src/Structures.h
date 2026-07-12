#pragma once

#include <SDL3/SDL.h>
#include <utility>

struct Spritesheet
{
    int TILE_SIZE;
    int COLS;
    static constexpr int ROWS = 8;

    Spritesheet(int tile_size, int cols);

    SDL_FRect getSrc(int row, int col) const;
};