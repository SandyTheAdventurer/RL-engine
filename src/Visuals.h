#pragma once
#include <SDL3/SDL.h>
#include <SDL3_ttf/SDL_ttf.h>
#include "Engine.h"
#include "Player.h"
#include "Constants.h"
#include "Audio.h"

struct Button {
    SDL_FRect rect;
    SDL_Texture* text = nullptr;
    float text_w = 0, text_h = 0;
};

class Visuals {
public:
    static void init(Engine& engine, Player& p1, Player& p2);
    static void hud(Engine& engine);
    static void shutdown();

    static void start_fight_music();
    static void stop_fight_music();

    static MenuResult start_menu(Engine& engine, FrameInput& input);
    static MenuResult end_menu(Engine& engine, FrameInput& input);

private:
    static TTF_Font* font;
    static SDL_Texture* start_text;
    static SDL_Texture* train_text;
    static SDL_Texture* end_text;
    static float start_w, start_h, train_w, train_h, end_w, end_h;

    static Button play_btn;
    static Button quit_btn;
    static Button restart_btn;

    static Audio audio;

    static void draw_button_shape(SDL_Renderer* r, SDL_FRect rect, float mx, float my, const char* text);
    static SDL_Texture* make_text(SDL_Renderer* r, TTF_Font* f, const char* t, SDL_Color c);
    static void make_buttons(SDL_Renderer* r);
    static void draw_button(SDL_Renderer* r, Button& btn, float mx, float my);
    static bool point_in_rect(float px, float py, SDL_FRect rect);
};
