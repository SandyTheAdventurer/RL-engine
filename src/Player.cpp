#include "Player.h"
#include "Constants.h"

Player::Player(float x, float y, float speed, std::string name)
    : speed(speed),
    name(name)
{
    box = {x, y, playerw, playerh};
    hitbox = {x + playerw / 2 - hitbox_size,  y + playerh / 2 - hitbox_size,
              hitbox_size * 2, hitbox_size * 2};
}

void Player::move(float dt, PlayerIntent intent) {
    float vx = intent.mx * speed;
    float vy = intent.my * speed;

    if (intent.mx != 0 || intent.my != 0)
        direction = {intent.mx, -intent.my};

    if (intent.mx != 0 && intent.my != 0){
        vx *= 0.7071f;
        vy *= 0.7071f;}

    if (intent.mx != 0) {
        float nx = box.x + vx * dt;
        if (nx >= 0 && nx + playerw <= screenw)
           box.x = nx;
    }
    if (intent.my != 0) {
        float ny = box.y + vy * dt;
        if (ny >= 0 && ny + playerh <= screenh)
            box.y = ny;
    }

    hitbox.x = box.x + playerw / 2 - hitbox_size;
    hitbox.y = box.y + playerh / 2 - hitbox_size;

    texture = (intent.mx == 0 && intent.my == 0) ? idle_texture : walk_texture;

    if (intent.fire) {
        for(Bullet& b: bullets) {
            if(b.isLoaded) {
                b.fire(box.x + playerw / 2, box.y + playerh / 2, intent.aim_x, intent.aim_y);
                break;
            }
        }
    }

    for(Bullet& b: bullets) {b.move(dt);}
    advanceFrame(dt);
}

void Player::draw(SDL_Renderer* renderer) {
    SDL_FRect src = get_texture_box();
    SDL_RenderTexture(renderer, texture, &src, &box);

    for(Bullet& b: bullets) {b.draw(renderer);}
}

void Player::advanceFrame(float dt) {
    anim_timer += dt;
    if (anim_timer >= spritechange) {
        anim_timer -= spritechange;
        texture_state = (texture_state + 1) % 15;
    }
}

void Player::load_textures(SDL_Texture* idle, SDL_Texture* walk, SDL_Texture* bullet)
{
    idle_texture = idle;
    walk_texture = walk;
    texture = idle;
    for(Bullet& b: bullets){b.load_textures(bullet);}
}

SDL_FRect Player::get_texture_box() {
    return spritesheet.getSrc(dirIndex.at(direction), texture_state);
}