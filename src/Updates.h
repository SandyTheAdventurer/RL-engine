#pragma once

#include <SDL3/SDL.h>
#include "Constants.h"

inline float deltaTime(Uint64& previous)
{
    Uint64 current = SDL_GetPerformanceCounter();
    float dt = (float)(current - previous) / SDL_GetPerformanceFrequency();
    previous = current;
    return dt;
}