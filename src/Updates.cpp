#include "Updates.h"

float deltaTime(Uint64& previous)
{
    Uint64 current = SDL_GetPerformanceCounter();
    float dt = (float)(current - previous) / SDL_GetPerformanceFrequency();
    previous = current;
    return dt;
}
