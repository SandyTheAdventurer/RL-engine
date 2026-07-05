#pragma once

#include <SDL3/SDL.h>

class Player;

bool aabb(const SDL_FRect& a, const SDL_FRect& b);
void check_players_collision(Player* human, Player* bot);
void check_bullet_collision(Player* human, Player* bot);
void check_melee_collision(Player* p1, Player* p2);