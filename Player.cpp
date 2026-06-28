#include "Player.h"
#include "Constants.h"

Player::Player(float x, float y, float speed, std::string name, Controls controls)
    : x(x),
    y(y),
    speed(speed),
    name(name),
    controls(controls)
{
    box = {x, y, playerw, playerh};
}

void Player::move(float dt) {
    const bool* keys = SDL_GetKeyboardState(nullptr);
    float dx = speed * dt;
    if (keys[controls.up])
        y -= (y - dx) >= 0 ? dx : y;
    if (keys[controls.down])
        y += (y + playerh + dx) <= screenh ? dx : screenh - y - playerh;
    if (keys[controls.left])
        x -= (x - dx) >= 0 ? dx : x;
    if (keys[controls.right])
        x += (x + playerw + dx) <= screenw ? dx : screenw - x - playerw;
    
    box.x = x;
    box.y = y;
}