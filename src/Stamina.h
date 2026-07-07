#pragma once
#include "Stats.h"

struct PlayerStats;

struct Stamina {
    float max_stamina = 100.0f;
    float current = 100.0f;
    float regen_rate = 40.0f;
    float regen_delay_timer = 0.0f;

    void init(const PlayerStats& stats);
    void tick(float dt, const PlayerStats& stats);
    bool can_afford(float cost) const;
    void spend(float cost);
    void reset(const PlayerStats& stats);
};
