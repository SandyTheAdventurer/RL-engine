#include "Events.h"
#include <SDL3/SDL.h>

FrameInput pollEvents() {
    FrameInput input;
    SDL_GetMouseState(&input.mouse_x, &input.mouse_y);
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
        }
    }
    return input;
}
