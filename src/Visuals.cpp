#include "Visuals.h"
#include <SDL3_image/SDL_image.h>

TTF_Font* Visuals::font = nullptr;
SDL_Texture* Visuals::start_text = nullptr;
SDL_Texture* Visuals::train_text = nullptr;
SDL_Texture* Visuals::end_text = nullptr;
float Visuals::start_w = 0, Visuals::start_h = 0;
float Visuals::train_w = 0, Visuals::train_h = 0;
float Visuals::end_w = 0, Visuals::end_h = 0;

SDL_Texture* Visuals::make_text(SDL_Renderer* r, TTF_Font* f, const char* t, SDL_Color c) {
    SDL_Surface* s = TTF_RenderText_Blended(f, t, SDL_strlen(t), c);
    if (!s) return nullptr;
    SDL_Texture* tx = SDL_CreateTextureFromSurface(r, s);
    SDL_DestroySurface(s);
    return tx;
}

void Visuals::init(Engine& engine, Player& p1, Player& p2) {
    SDL_Renderer* r = engine.renderer;
    if (!r) return;

    TTF_Init();
    font = TTF_OpenFont("assets/LiberationSans-Regular.ttf", font_size);
    if (!font) return;

    SDL_Color white = {255, 255, 255, 255};
    start_text = make_text(r, font, "CLICK TO START", white);
    train_text = make_text(r, font, "TRAINING HOW TO BEAT YOU...", white);
    end_text = make_text(r, font, "LEFT CLICK TO QUIT, RIGHT CLICK TO RESTART", white);

    if (start_text) SDL_GetTextureSize(start_text, &start_w, &start_h);
    if (train_text) SDL_GetTextureSize(train_text, &train_w, &train_h);
    if (end_text)   SDL_GetTextureSize(end_text, &end_w, &end_h);


}

void Visuals::start_screen(Engine& engine) {
    SDL_Renderer* r = engine.renderer;
    if (!r) return;
    SDL_SetRenderDrawColor(r, 0, 0, 0, 255);
    SDL_RenderClear(r);
    if (start_text) {
        SDL_FRect dst = {(screenw - start_w) / 2, (screenh - start_h) / 2, start_w, start_h};
        SDL_RenderTexture(r, start_text, nullptr, &dst);
    }
    SDL_RenderPresent(r);
}

void Visuals::training_screen(Engine& engine) {
    SDL_Renderer* r = engine.renderer;
    if (!r) return;
    SDL_SetRenderDrawColor(r, 0, 0, 0, 255);
    SDL_RenderClear(r);
    if (train_text) {
        SDL_FRect dst = {(screenw - train_w) / 2, (screenh - train_h) / 2, train_w, train_h};
        SDL_RenderTexture(r, train_text, nullptr, &dst);
    }
    SDL_RenderPresent(r);
}

void Visuals::end_screen(Engine& engine) {
    SDL_Renderer* r = engine.renderer;
    if (!r) return;
    SDL_SetRenderDrawColor(r, 0, 0, 0, 255);
    SDL_RenderClear(r);
    if (end_text) {
        SDL_FRect dst = {(screenw - end_w) / 2, (screenh - end_h) / 2, end_w, end_h};
        SDL_RenderTexture(r, end_text, nullptr, &dst);
    }
    SDL_RenderPresent(r);
}

void Visuals::hud(Engine&) {}

void Visuals::shutdown() {
    SDL_DestroyTexture(start_text);
    SDL_DestroyTexture(train_text);
    SDL_DestroyTexture(end_text);
    start_text = train_text = end_text = nullptr;
    TTF_CloseFont(font);
    font = nullptr;
    TTF_Quit();
}
