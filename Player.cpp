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

    int mx = 0, my = 0;
    if (keys[controls.up])    my = -1;
    if (keys[controls.down])  my = 1;
    if (keys[controls.left])  mx = -1;
    if (keys[controls.right]) mx = 1;

    if (mx != 0 || my != 0)
        direction = {mx, -my};

    float dx = speed * dt;
    if (mx != 0 && my != 0)
        dx *= 0.7071f;

    if (mx != 0) {
        float nx = x + mx * dx;
        if (nx >= 0 && nx + playerw <= screenw)
            x = nx;
    }
    if (my != 0) {
        float ny = y + my * dx;
        if (ny >= 0 && ny + playerh <= screenh)
            y = ny;
    }

    if (mx == 0 && my == 0) {
        texture = idle_texture;
    } else {
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