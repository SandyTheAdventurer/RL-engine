#pragma once

#include <SDL3/SDL.h>
#include <utility>

struct Spritesheet
{
    static constexpr int TILE_SIZE = 128;
    static constexpr int COLS = 24;
    static constexpr int ROWS = 8;

    SDL_FRect getSrc(int row, int col) const;
    std::pair<int,int> getIndex(float x, float y) const;
};