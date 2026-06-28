#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
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

    human.load_textures(IMG_LoadTexture(renderer, "assests/1Knight/Idle_Shadowless.png"), IMG_LoadTexture(renderer, "assests/1Knight/Walk_Shadowless.png"));
    bot.load_textures(IMG_LoadTexture(renderer, "assests/1Knight/Idle_Shadowless.png"), IMG_LoadTexture(renderer, "assests/1Knight/Walk_Shadowless.png"));
    
    bool running = true;
    float timer = 0;
    Uint64 previous = SDL_GetPerformanceCounter();

    while (running)
    {
        if (pollQuit()) running = false;

        float dt = deltaTime(previous);
        timer += dt;
        if (timer > spritechange) {
            timer = 0;
            human.texture_state = (human.texture_state + 1) % 15;
            bot.texture_state = (bot.texture_state + 1) % 15;
        }
        human.move(dt);
        bot.move(dt);

        SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
        SDL_RenderClear(renderer);

        SDL_FRect human_src = human.get_texture_box();
        SDL_FRect bot_src = bot.get_texture_box();
        SDL_RenderTexture(renderer, bot.texture, &bot_src, &bot.box);
        SDL_RenderTexture(renderer, human.texture, &human_src, &human.box);

        SDL_RenderPresent(renderer);
    }

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();

    return 0;
}
