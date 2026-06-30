#pragma once
#include <nlohmann/json.hpp>
#include <string>
#include <array>
#include "Player.h"

class State {
    public:
        static nlohmann::json extract(const Player& self, const Player& enemy);
        static nlohmann::json game_config();
};