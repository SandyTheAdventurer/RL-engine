#pragma once
#include <SDL3/SDL.h>
#include "Player.h"
#include "Constants.h"

inline bool aabb(const SDL_FRect& a, const SDL_FRect& b) {
    return a.x < b.x + b.w && a.x + a.w > b.x &&
           a.y < b.y + b.h && a.y + a.h > b.y;
}

inline void check_players_collision(Player* human, Player* bot) {
        if (aabb(human->hitbox, bot->hitbox)) {
            float overlap_x = (human->hitbox.w + bot->hitbox.w) / 2.0f - abs(human->hitbox.x - bot->hitbox.x);
            float overlap_y = (human->hitbox.h + bot->hitbox.h) / 2.0f - abs(human->hitbox.y - bot->hitbox.y);

            float push_x = overlap_x / 2;
            float push_y = overlap_y / 2;

            if (overlap_x < overlap_y) {
                if (human->hitbox.x < bot->hitbox.x) {
                    human->box.x -= push_x;
                    bot->box.x += push_x;
                } else {
                    human->box.x += push_x;
                    bot->box.x -= push_x;
                }
            } else {
                if (human->hitbox.y < bot->hitbox.y) {
                    human->box.y -= push_y;
                    bot->box.y += push_y;
                } else {
                    human->box.y += push_y;
                    bot->box.y -= push_y;
                }
            }
            human->hitbox.x = human->box.x + playerw / 2 - hitbox_size;
            human->hitbox.y = human->box.y + playerh / 2 - hitbox_size;
            bot->hitbox.x = bot->box.x + playerw / 2 - hitbox_size;
            bot->hitbox.y = bot->box.y + playerh / 2 - hitbox_size;
        }
}