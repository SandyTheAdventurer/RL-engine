#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
#include <SDL3_ttf/SDL_ttf.h>
#include <nlohmann/json.hpp>
#include "Constants.h"
#include "Events.h"
#include "Updates.h"
#include "Player.h"
#include "SocketClient.h"
#include "Collision.h"
#include "Input.h"

using json = nlohmann::json;

static SDL_Texture* make_text(SDL_Renderer* r, TTF_Font* f, const char* t, SDL_Color c) {
    SDL_Surface* s = TTF_RenderText_Blended(f, t, SDL_strlen(t), c);
    SDL_Texture* tx = SDL_CreateTextureFromSurface(r, s);
    SDL_DestroySurface(s);
    return tx;
}

int main()
{
    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMEPAD);
    TTF_Init();

    Player human((screenw / 2.0f) - playerw * 2, (screenh - playerh) / 2.0f, playerspeed, "Human");
    Player bot((screenw / 2.0f) + playerw, (screenh - playerh) / 2.0f, playerspeed, "Bot");

    SDL_Window* window = SDL_CreateWindow("Hello SDL3", screenw, screenh, 0);
    SDL_Renderer* renderer = SDL_CreateRenderer(window, nullptr);

    human.load_textures(IMG_LoadTexture(renderer, "assets/1Knight/Idle_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/Walk_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/CastSpell_Shadowless.png"), IMG_LoadTexture(renderer, "assets/bullet.png"));
    bot.load_textures(IMG_LoadTexture(renderer, "assets/1Knight/Idle_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/Walk_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/CastSpell_Shadowless.png"), IMG_LoadTexture(renderer, "assets/bullet.png"));

    SocketClient client;
    client.connect();

    TTF_Font* font = TTF_OpenFont("assets/LiberationSans-Regular.ttf", font_size);
    SDL_Color white = {255, 255, 255, 255};
    SDL_Texture* start_text = make_text(renderer, font, "CLICK TO START", white);
    SDL_Texture* end_text = make_text(renderer, font, "LEFT CLICK TO QUIT, RIGHT CLICK TO RESTART", white);

    float start_w, start_h, end_w, end_h;
    SDL_GetTextureSize(start_text, &start_w, &start_h);
    SDL_GetTextureSize(end_text, &end_w, &end_h);

    SDL_Gamepad* ctrl = nullptr;
    int num_joysticks = 0;
    SDL_JoystickID* joysticks = SDL_GetJoysticks(&num_joysticks);
    for (int i = 0; i < num_joysticks; i++) {
        if (SDL_IsGamepad(joysticks[i])) {
            ctrl = SDL_OpenGamepad(joysticks[i]);
            if (ctrl) break;
        }
    }
    SDL_free(joysticks);

    bool running = true;
    Uint64 previous = SDL_GetPerformanceCounter();
    bool prev_fire_btn = false;

    GameState state = GameState::START;

    while (running)
    {
        FrameInput input = pollEvents();
        if (input.quit) running = false;

        switch(state)
        {
            case GameState::START:
            {
                human.reset((screenw / 2.0f) - playerw * 2, (screenh - playerh) / 2.0f);
                bot.reset((screenw / 2.0f) + playerw, (screenh - playerh) / 2.0f);

                SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
                SDL_RenderClear(renderer);

                SDL_FRect dst = {(screenw - start_w) / 2, (screenh - start_h) / 2, start_w, start_h};
                SDL_RenderTexture(renderer, start_text, nullptr, &dst);

                if(input.mouse_left_clicked) state = GameState::PLAYING;
                break;
            }

            case GameState::PLAYING:
            {
                float dt = deltaTime(previous);

                human.move(dt, getHumanIntent(input));
                PlayerIntent intent = getBotIntent(ctrl, bot.box, prev_fire_btn);
                PlayerIntent rlintent;
                if(client.isConnected() && client.pollIntent(rlintent)) {
                    intent = rlintent;
                }
                bot.move(dt, intent);

                if(client.isConnected()) {
                    json state = {
                    {"x", bot.box.x},
                    {"y", bot.box.y},
                    {"health", bot.health}
                    };
                    client.sendState(state.dump());
                }

                check_players_collision(&human, &bot);
                check_bullet_collision(&human, &bot);

                SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
                SDL_RenderClear(renderer);

                bot.draw(renderer);
                human.draw(renderer);
                if(human.health == 0 || bot.health == 0) state = GameState::END;
                break;
            }

            case GameState::END:
            {
                SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
                SDL_RenderClear(renderer);

                SDL_FRect dst = {(screenw - end_w) / 2, (screenh - end_h) / 2, end_w, end_h};
                SDL_RenderTexture(renderer, end_text, nullptr, &dst);

                if(input.mouse_left_clicked) running = false;
                if(input.mouse_right_clicked) state = GameState::START;
                break;
            }
        }

        SDL_RenderPresent(renderer);
    }

    SDL_DestroyTexture(start_text);
    SDL_DestroyTexture(end_text);
    TTF_CloseFont(font);

    if (ctrl) SDL_CloseGamepad(ctrl);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    TTF_Quit();
    SDL_Quit();

    return 0;
}
