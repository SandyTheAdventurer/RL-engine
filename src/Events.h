#pragma once

#include <SDL3/SDL.h>
#include "Constants.h"
inline FrameInput pollEvents() {
    FrameInput input;
    SDL_Event event;
    while (SDL_PollEvent(&event)) {
        if (event.type == SDL_EVENT_QUIT)
            input.quit = true;
        else if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN)
        {
            if(event.button.button == SDL_BUTTON_LEFT) {
                input.mouse_left_clicked = true;
            }
            if(event.button.button == SDL_BUTTON_RIGHT) {
                input.mouse_right_clicked = true;
            }
            input.mouse_x = event.button.x;
            input.mouse_y = event.button.y;
        }
    }
    return input;
}