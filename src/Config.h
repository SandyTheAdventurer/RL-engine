#pragma once
#include <string>
#include <map>
#include <fstream>
#include <stdexcept>

struct GameConfig {
    int screenw = 1280;
    int screenh = 720;
    float playerspeed = 200.0f;
    int aim_directions = 16;
    float aim_radius = 1000.0f;
    int frame_skip = 4;
    int max_episode_steps = 900;
    float win_bonus = 10.0f;
};

inline std::map<std::string, float> parse_json_flat(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open())
        throw std::runtime_error("Cannot open config file: " + path);

    std::map<std::string, float> cfg;
    std::string content((std::istreambuf_iterator<char>(file)),
                         std::istreambuf_iterator<char>());

    size_t i = 0;
    while (i < content.size()) {
        while (i < content.size() && (content[i] == ',' || content[i] == '\n' ||
               content[i] == '\r' || content[i] == '\t' || content[i] == ' '))
            ++i;
        if (i >= content.size() || content[i] == '}' || content[i] == '{') { ++i; continue; }

        // parse key
        if (content[i] != '"') break;
        ++i;
        size_t key_start = i;
        while (i < content.size() && content[i] != '"') ++i;
        std::string key = content.substr(key_start, i - key_start);
        ++i;

        // skip : whitespace
        while (i < content.size() && (content[i] == ':' || content[i] == ' ' ||
               content[i] == '\t' || content[i] == '\n' || content[i] == '\r'))
            ++i;

        // parse value
        if (content[i] == '"') {
            ++i;
            while (i < content.size() && content[i] != '"') ++i;
            ++i;
        } else {
            size_t val_start = i;
            while (i < content.size() && content[i] != ',' &&
                   content[i] != '}' && content[i] != '\n')
                ++i;
            std::string val_str = content.substr(val_start, i - val_start);
            if (!val_str.empty())
                cfg[key] = std::stof(val_str);
        }
    }
    return cfg;
}

inline GameConfig load_game_config(const std::string& path) {
    GameConfig gc;
    auto m = parse_json_flat(path);
    auto f = [&](const std::string& k, auto& v) {
        auto it = m.find(k);
        if (it != m.end()) v = it->second;
    };
    f("screenw", gc.screenw);
    f("screenh", gc.screenh);
    f("playerspeed", gc.playerspeed);
    f("aim_directions", gc.aim_directions);
    f("aim_radius", gc.aim_radius);
    f("frame_skip", gc.frame_skip);
    f("max_episode_steps", gc.max_episode_steps);
    f("win_bonus", gc.win_bonus);
    return gc;
}
