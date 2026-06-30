#include "Player.h"
#include "State.h"
#include "Constants.h"
#include <nlohmann/json.hpp>

using json = nlohmann::json;

json State::extract(const Player& self, const Player& enemy) {
    float health = self.health;
    float speed = self.speed;
    float enemy_health = enemy.health;
    float x = self.box.x;
    float y = self.box.y;
    float enemy_x = enemy.box.x;
    float enemy_y = enemy.box.y;
    float enemy_speed = enemy.speed;
    std::array<bool, max_bullets / 2> bullets_fired;
    std::array<bool, max_bullets / 2> bullets_reloaded;
    std::array<std::array<float, 2>, max_bullets> bullets_pos;
    std::array<std::array<float, 2>, max_bullets> bullets_vel;
    for(int i = 0; i<max_bullets / 2; i++) {
        bullets_fired[i] = self.bullets[i].isShot;
        bullets_reloaded[i] = self.bullets[i].isLoaded;

        if(bullets_fired[i]) {
            bullets_pos[i] = {self.bullets[i].hitbox.x, self.bullets[i].hitbox.y};
            bullets_vel[i] = self.bullets[i].getVel();
        } else {
            bullets_pos[i] = {-1.0f, -1.0f};
            bullets_vel[i] = {-1.0f, -1.0f};
        }

        if(enemy.bullets[i].isShot) {
            bullets_pos[i + max_bullets / 2] = {enemy.bullets[i].hitbox.x, enemy.bullets[i].hitbox.y};
            bullets_vel[i + max_bullets / 2] = enemy.bullets[i].getVel();
        } else {
            bullets_pos[i + max_bullets / 2] = {-1.0f, -1.0f};
            bullets_vel[i + max_bullets / 2] = {-1.0f, -1.0f};
        }
    }

    json j = {
        {"health", health},
        {"enemy_health", enemy_health},
        {"x", x},
        {"y", y},
        {"enemy_x", enemy_x},
        {"enemy_y", enemy_y},
        {"speed", speed},
        {"enemy_speed", enemy_speed},
        {"bullets_fired", bullets_fired},
        {"bullets_reloaded", bullets_reloaded},
        {"bullets_pos", bullets_pos},
        {"bullets_vel", bullets_vel}
    };
    return j;
}

json State::game_config() {
    json j = {
        {"screen_dim", {screenh, screenw}},
    };
    return j;
}