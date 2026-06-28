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
    if (keys[controls.up]){
        y -= (y - dx) >= 0 ? dx : y;
        direction = {0, 1};
    }
    if (keys[controls.down]){
        y += (y + playerh + dx) <= screenh ? dx : screenh - y - playerh;
        direction = {0, -1};
    }
    if (keys[controls.left]){
        x -= (x - dx) >= 0 ? dx : x;
        direction = {-1, 0};
    }
    if (keys[controls.right]){
        x += (x + playerw + dx) <= screenw ? dx : screenw - x - playerw;
        direction = {1, 0};
    }
    if (box.x == x && box.y == y) {
        texture = idle_texture;
    }
    else {
        box.x = x;
        box.y = y;
        texture = walk_texture;
    }
}

void Player::load_textures(SDL_Texture* idle, SDL_Texture* walk)
{
    idle_texture = idle;
    walk_texture = walk;
    texture = idle;
}

SDL_FRect Player::get_texture_box() {
    return spritesheet.getSrc(dirIndex.at(direction), texture_state);
}