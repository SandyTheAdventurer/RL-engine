#pragma once

#include <SDL3/SDL.h>

inline bool pollQuit()
{
    SDL_Event event;
    while (SDL_PollEvent(&event))
        if (event.type == SDL_EVENT_QUIT)
            return true;
    return false;
}