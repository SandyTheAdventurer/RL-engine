#include "Input.h"

PlayerIntent getHumanIntent(const FrameInput& input) {
    const bool* keys = SDL_GetKeyboardState(nullptr);
    PlayerIntent intent;
    intent.mx = (keys[SDL_SCANCODE_D] ? 1 : 0) - (keys[SDL_SCANCODE_A] ? 1 : 0);
    intent.my = (keys[SDL_SCANCODE_S] ? 1 : 0) - (keys[SDL_SCANCODE_W] ? 1 : 0);
    intent.attack = input.mouse_left_clicked;
    intent.fire = input.mouse_right_clicked;
    intent.dash = (keys[SDL_SCANCODE_LSHIFT]);
    intent.aim_x = input.mouse_x;
    intent.aim_y = input.mouse_y;

    if (keys[SDL_SCANCODE_1]) intent.selected_spell = 0;
    else if (keys[SDL_SCANCODE_2]) intent.selected_spell = 1;
    else if (keys[SDL_SCANCODE_3]) intent.selected_spell = 2;
    else if (keys[SDL_SCANCODE_4]) intent.selected_spell = 3;

    return intent;
}
