#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
#include "Constants.h"
#include "Events.h"
#include "Updates.h"
#include "Player.h"
#include "Collision.h"
#include "Input.h"

int main()
{
    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMEPAD);

    Player human((screenw / 2.0f) - playerw * 2, (screenh - playerh) / 2.0f, playerspeed, "Human");
    Player bot((screenw / 2.0f) + playerw, (screenh - playerh) / 2.0f, playerspeed, "Bot");

    SDL_Window* window = SDL_CreateWindow("Hello SDL3", screenw, screenh, 0);
    SDL_Renderer* renderer = SDL_CreateRenderer(window, nullptr);

    human.load_textures(IMG_LoadTexture(renderer, "assets/1Knight/Idle_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/Walk_Shadowless.png"), IMG_LoadTexture(renderer, "assets/bullet.png"));
    bot.load_textures(IMG_LoadTexture(renderer, "assets/1Knight/Idle_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/Walk_Shadowless.png"), IMG_LoadTexture(renderer, "assets/bullet.png"));

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

    while (running)
    {
        FrameInput input = pollEvents();
        if (input.quit) running = false;

        float dt = deltaTime(previous);

        human.move(dt, getHumanIntent(input));
        bot.move(dt, getBotIntent(ctrl, bot.box, prev_fire_btn));

        check_players_collision(&human, &bot);
        check_bullet_collision(&human, &bot);

        SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
        SDL_RenderClear(renderer);

        bot.draw(renderer);
        human.draw(renderer);

        SDL_RenderPresent(renderer);
    }

    if (ctrl) SDL_CloseGamepad(ctrl);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();

    return 0;
}
