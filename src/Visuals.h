#pragma once
#include <SDL3/SDL.h>
#include <SDL3_ttf/SDL_ttf.h>
#include "Engine.h"
#include "Player.h"
#include "Constants.h"

class Visuals {
public:
    static void init(Engine& engine, Player& p1, Player& p2);
    static void start_screen(Engine& engine);
    static void training_screen(Engine& engine);
    static void end_screen(Engine& engine);
    static void hud(Engine& engine);
    static void shutdown();

private:
    static TTF_Font* font;
    static SDL_Texture* start_text;
    static SDL_Texture* train_text;
    static SDL_Texture* end_text;
    static float start_w, start_h, train_w, train_h, end_w, end_h;

    static SDL_Texture* make_text(SDL_Renderer* r, TTF_Font* f, const char* t, SDL_Color c);
};
