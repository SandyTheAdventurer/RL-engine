#include "Engine.h"
#include "Collision.h"
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <SDL3_image/SDL_image.h>
#include <string>
#include <cstdio>
#include <stdexcept>

static constexpr int animation_count = static_cast<int>(AnimationState::Count);

Engine::Engine(bool vsync, bool render, Player& p1, Player& p2, int screenw, int screenh)
    : p1(p1), p2(p2), screenw(screenw), screenh(screenh), vsync(vsync), is_render(render)
{
    std::srand(static_cast<unsigned>(std::time(nullptr)));
    if (is_render) {
        if (!SDL_Init(SDL_INIT_VIDEO)) {
            throw std::runtime_error("Failed to initialize SDL video");
        }
        window = SDL_CreateWindow("RL Engine", screenw, screenh, 0);
        if (!window) {
            SDL_Quit();
            throw std::runtime_error("Failed to create window");
        }
        renderer = SDL_CreateRenderer(window, nullptr);
        if (!renderer) {
            SDL_DestroyWindow(window);
            window = nullptr;
            SDL_Quit();
            throw std::runtime_error("Failed to create renderer");
        }
        SDL_SetRenderVSync(renderer, vsync ? 1 : 0);

        for (int i = 0; i < animation_count; ++i) {
            std::string path = std::string(asset_dir) + "/" + animation_suffixes[i] + "/" + animation_suffixes[i] + ".png";
            tex_textures[i] = IMG_LoadTexture(renderer, path.c_str());
            if (!tex_textures[i]) {
                fprintf(stderr, "ERROR: Failed to load texture %s: %s\n", path.c_str(), SDL_GetError());
            } else {
                float tw, th;
                SDL_GetTextureSize(tex_textures[i], &tw, &th);
                fprintf(stderr, "OK: Loaded %s (%.0fx%.0f)\n", path.c_str(), tw, th);
            }
        }

        for (int i = 0; i < weapon_count; ++i) {
            const WeaponShopInfo& info = get_weapon_shop_info(static_cast<WeaponType>(i));
            std::string path = std::string(asset_dir) + "/weapons/" + info.tex_file;
            tex_weapons[i] = IMG_LoadTexture(renderer, path.c_str());
        }

        for (int i = 0; i < animation_count; ++i) {
            p1.load_texture(static_cast<AnimationState>(i), tex_textures[i]);
            p2.load_texture(static_cast<AnimationState>(i), tex_textures[i]);
        }
        p1.load_weapon_texture(tex_weapons[static_cast<int>(p1.equipment.weapon)]);
        p2.load_weapon_texture(tex_weapons[static_cast<int>(p2.equipment.weapon)]);

        tex_particles[static_cast<int>(ParticleType::Spark)] = IMG_LoadTexture(renderer, (std::string(asset_dir) + "/vfx/brackeys_vfx_bundle/particles/alpha/spark_02_a.png").c_str());
        tex_particles[static_cast<int>(ParticleType::Magic)] = IMG_LoadTexture(renderer, (std::string(asset_dir) + "/vfx/brackeys_vfx_bundle/particles/alpha/magic_02_a.png").c_str());
        tex_particles[static_cast<int>(ParticleType::Flare)] = IMG_LoadTexture(renderer, (std::string(asset_dir) + "/vfx/brackeys_vfx_bundle/particles/alpha/flare_01_a.png").c_str());
        tex_particles[static_cast<int>(ParticleType::Blood)] = IMG_LoadTexture(renderer, (std::string(asset_dir) + "/vfx/brackeys_vfx_bundle/particles/alpha/spark_01_a.png").c_str());
        tex_particles[static_cast<int>(ParticleType::CastCircle)] = IMG_LoadTexture(renderer, (std::string(asset_dir) + "/vfx/brackeys_vfx_bundle/particles/alpha/magic_02_a.png").c_str());
    }
}

Engine::~Engine() {
    close();
}

void Engine::push_vfx(float x, float y, int count, ParticleType type, SDL_Color color, float angle) {
    if (!is_render) return;
    pending_vfx.push_back({x, y, count, type, color, angle});
}

void Engine::spawn_particles(float cx, float cy, int count, ParticleType type, SDL_Color color, float fixed_angle) {
    if (!is_render) return;
    for (int i = 0; i < count; ++i) {
        Particle p;
        p.x = cx; p.y = cy;
        p.type = type;
        p.color = color;
        p.life = 0.2f + (rand() % 100) / 200.0f;
        p.max_life = p.life;
        if (type == ParticleType::Blood) {
            p.size = 8.0f + (rand() % 8);
        } else if (type == ParticleType::Spark) {
            p.size = 10.0f + (rand() % 10);
        } else {
            p.size = 20.0f + (rand() % 20);
        }
        float angle = (rand() % 360) * M_PI / 180.0f;
        float speed = 50.0f + (rand() % 150);
        if (type == ParticleType::Flare || type == ParticleType::CastCircle) {
            p.vx = 0; p.vy = 0;
            p.life = (type == ParticleType::CastCircle) ? 0.6f : 0.15f;
            p.max_life = p.life;
            p.size = (type == ParticleType::CastCircle) ? 160.0f : 250.0f;
            p.angle = (fixed_angle >= 0.0f) ? fixed_angle * 180.0f / M_PI : 0.0f;
        } else {
            p.vx = std::cos(angle) * speed;
            p.vy = std::sin(angle) * speed;
            p.angle = static_cast<float>(rand() % 360);
        }
        particles.push_back(p);
    }
}

void Engine::reset(float p1_x, float p1_y, float p2_x, float p2_y) {
    if (p1_x < 0) p1_x = (screenw / 2.0f) - playerw * 2;
    if (p1_y < 0) p1_y = (screenh - playerh) / 2.0f;
    if (p2_x < 0) p2_x = (screenw / 2.0f) + playerw;
    if (p2_y < 0) p2_y = (screenh - playerh) / 2.0f;
    p1.reset(p1_x, p1_y);
    p2.reset(p2_x, p2_y);
    done = false;
}

bool Engine::is_death_done() const {
    auto finished = [](const Player& p) { return !p.dead || p.death_timer <= 0.0f; };
    return finished(p1) && finished(p2);
}

void Engine::step(PlayerIntent& pi1, PlayerIntent& pi2, float dt) {
    if (hit_stop_timer > 0.0f) {
        hit_stop_timer -= dt;
        return;
    }

    const bool rendering = (renderer != nullptr);

    // Start the death animation once a player dies (only while rendering).
    if (rendering) {
        if (p1.health <= 0.0f && !p1.dead) { p1.dead = true; p1.death_timer = death_duration; }
        if (p2.health <= 0.0f && !p2.dead) { p2.dead = true; p2.death_timer = death_duration; }
    }

    // While a death animation is playing, feed neutral inputs so it plays out cleanly.
    PlayerIntent neutral;
    bool death_playing = rendering && ((p1.dead && p1.death_timer > 0.0f) || (p2.dead && p2.death_timer > 0.0f));
    PlayerIntent& a1 = death_playing ? neutral : pi1;
    PlayerIntent& a2 = death_playing ? neutral : pi2;

    p1.move(dt, a1);
    p2.move(dt, a2);

    bool hit_before = p1.hit_this_swing || p2.hit_this_swing;
    float p1_health_before = p1.health;
    float p2_health_before = p2.health;

    check_melee_collision(&p1, &p2, this);
    check_spell_collision(&p1, &p2, this);
    check_spell_collision(&p2, &p1, this);
    check_players_collision(&p1, &p2);

    bool hit_after = p1.hit_this_swing || p2.hit_this_swing;
    if (hit_after && !hit_before) {
        hit_stop_timer = 0.05f;
    }

    if (p1.health < p1_health_before || p2.health < p2_health_before)
        engagement.on_damage_dealt();

    float dist = std::abs(p1.box.x - p2.box.x) + std::abs(p1.box.y - p2.box.y);
    engagement.update(dt, dist);

    if (rendering) {
        visual_dt += dt;
    }

    // Advance death-animation timers (single source of truth).
    if (p1.dead && p1.death_timer > 0.0f) p1.death_timer -= dt;
    if (p2.dead && p2.death_timer > 0.0f) p2.death_timer -= dt;

    // Mark the match done: only after the death animation finishes (when rendering);
    // headless, mark done immediately when a player's health hits zero.
    if (rendering) {
        done = (p1.dead || p2.dead) && is_death_done();
    } else {
        done = (p1.health <= 0.0f || p2.health <= 0.0f);
    }

    if (!dropped_dimes.collected && rendering) {
        dropped_dimes.time_since_drop += dt;
    }
}

void Engine::render() {
    if (!renderer) return;

    auto process_cast_vfx = [this](Player& p) {
        if (p.trigger_cast_vfx) {
            p.trigger_cast_vfx = false;
            float cx = p.box.x + playerw / 2.0f;
            float cy = p.box.y + playerh / 2.0f;
            spawn_particles(cx, cy + 30.0f, 1, ParticleType::CastCircle, {150, 150, 255, 255}, 0.0f);
        }
    };
    process_cast_vfx(p1);
    process_cast_vfx(p2);

    for (auto& v : pending_vfx) {
        spawn_particles(v.x, v.y, v.count, v.type, v.color, v.angle);
    }
    pending_vfx.clear();

    for (auto it = particles.begin(); it != particles.end();) {
        it->x += it->vx * visual_dt;
        it->y += it->vy * visual_dt;
        it->life -= visual_dt;
        if (it->life <= 0) {
            it = particles.erase(it);
        } else {
            ++it;
        }
    }
    visual_dt = 0.0f;

    SDL_SetRenderDrawColor(renderer, 30, 30, 40, 255);
    SDL_RenderClear(renderer);
    p1.draw(renderer);
    p2.draw(renderer);

    for (const auto& p : particles) {
        SDL_Texture* tex = tex_particles[static_cast<int>(p.type)];
        if (tex) {
            float alpha = (p.life / p.max_life) * 255.0f;
            SDL_SetTextureBlendMode(tex, SDL_BLENDMODE_BLEND);
            SDL_SetTextureColorMod(tex, p.color.r, p.color.g, p.color.b);
            SDL_SetTextureAlphaMod(tex, static_cast<Uint8>(alpha));
            
            SDL_FRect dst = {p.x - p.size / 2.0f, p.y - p.size / 2.0f, p.size, p.size};
            SDL_RenderTextureRotated(renderer, tex, nullptr, &dst, p.angle, nullptr, SDL_FLIP_NONE);
        }
    }
}

static constexpr float proj_speed = 500.0f;
static constexpr int max_proj_obs = 6;

std::array<float, obs_dim> Engine::observe(const Player& self, const Player& enemy) {
    std::array<float, obs_dim> obs{};
    size_t i = 0;

    float self_cx = self.box.x + playerw / 2.0f;
    float self_cy = self.box.y + playerh / 2.0f;
    float enemy_cx = enemy.box.x + playerw / 2.0f;
    float enemy_cy = enemy.box.y + playerh / 2.0f;

    obs[i++] = self.health / self.max_hp;
    obs[i++] = self.mana / self.max_mana;
    obs[i++] = self.stun_timer > 0.0f ? 1.0f : 0.0f;
    obs[i++] = self.is_dashing ? 1.0f : 0.0f;
    obs[i++] = self_cx / screenw;
    obs[i++] = self_cy / screenh;
    obs[i++] = self.vx / playerspeed;
    obs[i++] = self.vy / playerspeed;

    obs[i++] = enemy.health / enemy.max_hp;
    obs[i++] = (enemy_cx - self_cx) / screenw;
    obs[i++] = (enemy_cy - self_cy) / screenh;
    obs[i++] = enemy.vx / playerspeed;
    obs[i++] = enemy.vy / playerspeed;

    constexpr float sentinel = 0.0f;

    for (int j = 0; j < max_proj_obs; j++) {
        const SpellProjectile& p = self.projectiles[j];
        if (p.active && p.speed > 0.0f) {
            float bx = p.hitbox.x + p.hitbox.w / 2.0f;
            float by = p.hitbox.y + p.hitbox.h / 2.0f;
            obs[i++] = 1.0f;
            obs[i++] = (bx - self_cx) / screenw;
            obs[i++] = (by - self_cy) / screenh;
            obs[i++] = p.vx / proj_speed;
            obs[i++] = p.vy / proj_speed;
        } else {
            obs[i++] = 0.0f;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
        }
    }
    for (int j = 0; j < max_proj_obs; j++) {
        const SpellProjectile& p = enemy.projectiles[j];
        if (p.active && p.speed > 0.0f) {
            float bx = p.hitbox.x + p.hitbox.w / 2.0f;
            float by = p.hitbox.y + p.hitbox.h / 2.0f;
            obs[i++] = 1.0f;
            obs[i++] = (bx - self_cx) / screenw;
            obs[i++] = (by - self_cy) / screenh;
            obs[i++] = p.vx / proj_speed;
            obs[i++] = p.vy / proj_speed;
        } else {
            obs[i++] = 0.0f;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
            obs[i++] = sentinel;
        }
    }

    float dx = enemy_cx - self_cx;
    float dy = enemy_cy - self_cy;
    obs[i++] = std::sqrt(dx * dx + dy * dy) / max_dist;

    obs[i++] = self.is_attacking ? 1.0f : 0.0f;
    obs[i++] = static_cast<float>(self.combo_stage) / max_combo_stage;
    
    obs[i++] = enemy.is_attacking ? 1.0f : 0.0f;
    obs[i++] = static_cast<float>(enemy.combo_stage) / max_combo_stage;
    obs[i++] = enemy.is_dashing ? 1.0f : 0.0f;
    obs[i++] = enemy.stun_timer > 0.0f ? 1.0f : 0.0f;
    obs[i++] = static_cast<float>(static_cast<int>(enemy.equipment.weapon)) / weapon_count;

    obs[i++] = self.stats.strength / max_stat_value;
    obs[i++] = self.stats.vitality / max_stat_value;
    obs[i++] = self.stats.agility / max_stat_value;
    obs[i++] = self.stats.reasoning / max_stat_value;
    obs[i++] = self.stats.endurance / max_stat_value;
    obs[i++] = self.stamina.current / self.stamina.max_stamina;
    obs[i++] = self.equip_load_ratio;

    return obs;
}

std::array<float, qm_obs_dim> Engine::observe_qm(const Player& p, float match_outcome,
                                                   float damage_dealt, float damage_taken) const {
    std::array<float, qm_obs_dim> obs{};
    size_t i = 0;

    obs[i++] = p.stats.strength / max_stat_value;
    obs[i++] = p.stats.vitality / max_stat_value;
    obs[i++] = p.stats.agility / max_stat_value;
    obs[i++] = p.stats.reasoning / max_stat_value;
    obs[i++] = p.stats.endurance / max_stat_value;

    obs[i++] = p.dimes / qm_dimes_normalizer;

    for (int w = 0; w < weapon_count; ++w)
        obs[i++] = static_cast<float>(p.weapon_upgrade_levels[w]) / max_upgrade_level;
    obs[i++] = static_cast<float>(p.armor_upgrade_levels[0]) / max_upgrade_level;
    obs[i++] = static_cast<float>(p.armor_upgrade_levels[1]) / max_upgrade_level;
    obs[i++] = static_cast<float>(p.armor_upgrade_levels[2]) / max_upgrade_level;

    obs[i++] = static_cast<float>(static_cast<int>(p.equipment.weapon)) / weapon_count;

    for (int w = 0; w < weapon_count; ++w)
        obs[i++] = p.owned_weapons[w] ? 1.0f : 0.0f;

    {
        float min_stat_cost = qm_cost_normalizer;
        for (int s = 0; s < 5; ++s) {
            float val;
            switch (s) {
                case 0: val = p.stats.strength; break;
                case 1: val = p.stats.vitality; break;
                case 2: val = p.stats.agility; break;
                case 3: val = p.stats.reasoning; break;
                default: val = p.stats.endurance; break;
            }
            if (val < max_stat_value) {
                float c = UpgradeCosts::stat_cost(static_cast<int>(val));
                if (c < min_stat_cost) min_stat_cost = c;
            }
        }
        obs[i++] = min_stat_cost / qm_cost_normalizer;
    }

    for (int w = 0; w < weapon_count; ++w)
        obs[i++] = UpgradeCosts::weapon_cost(p.weapon_upgrade_levels[w]) / qm_cost_normalizer;

    {
        float min_armor_cost = qm_cost_normalizer;
        for (int a = 0; a < 3; ++a) {
            if (p.armor_upgrade_levels[a] < max_upgrade_level) {
                float c = UpgradeCosts::armor_cost(p.armor_upgrade_levels[a]);
                if (c < min_armor_cost) min_armor_cost = c;
            }
        }
        obs[i++] = min_armor_cost / qm_cost_normalizer;
    }

    obs[i++] = match_outcome;
    obs[i++] = engagement.teff / qm_teff_normalizer;
    obs[i++] = damage_dealt / qm_hp_normalizer;
    obs[i++] = damage_taken / qm_hp_normalizer;
    obs[i++] = p.health / p.max_hp;
    obs[i++] = p.max_hp / qm_hp_normalizer;

    obs[i++] = dropped_dimes.collected ? 0.0f : 1.0f;

    while (i < qm_obs_dim)
        obs[i++] = -2.0f;

    return obs;
}

void Engine::present() {
    if (renderer) SDL_RenderPresent(renderer);
}

void Engine::close() {
    if (renderer) {
        for (int i = 0; i < animation_count; ++i) {
            SDL_DestroyTexture(tex_textures[i]);
            tex_textures[i] = nullptr;
        }
        for (int i = 0; i < weapon_count; ++i) {
            SDL_DestroyTexture(tex_weapons[i]);
            tex_weapons[i] = nullptr;
        }
        SDL_DestroyRenderer(renderer);
        renderer = nullptr;
    }
    if (window) {
        SDL_DestroyWindow(window);
        window = nullptr;
    }
    if (is_render) {
        SDL_Quit();
    }
}

void Engine::on_damage_dealt() {
    engagement.on_damage_dealt();
}

bool Engine::try_collect_drop(float px, float py) {
    if (dropped_dimes.can_collect(px, py)) {
        p1.dimes += dropped_dimes.current_amount();
        dropped_dimes.collected = true;
        return true;
    }
    return false;
}

void Engine::handle_level_up(LevelUpIntent& intent) {
    if (intent.stat_up >= 0 && intent.stat_up <= 4) {
        p1.purchase_stat_upgrade(static_cast<StatType>(intent.stat_up));
    }
    if (intent.buy_weapon >= 0 && intent.buy_weapon < weapon_count) {
        if (p1.purchase_weapon(static_cast<WeaponType>(intent.buy_weapon)))
            reload_weapon_texture(p1);
    }
    if (intent.equip_weapon >= 0 && intent.equip_weapon < weapon_count) {
        if (p1.equip_weapon(static_cast<WeaponType>(intent.equip_weapon)))
            reload_weapon_texture(p1);
    }
    if (intent.weapon_upgrade_index >= 0 && intent.weapon_upgrade_index < weapon_count) {
        p1.purchase_weapon_upgrade(intent.weapon_upgrade_index);
    }
    if (intent.armor_upgrade >= 0 && intent.armor_upgrade <= 2) {
        p1.purchase_armor_upgrade(static_cast<ArmorSlot>(intent.armor_upgrade));
    }
}

void Engine::reload_weapon_texture(Player& p) {
    int idx = static_cast<int>(p.equipment.weapon);
    if (idx >= 0 && idx < weapon_count && tex_weapons[idx]) {
        p.load_weapon_texture(tex_weapons[idx]);
    }
}
