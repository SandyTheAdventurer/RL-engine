#include "Stamina.h"
#include "Constants.h"
#include <algorithm>

void Stamina::init(const PlayerStats& stats) {
    max_stamina = calc_max_stamina(stats);
    current = max_stamina;
    regen_rate = calc_stamina_regen(stats);
    regen_delay_timer = 0.0f;
}

void Stamina::tick(float dt, const PlayerStats& stats) {
    if (regen_delay_timer > 0.0f) {
        regen_delay_timer = std::max(0.0f, regen_delay_timer - dt);
        return;
    }
    current = std::min(max_stamina, current + regen_rate * dt);
}

void Stamina::spend(float cost) {
    current = std::max(0.0f, current - cost);
    regen_delay_timer = stamina_regen_delay;
}

bool Stamina::can_afford(float cost) const {
    return current >= cost;
}

void Stamina::reset(const PlayerStats& stats) {
    max_stamina = calc_max_stamina(stats);
    current = max_stamina;
    regen_rate = calc_stamina_regen(stats);
    regen_delay_timer = 0.0f;
}
