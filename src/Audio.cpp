#include "Audio.h"
#include <algorithm>
#include <filesystem>
#include <cctype>

bool Audio::init(float volume) {
    if (initialized) return true;
    if (!MIX_Init()) {
        SDL_Log("Audio: MIX_Init failed: %s", SDL_GetError());
        return false;
    }
    mixer = MIX_CreateMixerDevice(SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, nullptr);
    if (!mixer) {
        SDL_Log("Audio: MIX_CreateMixerDevice failed: %s", SDL_GetError());
        return false;
    }
    track = MIX_CreateTrack(mixer);
    if (!track) {
        SDL_Log("Audio: MIX_CreateTrack failed: %s", SDL_GetError());
        MIX_DestroyMixer(mixer);
        mixer = nullptr;
        return false;
    }
    MIX_SetTrackGain(track, volume);
    MIX_SetTrackLoops(track, -1);
    initialized = true;
    SDL_Log("Audio: initialized (volume=%.2f)", volume);
    return true;
}

void Audio::load_from_directory(const std::string& dir) {
    if (!initialized) return;
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(dir, ec)) {
        SDL_Log("Audio: music directory not found: %s", dir.c_str());
        return;
    }
    int skipped = 0;
    for (const auto& entry : fs::directory_iterator(dir, ec)) {
        if (!entry.is_regular_file(ec)) continue;
        std::string path = entry.path().string();
        std::string ext = entry.path().extension().string();
        std::transform(ext.begin(), ext.end(), ext.begin(),
                       [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        if (ext != ".mp3" && ext != ".ogg" && ext != ".wav") continue;
        MIX_Audio* a = MIX_LoadAudio(mixer, path.c_str(), true);
        if (a) {
            musics.push_back(a);
            names.push_back(entry.path().filename().string());
        } else {
            SDL_Log("Audio: failed to load %s: %s", path.c_str(), SDL_GetError());
            ++skipped;
        }
    }
    SDL_Log("Audio: loaded %d track(s) from %s (%d skipped)",
            static_cast<int>(musics.size()), dir.c_str(), skipped);
}

void Audio::play_random() {
    if (!initialized || !track || musics.empty()) {
        SDL_Log("Audio: play_random ignored (initialized=%d, tracks=%d)",
                initialized, static_cast<int>(musics.size()));
        return;
    }
    int idx = current;
    if (musics.size() > 1) {
        std::uniform_int_distribution<int> dist(0, static_cast<int>(musics.size()) - 1);
        while ((idx = dist(rng)) == current) {}
    } else {
        idx = 0;
    }
    current = idx;
    MIX_SetTrackAudio(track, musics[idx]);
    MIX_PlayTrack(track, 0);
    playing = true;
    SDL_Log("Audio: playing track %d/%d: %s", idx, static_cast<int>(musics.size()),
            names[idx].c_str());
}

void Audio::stop() {
    if (track) MIX_StopTrack(track, 0);
    playing = false;
    SDL_Log("Audio: stopped");
    current = -1;
}

void Audio::shutdown() {
    stop();
    if (mixer) {
        SDL_Log("Audio: shutting down, freeing %d track(s)", static_cast<int>(musics.size()));
        for (auto* a : musics) MIX_DestroyAudio(a);
        musics.clear();
        MIX_DestroyMixer(mixer);
        mixer = nullptr;
        track = nullptr;
    }
    if (initialized) {
        MIX_Quit();
        initialized = false;
    }
}
