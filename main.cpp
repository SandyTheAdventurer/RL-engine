#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
#include <SDL3_ttf/SDL_ttf.h>
#include <spdlog/spdlog.h>
#include "Constants.h"
#include "Events.h"
#include "Updates.h"
#include "Player.h"
#include "SocketClient.h"
#include "Collision.h"
#include "Input.h"
#include "State.h"

static SDL_Texture* make_text(SDL_Renderer* r, TTF_Font* f, const char* t, SDL_Color c) {
    SDL_Surface* s = TTF_RenderText_Blended(f, t, SDL_strlen(t), c);
    SDL_Texture* tx = SDL_CreateTextureFromSurface(r, s);
    SDL_DestroySurface(s);
    return tx;
}

int main(int argc, char* argv[])
{
    spdlog::info("Game starting");
    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMEPAD);
    TTF_Init();

    Player human((screenw / 2.0f) - playerw * 2, (screenh - playerh) / 2.0f, playerspeed, "Human");
    Player bot((screenw / 2.0f) + playerw, (screenh - playerh) / 2.0f, playerspeed, "Bot");

    SDL_Window* window = SDL_CreateWindow("Hello SDL3", screenw, screenh, 0);
    SDL_Renderer* renderer = SDL_CreateRenderer(window, nullptr);
    spdlog::info("Window and renderer created");
    human.load_textures(IMG_LoadTexture(renderer, "assets/1Knight/Idle_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/Walk_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/CastSpell_Shadowless.png"), IMG_LoadTexture(renderer, "assets/bullet.png"));
    bot.load_textures(IMG_LoadTexture(renderer, "assets/1Knight/Idle_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/Walk_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/CastSpell_Shadowless.png"), IMG_LoadTexture(renderer, "assets/bullet.png"));

    SocketClient client;
    client.connect();
    SocketClient clclient;

    TTF_Font* font = TTF_OpenFont("assets/LiberationSans-Regular.ttf", font_size);
    SDL_Color white = {255, 255, 255, 255};
    SDL_Texture* start_text = make_text(renderer, font, "CLICK TO START", white);
    SDL_Texture* train_text = make_text(renderer, font, "TRAINING HOW TO BEAT YOU...", white);
    SDL_Texture* end_text = make_text(renderer, font, "LEFT CLICK TO QUIT, RIGHT CLICK TO RESTART", white);

    float start_w, start_h, train_w, train_h, end_w, end_h;
    SDL_GetTextureSize(start_text, &start_w, &start_h);
    SDL_GetTextureSize(train_text, &train_w, &train_h);
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
    bool inference = false;

    for (int i = 1; i < argc; i++) {
        if (std::string(argv[i]) == "--inference") {
            inference = true;
        }
    }
    int data_counter = 0;
    int train_counter = 0;
    int max_data = 0;
    int max_train = 100;
    if(!inference) {
        std::array<int, 2> state = client.getTrainState();
        max_data = state[0];
        max_train = state[1];
    }
    spdlog::info("Collecting data for {}", max_data);
    spdlog::info("Training for {}", max_train);
    Uint64 previous = SDL_GetPerformanceCounter();
    bool prev_fire_btn = false;

    GameState state = GameState::START;
    GameState prev_state = GameState::END;
    PlayerIntent last_bot_intent;
    PlayerIntent last_human_intent;
    int frame_counter = 0;
    bool prev_bot_fire = false;
    bool prev_human_fire = false;

    while (running)
    {
        FrameInput input = pollEvents();
        if (input.quit) {
            spdlog::info("Quit requested");
            running = false;
        }

        if (state != prev_state) {
            spdlog::info("State changed: {} -> {}", static_cast<int>(prev_state), static_cast<int>(state));
            prev_state = state;
        }

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

                if(input.mouse_left_clicked) {
                    spdlog::info("Starting game");
                    state = GameState::PLAYING;
                }
                break;
            }

            case GameState::PLAYING:
            {
                SDL_SetRenderVSync(renderer, 1);
                train_counter = 0;
                float dt = deltaTime(previous);

                PlayerIntent human_intent = getHumanIntent(input);
                human.move(dt, human_intent);
                PlayerIntent intent = getBotIntent(ctrl, bot.box, prev_fire_btn);
                if (frame_counter % FRAME_SKIP == 0) {
                    prev_bot_fire = false;
                    PlayerIntent fresh;
                    if(client.isConnected() && client.pollIntent(fresh)) {
                        last_bot_intent = fresh;
                    }
                }
                if(client.isConnected()) {
                    intent = last_bot_intent;
                    bool raw_fire = intent.fire;
                    intent.fire = raw_fire && !prev_bot_fire;
                    prev_bot_fire = raw_fire;
                }
                bot.move(dt, intent);

                check_players_collision(&human, &bot);
                check_bullet_collision(&human, &bot);

                if (frame_counter % FRAME_SKIP == 0) {
                    if(client.isConnected()) {
                        nlohmann::json msg;
                        msg["game_state"] = "PLAYING";
                        msg["role"] = "agent";
                        msg["self"] = State::extract(human, bot);
                        msg["expert_action"] = {
                            {"mx", human_intent.mx},
                            {"my", human_intent.my},
                            {"fire", human_intent.fire},
                            {"aim_x", human_intent.aim_x},
                            {"aim_y", human_intent.aim_y}
                        };
                        client.sendState(msg.dump());
                    }
                }

                SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
                SDL_RenderClear(renderer);

                bot.draw(renderer);
                human.draw(renderer);
                if(human.health == 0 || bot.health == 0) {
                    if(!inference && data_counter < max_data) {
                        data_counter++;
                        spdlog::info("Data collection iteration {}", data_counter);
                        human.reset((screenw / 2.0f) - playerw * 2, (screenh - playerh) / 2.0f);
                        bot.reset((screenw / 2.0f) + playerw, (screenh - playerh) / 2.0f);
                    }
                    else if(!inference && data_counter >= max_data) {
                        spdlog::info("Data collection done");
                        state = GameState::TRAINING;
                    }
                    else {
                        spdlog::info("Game over — human health: {}, bot health: {}", human.health, bot.health);
                        state = GameState::END;
                    }
                }
                break;
            }

            case GameState::TRAINING:
            {
                SDL_SetRenderVSync(renderer, 0);
                data_counter = 0;
                if(!clclient.isConnected()) {
                    clclient.connect();
                }
                float dt = deltaTime(previous);
                if (frame_counter % FRAME_SKIP == 0) {
                    prev_bot_fire = false;
                    prev_human_fire = false;
                    PlayerIntent fresh_human;
                    PlayerIntent fresh_bot;
                    if(client.isConnected() && client.pollIntent(fresh_bot)) {
                        last_bot_intent = fresh_bot;
                    }
                    if(clclient.isConnected() && clclient.pollIntent(fresh_human)) {
                        last_human_intent = fresh_human;
                    }
                }
                {
                    bool raw_fire = last_human_intent.fire;
                    last_human_intent.fire = raw_fire && !prev_human_fire;
                    prev_human_fire = raw_fire;
                }
                {
                    bool raw_fire = last_bot_intent.fire;
                    last_bot_intent.fire = raw_fire && !prev_bot_fire;
                    prev_bot_fire = raw_fire;
                }
                human.move(dt, last_human_intent);
                bot.move(dt, last_bot_intent);

                check_players_collision(&human, &bot);
                check_bullet_collision(&human, &bot);

                if (frame_counter % FRAME_SKIP == 0) {
                    if(client.isConnected()) {
                        nlohmann::json msg;
                        msg["game_state"] = "TRAINING";
                        msg["role"] = "agent";
                        msg["self"] = State::extract(human, bot);
                        client.sendState(msg.dump());
                    }

                    if(clclient.isConnected()) {
                        nlohmann::json msg;
                        msg["game_state"] = "TRAINING";
                        msg["role"] = "clone";
                        msg["self"] = State::extract(bot, human);
                        clclient.sendState(msg.dump());
                    }
                }

                SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
                SDL_RenderClear(renderer);

                SDL_FRect dst = {(screenw - train_w) / 2, (screenh - train_h) / 2, train_w, train_h};
                SDL_RenderTexture(renderer, train_text, nullptr, &dst);

                if(human.health == 0 || bot.health == 0) {
                    train_counter++;
                    human.reset((screenw / 2.0f) - playerw * 2, (screenh - playerh) / 2.0f);
                    bot.reset((screenw / 2.0f) + playerw, (screenh - playerh) / 2.0f);
                    if(train_counter < max_train) {
                        spdlog::info("Training iteration {}", train_counter);
                    }
                    else {
                        spdlog::info("Training done");
                        clclient.disconnect();
                        state = GameState::PLAYING;
                    }
                }

                break;
            }

            case GameState::END:
            {
                SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
                SDL_RenderClear(renderer);

                SDL_FRect dst = {(screenw - end_w) / 2, (screenh - end_h) / 2, end_w, end_h};
                SDL_RenderTexture(renderer, end_text, nullptr, &dst);

                if(input.mouse_left_clicked) {
                    spdlog::info("Exiting game");
                    running = false;
                }
                if(input.mouse_right_clicked) state = GameState::START;
                break;
            }
        }

        frame_counter++;
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
