#include "Economy.h"
#include <algorithm>
#include <cmath>

bool EngagementTracker::is_engaged() const {
    if (time_since_damage <= damage_window)
        return true;
    if (time_since_perfect_dodge <= perfect_dodge_window)
        return true;
    return false;
}

void EngagementTracker::on_damage_dealt() {
    time_since_damage = 0.0f;
}

void EngagementTracker::update(float dt, float distance) {
    time_since_damage += dt;
    time_since_perfect_dodge += dt;

    if (distance <= distance_threshold)
        return;

    if (!is_engaged())
        teff += dt;
}

void EngagementTracker::reset() {
    teff = 0.0f;
    time_since_damage = 999.0f;
    time_since_perfect_dodge = 999.0f;
}

bool DroppedDimes::can_collect(float px, float py) const {
    if (collected) return false;
    float dx = px - x;
    float dy = py - y;
    return std::sqrt(dx * dx + dy * dy) <= collect_radius;
}

float DroppedDimes::current_amount(float lambda) const {
    return Economy::apply_decay(amount, time_since_drop, decay_start_time, lambda);
}

float Economy::calculate_payout(float teff, float base, float par_time,
                                 float lambda, float min_multiplier) {
    float excess = std::max(0.0f, teff - par_time);
    float multiplier = 1.0f - lambda * excess;
    multiplier = std::max(min_multiplier, multiplier);
    return base * multiplier;
}

float Economy::calculate_pity_dimes(float damage_dealt, int perfect_dodges,
                                     int parries, float alpha, float beta,
                                     float gamma) {
    return alpha * damage_dealt + beta * perfect_dodges + gamma * parries;
}

DroppedDimes Economy::create_drop(float x, float y, float current_dimes,
                                   float drop_fraction) {
    DroppedDimes drop;
    drop.x = x;
    drop.y = y;
    drop.amount = current_dimes * drop_fraction;
    drop.time_since_drop = 0.0f;
    return drop;
}

float Economy::apply_decay(float initial_amount, float elapsed,
                            float decay_delay, float lambda) {
    if (elapsed <= decay_delay)
        return initial_amount;
    float decay_time = elapsed - decay_delay;
    float decayed = initial_amount * (1.0f - lambda * decay_time);
    return std::max(0.0f, decayed);
}

float UpgradeCosts::stat_cost(int current_level) {
    float levels_above_base = std::max(0.0f, current_level - default_stat_value);
    return upgrade_base_stat_cost + upgrade_stat_growth * levels_above_base * upgrade_base_stat_cost;
}

float UpgradeCosts::weapon_cost(int current_level) {
    return upgrade_base_weapon_cost * std::pow(upgrade_weapon_growth, current_level);
}

float UpgradeCosts::armor_cost(int current_level) {
    return upgrade_base_armor_cost * std::pow(upgrade_armor_growth, current_level);
}


