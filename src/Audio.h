#pragma once
#include <SDL3/SDL.h>
#include <SDL3_mixer/SDL_mixer.h>
#include <vector>
#include <string>
#include <random>

class Audio {
public:
    bool init(float volume);
    void load_from_directory(const std::string& dir);
    void play_random();
    void stop();
    void shutdown();
    bool is_playing() const { return playing; }

private:
    MIX_Mixer* mixer = nullptr;
    MIX_Track* track = nullptr;
    std::vector<MIX_Audio*> musics;
    std::vector<std::string> names;
    int current = -1;
    bool initialized = false;
    bool playing = false;
    std::mt19937 rng{std::random_device{}()};
};
