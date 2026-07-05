#include "Collision.h"
#include "Player.h"
#include "Constants.h"
#include <cstdlib>

bool aabb(const SDL_FRect& a, const SDL_FRect& b) {
    return a.x < b.x + b.w && a.x + a.w > b.x &&
           a.y < b.y + b.h && a.y + a.h > b.y;
}

void check_players_collision(Player* human, Player* bot) {
    if (human->is_dashing || bot->is_dashing) return;
    if (aabb(human->hitbox, bot->hitbox)) {
        float overlap_x = (human->hitbox.w + bot->hitbox.w) / 2.0f - std::abs(human->hitbox.x - bot->hitbox.x);
        float overlap_y = (human->hitbox.h + bot->hitbox.h) / 2.0f - std::abs(human->hitbox.y - bot->hitbox.y);

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

void check_melee_collision(Player* p1, Player* p2) {
    if (p1->is_attacking && !p1->hit_this_swing && !p1->is_dashing && aabb(p1->melee_hitbox, p2->hitbox) && !p2->is_dashing) {
        float mult = p1->combo_stage == 0 ? 1.0f : (p1->combo_stage == 1 ? 1.3f : 1.8f);
        p2->health -= melee_damage * mult;
        p2->hurt_timer = hurt_flash_duration;
        p1->hit_this_swing = true;
    }
    if (p2->is_attacking && !p2->hit_this_swing && !p2->is_dashing && aabb(p2->melee_hitbox, p1->hitbox) && !p1->is_dashing) {
        float mult = p2->combo_stage == 0 ? 1.0f : (p2->combo_stage == 1 ? 1.3f : 1.8f);
        p1->health -= melee_damage * mult;
        p1->hurt_timer = hurt_flash_duration;
        p2->hit_this_swing = true;
    }
}

void check_bullet_collision(Player* human, Player* bot) {
    for(Bullet& b: human->bullets) {
        if(!b.isShot) continue;
        if(human->is_dashing) continue;
        if(bot->is_dashing) continue;
        if(aabb(b.hitbox, bot->hitbox)) {
            bot->health -= rand() % 10 + 1;
            bot->hurt_timer = hurt_flash_duration;
            b.isShot = false;
            b.isLoaded = true;
        }
    }
    for(Bullet& b: bot->bullets) {
        if(!b.isShot) continue;
        if(bot->is_dashing) continue;
        if(human->is_dashing) continue;
        if(aabb(b.hitbox, human->hitbox)) {
            human->health -= rand() % 10 + 1;
            human->hurt_timer = hurt_flash_duration;
            b.isShot = false;
            b.isLoaded = true;
        }
    }
}