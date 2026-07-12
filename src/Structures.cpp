#include "Structures.h"

Spritesheet::Spritesheet(int tile_size, int cols)
    : TILE_SIZE(tile_size), COLS(cols)
{
}

SDL_FRect Spritesheet::getSrc(int row, int col) const
{
    return SDL_FRect{
        col * TILE_SIZE * 1.0f,
        row * TILE_SIZE * 1.0f,
        TILE_SIZE * 1.0f,
        TILE_SIZE * 1.0f
    };
}