#pragma once
#include <SDL3/SDL.h>

enum class ParticleType {
    Spark,
    Magic,
    Flare,
    Blood,
    CastCircle
};
struct Particle {
    float x, y;
    float vx, vy;
    float life;
    float max_life;
    float size;
    float angle;
    ParticleType type;
    SDL_Color color;
};
