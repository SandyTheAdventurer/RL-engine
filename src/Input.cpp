#include "Input.h"

PlayerIntent getHumanIntent(const FrameInput& input) {
    const bool* keys = SDL_GetKeyboardState(nullptr);
    PlayerIntent intent;
    intent.mx = (keys[SDL_SCANCODE_D] ? 1 : 0) - (keys[SDL_SCANCODE_A] ? 1 : 0);
    intent.my = (keys[SDL_SCANCODE_S] ? 1 : 0) - (keys[SDL_SCANCODE_W] ? 1 : 0);
    intent.fire = input.mouse_left_clicked;
    intent.aim_x = input.mouse_x;
    intent.aim_y = input.mouse_y;
    return intent;
}

PlayerIntent getBotIntent(SDL_Gamepad* ctrl, const SDL_FRect& bot_box, bool& prev_fire_btn) {
    PlayerIntent intent;
    if (!ctrl) return intent;

    float ax = SDL_GetGamepadAxis(ctrl, SDL_GAMEPAD_AXIS_LEFTX);
    float ay = SDL_GetGamepadAxis(ctrl, SDL_GAMEPAD_AXIS_LEFTY);
    intent.mx = (ax > 16384) ? 1 : (ax < -16384) ? -1 : 0;
    intent.my = (ay > 16384) ? 1 : (ay < -16384) ? -1 : 0;

    float rx = SDL_GetGamepadAxis(ctrl, SDL_GAMEPAD_AXIS_RIGHTX);
    float ry = SDL_GetGamepadAxis(ctrl, SDL_GAMEPAD_AXIS_RIGHTY);
    bool aim_valid = (rx > 16384 || rx < -16384 || ry > 16384 || ry < -16384);

    if (aim_valid) {
        float bot_cx = bot_box.x + playerw / 2.0f;
        float bot_cy = bot_box.y + playerh / 2.0f;
        intent.aim_x = bot_cx + (rx / 32767.0f) * 500.0f;
        intent.aim_y = bot_cy + (ry / 32767.0f) * 500.0f;
    }

    bool btn = SDL_GetGamepadButton(ctrl, SDL_GAMEPAD_BUTTON_SOUTH);
    intent.fire = btn && !prev_fire_btn && aim_valid;
    prev_fire_btn = btn;

    return intent;
}
