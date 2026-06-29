#include "Bullet.h"
#include <math.h>
#include <SDL3/SDL.h>
#include <Constants.h>

void Bullet::fire(float x, float y, float tx, float ty) {
    hitbox = {x - bulletw / 2.0f, y - bulleth / 2.0f, bulletw, bulleth};
    float dx = tx - x;
    float dy = ty - y;
    float dist = std::sqrt(dx*dx + dy*dy);
    vx = dx / dist * bullet_speed;
    vy = dy / dist * bullet_speed;
    angle = std::atan2(dy, dx) * 180 / M_PI;
    isLoaded = false;
    isShot = true;
}

void Bullet::move(float dt) {
    if (!isShot)
        return;
    hitbox.x += vx * dt;
    hitbox.y += vy * dt;
    if (hitbox.x < -bulletw || hitbox.x > screenw + bulletw ||
        hitbox.y < -bulleth || hitbox.y > screenh + bulleth) {
        isShot = false;
        isLoaded = true;
    }
}

void Bullet::draw(SDL_Renderer* renderer) {
    if (!isShot)
        return;
    SDL_FRect src = {0, 0, 32, 32};
    SDL_RenderTextureRotated(renderer, texture, &src, &hitbox, angle, NULL, SDL_FLIP_NONE);
}

void Bullet::load_textures(SDL_Texture* texture) {
    this->texture = texture;
}