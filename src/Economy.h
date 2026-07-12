#pragma once
#include "Constants.h"

struct EngagementTracker {
    float distance_threshold = economy_distance_threshold;
    float damage_window = economy_damage_window;
    float perfect_dodge_window = economy_perfect_dodge_window;

    float teff = 0.0f;
    float time_since_damage = 999.0f;
    float time_since_perfect_dodge = 999.0f;

    bool is_engaged() const;

    void update(float dt, float distance);

    void on_damage_dealt();

    void reset();
};

struct DroppedDimes {
    float x = 0.0f, y = 0.0f;
    float amount = 0.0f;
    float time_since_drop = 0.0f;
    float decay_start_time = economy_decay_start_time;
    float collect_radius = economy_collect_radius;
    bool collected = false;

    bool can_collect(float px, float py) const;
    float current_amount(float lambda = economy_lambda) const;
};

struct Economy {
    static float calculate_payout(float teff, float base = economy_base_payout,
                                   float par_time = economy_par_time,
                                   float lambda = economy_lambda,
                                   float min_multiplier = economy_min_multiplier);

    static float calculate_pity_dimes(float damage_dealt, int perfect_dodges,
                                       int parries,
                                       float alpha = economy_pity_alpha,
                                       float beta = economy_pity_beta,
                                       float gamma = economy_pity_gamma);

    static DroppedDimes create_drop(float x, float y, float current_dimes,
                                     float drop_fraction = economy_drop_fraction);

    static float apply_decay(float initial_amount, float elapsed,
                              float decay_delay, float lambda);
};

struct UpgradeCosts {
    static float stat_cost(int current_level);
    static float weapon_cost(int current_level);
    static float armor_cost(int current_level);
};


