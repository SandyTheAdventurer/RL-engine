#include "Player.h"
#include "Constants.h"

Player::Player(float x, float y, float speed, std::string name, Controls controls)
    : speed(speed),
    name(name),
    controls(controls)
{
    box = {x, y, playerw, playerh};
    hitbox = {x + playerw / 2 - hitbox_size,  y + playerh / 2 - hitbox_size,
              hitbox_size * 2, hitbox_size * 2};
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
        float nx = box.x + mx * dx;
        if (nx >= 0 && nx + playerw <= screenw)
           box.x = nx;
    }
    if (my != 0) {
        float ny = box.y + my * dx;
        if (ny >= 0 && ny + playerh <= screenh)
            box.y = ny;
    }

    hitbox.x = box.x + playerw / 2 - hitbox_size;
    hitbox.y = box.y + playerh / 2 - hitbox_size;

    texture = (mx == 0 && my == 0) ? idle_texture : walk_texture;
    advanceFrame(dt);
}

void Player::draw(SDL_Renderer* renderer) {
    SDL_FRect src = get_texture_box();
    SDL_RenderTexture(renderer, texture, &src, &box);
}

void Player::advanceFrame(float dt) {
    anim_timer += dt;
    if (anim_timer >= spritechange) {
        anim_timer -= spritechange;
        texture_state = (texture_state + 1) % 15;
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