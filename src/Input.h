#pragma once
#include "Constants.h"
#include <SDL3/SDL.h>

PlayerIntent getHumanIntent(const FrameInput& input);
PlayerIntent getBotIntent(SDL_Gamepad* ctrl, const SDL_FRect& bot_box, bool& prev_fire_btn);
