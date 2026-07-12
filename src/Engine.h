#pragma once
#include <SDL3/SDL.h>
#include <array>
#include "Constants.h"
#include "Player.h"
#include "Economy.h"
#include "Particle.h"
#include <vector>

struct PendingVfx {
    float x, y; 
    int count; 
    ParticleType type; 
    SDL_Color color; 
    float angle = -1.0f;
};

class Engine {
public:
    Engine(bool vsync, bool render, Player& p1, Player& p2, int screenw, int screenh);
    ~Engine();

    void step(PlayerIntent& pi1, PlayerIntent& pi2, float dt);
    void render();
    void present();
    std::array<float, obs_dim> observe(const Player& self, const Player& enemy);
    std::array<float, qm_obs_dim> observe_qm(const Player& p, float match_outcome,
                                               float damage_dealt, float damage_taken) const;
    void reset(float p1_x = -1, float p1_y = -1, float p2_x = -1, float p2_y = -1);
    void close();

    bool is_done() const { return done; }
    bool is_death_done() const;
    Player& player1() { return p1; }
    Player& player2() { return p2; }
    float get_teff() const { return engagement.teff; }
    void on_damage_dealt();
    DroppedDimes& get_drop() { return dropped_dimes; }
    bool try_collect_drop(float px, float py);
    void handle_level_up(LevelUpIntent& intent);
    SDL_Renderer* renderer = nullptr;
    float hit_stop_timer = 0.0f;
    EngagementTracker engagement;
    DroppedDimes dropped_dimes;

    void reload_weapon_texture(Player& p);
    void spawn_particles(float cx, float cy, int count, ParticleType type, SDL_Color color, float fixed_angle = -1.0f);
    void push_vfx(float x, float y, int count, ParticleType type, SDL_Color color, float angle = -1.0f);

    std::vector<Particle> particles;
    std::vector<PendingVfx> pending_vfx;
    float visual_dt = 0.0f;
    SDL_Texture* tex_particles[6] = {}; // 0: Spark, 1: Magic, 2: Flare, 3: Blood

private:
    SDL_Window* window = nullptr;
    Player& p1;
    Player& p2;
    int screenw, screenh;
    bool vsync;
    bool is_render;
    bool done = false;

    SDL_Texture* tex_textures[static_cast<int>(AnimationState::Count)] = {};
    SDL_Texture* tex_weapons[weapon_count] = {};
};
