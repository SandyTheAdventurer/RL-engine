#pragma once

#include <SDL3/SDL.h>

class Player;
class Engine;

bool aabb(const SDL_FRect& a, const SDL_FRect& b);
void check_players_collision(Player* human, Player* bot);
void check_spell_collision(Player* caster, Player* target, Engine* engine);
void check_melee_collision(Player* p1, Player* p2, Engine* engine);
