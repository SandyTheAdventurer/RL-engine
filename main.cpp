#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
#include "Constants.h"
#include "Events.h"
#include "Updates.h"
#include "Player.h"
#include "Collision.h"

int main()
{
    SDL_Init(SDL_INIT_VIDEO);

    Player human({(screenw / 2.0f) - playerw*2}, (screenh - playerh) / 2.0f, playerspeed, "Human", HumanControls);
    Player bot({(screenw / 2.0f) + playerw}, (screenh - playerh) / 2.0f, playerspeed, "Bot", BotControls);

    SDL_Window* window = SDL_CreateWindow("Hello SDL3", screenw, screenh, 0);
    SDL_Renderer* renderer = SDL_CreateRenderer(window, nullptr);

    human.load_textures(IMG_LoadTexture(renderer, "assets/1Knight/Idle_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/Walk_Shadowless.png"));
    bot.load_textures(IMG_LoadTexture(renderer, "assets/1Knight/Idle_Shadowless.png"), IMG_LoadTexture(renderer, "assets/1Knight/Walk_Shadowless.png"));
    
    bool running = true;
    Uint64 previous = SDL_GetPerformanceCounter();

    while (running)
    {
        if (pollQuit()) running = false;

        float dt = deltaTime(previous);

        human.move(dt); 
        bot.move(dt);

        check_players_collision(&human, &bot);

        SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
        SDL_RenderClear(renderer);

        bot.draw(renderer);
        human.draw(renderer);

        SDL_RenderPresent(renderer);
    }

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();

    return 0;
}
