#include <SDL3/SDL.h>
#include "Constants.h"
#include "Events.h"
#include "Updates.h"
#include "Player.h"
int main()
{
    SDL_Init(SDL_INIT_VIDEO);

    Player human({(screenw / 2.0f) - playerw*2}, (screenh - playerh) / 2.0f, playerspeed, "Human", HumanControls);
    Player bot({(screenw / 2.0f) + playerw}, (screenh - playerh) / 2.0f, playerspeed, "Bot", BotControls);

    SDL_Window* window = SDL_CreateWindow("Hello SDL3", screenw, screenh, 0);
    SDL_Renderer* renderer = SDL_CreateRenderer(window, nullptr);

    bool running = true;
    Uint64 previous = SDL_GetPerformanceCounter();

    while (running)
    {
        if (pollQuit()) running = false;

        float dt = deltaTime(previous);
        human.move(dt);
        bot.move(dt);

        SDL_SetRenderDrawColor(renderer, 20, 20, 30, 255);
        SDL_RenderClear(renderer);

        SDL_SetRenderDrawColor(renderer, 255, 0, 0, 255);
        SDL_RenderFillRect(renderer, &human.box);

        SDL_SetRenderDrawColor(renderer, 0, 0, 255, 255);
        SDL_RenderFillRect(renderer, &bot.box);

        SDL_RenderPresent(renderer);
    }

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();

    return 0;
}
