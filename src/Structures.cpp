#include "Structures.h"

SDL_FRect Spritesheet::getSrc(int row, int col) const
{
    return SDL_FRect{
        col * TILE_SIZE * 1.0f,
        row * TILE_SIZE * 1.0f,
        TILE_SIZE * 1.0f,
        TILE_SIZE * 1.0f
    };
}

std::pair<int,int> Spritesheet::getIndex(float x, float y) const
{
    return {
        static_cast<int>(y) / TILE_SIZE,
        static_cast<int>(x) / TILE_SIZE
    };
}
