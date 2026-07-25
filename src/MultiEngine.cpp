#include "MultiEngine.h"
#include <cmath>

MultiEngine::MultiEngine(const std::string& config_path) 
    : config(load_game_config(config_path)), num_envs(0), frame_skip(config.frame_skip) {
    
    // num_envs is set from the Python side after construction; we use
    // a two-phase init: Python calls MultiEngine(path), then sets .num_envs
    // and calls _init_engines(). For backward compat, we also support
    // the old calling pattern where Python passes num_envs inline.
}

void init_engines(MultiEngine& me, int num_envs) {
    me.num_envs = num_envs;
    me.frame_skip = me.config.frame_skip;
    float p1_x = -1.0f, p1_y = -1.0f, p2_x = -1.0f, p2_y = -1.0f;
    float speed = me.config.playerspeed;
    int sw = me.config.screenw;
    int sh = me.config.screenh;
    for (int i = 0; i < num_envs; i++) {
        me.p1s.push_back(std::make_unique<Player>(p1_x, p1_y, speed, "player"));
        me.p2s.push_back(std::make_unique<Player>(p2_x, p2_y, speed, "boss"));
        me.engines.push_back(std::make_unique<Engine>(false, false, *me.p1s.back(), *me.p2s.back(), sw, sh));
    }
}



PlayerIntent MultiEngine::decode_action(const float* action, const Player& p) {
    int mx = static_cast<int>(action[0]) - 1;
    int my = static_cast<int>(action[1]) - 1;
    bool fire = action[2] > 0.5f;
    bool dash = action[3] > 0.5f;
    int spell = action[4] > 0.5f ? 1 : 0;
    
    float angle = static_cast<int>(action[5]) * (2.0f * M_PI / static_cast<float>(config.aim_directions));
    float aim_x = p.box.x + p.box.w / 2.0f + std::cos(angle) * config.aim_radius;
    float aim_y = p.box.y + p.box.h / 2.0f + std::sin(angle) * config.aim_radius;
    bool attack = action[6] > 0.5f;
    
    return PlayerIntent{mx, my, fire, dash, spell, aim_x, aim_y, attack};
}

py::tuple MultiEngine::reset() {
    py::array_t<float> p1_obs({num_envs, (int)obs_dim});
    py::array_t<float> p2_obs({num_envs, (int)obs_dim});
    
    auto p1_ptr = p1_obs.mutable_unchecked<2>();
    auto p2_ptr = p2_obs.mutable_unchecked<2>();
    
    for (int i = 0; i < num_envs; i++) {
        engines[i]->reset(-1.0f, -1.0f, -1.0f, -1.0f);
        
        auto obs1 = engines[i]->observe(*p1s[i], *p2s[i]);
        auto obs2 = engines[i]->observe(*p2s[i], *p1s[i]);
        
        for (int j = 0; j < obs_dim; j++) {
            p1_ptr(i, j) = obs1[j];
            p2_ptr(i, j) = obs2[j];
        }
    }
    
    py::dict obs_dict;
    obs_dict["player"] = p1_obs;
    obs_dict["boss"] = p2_obs;
    
    return py::make_tuple(obs_dict, py::none());
}

py::tuple MultiEngine::step(py::array_t<float> p1_actions, py::array_t<float> p2_actions, float dt) {
    auto p1_act_ptr = p1_actions.unchecked<2>();
    auto p2_act_ptr = p2_actions.unchecked<2>();
    
    py::array_t<float> p1_obs({num_envs, (int)obs_dim});
    py::array_t<float> p2_obs({num_envs, (int)obs_dim});
    py::array_t<float> p1_rewards({num_envs});
    py::array_t<float> p2_rewards({num_envs});
    py::array_t<float> all_dones({num_envs});
    py::array_t<float> p1_dmg_dealt({num_envs});
    py::array_t<float> p1_dmg_taken({num_envs});
    py::array_t<float> p2_dmg_dealt({num_envs});
    py::array_t<float> p2_dmg_taken({num_envs});
    
    auto p1_obs_ptr = p1_obs.mutable_unchecked<2>();
    auto p2_obs_ptr = p2_obs.mutable_unchecked<2>();
    auto p1_rew_ptr = p1_rewards.mutable_unchecked<1>();
    auto p2_rew_ptr = p2_rewards.mutable_unchecked<1>();
    auto all_dones_ptr = all_dones.mutable_unchecked<1>();
    auto p1_dd_ptr = p1_dmg_dealt.mutable_unchecked<1>();
    auto p1_dt_ptr = p1_dmg_taken.mutable_unchecked<1>();
    auto p2_dd_ptr = p2_dmg_dealt.mutable_unchecked<1>();
    auto p2_dt_ptr = p2_dmg_taken.mutable_unchecked<1>();
    
    #pragma omp parallel for
    for (int i = 0; i < num_envs; i++) {
        PlayerIntent i1 = decode_action(&p1_act_ptr(i, 0), *p1s[i]);
        PlayerIntent i2 = decode_action(&p2_act_ptr(i, 0), *p2s[i]);
        
        p1s[i]->damage_dealt_step = 0.0f;
        p1s[i]->damage_taken_step = 0.0f;
        p2s[i]->damage_dealt_step = 0.0f;
        p2s[i]->damage_taken_step = 0.0f;
        
        for (int f = 0; f < frame_skip; f++) {
            engines[i]->step(i1, i2, dt);
            if (engines[i]->is_done()) break;
        }
        
        bool done = engines[i]->is_done();
        all_dones_ptr(i) = done ? 1.0f : 0.0f;
        
        float time_penalty = -0.01f;
        p1_rew_ptr(i) = (p1s[i]->damage_dealt_step - p1s[i]->damage_taken_step) + time_penalty;
        p2_rew_ptr(i) = (p2s[i]->damage_dealt_step - p2s[i]->damage_taken_step) + time_penalty;
        
        if (done) {
            float win_bonus = 100.0f;
            if (p1s[i]->health > 0 && p2s[i]->health <= 0) {
                p1_rew_ptr(i) += win_bonus;
                p2_rew_ptr(i) -= win_bonus;
            } else if (p2s[i]->health > 0 && p1s[i]->health <= 0) {
                p2_rew_ptr(i) += win_bonus;
                p1_rew_ptr(i) -= win_bonus;
            }
        }
        
        p1_dd_ptr(i) = p1s[i]->damage_dealt_step;
        p1_dt_ptr(i) = p1s[i]->damage_taken_step;
        p2_dd_ptr(i) = p2s[i]->damage_dealt_step;
        p2_dt_ptr(i) = p2s[i]->damage_taken_step;
        
        if (done) {
            engines[i]->reset(-1.0f, -1.0f, -1.0f, -1.0f);
        }
        
        auto obs1 = engines[i]->observe(*p1s[i], *p2s[i]);
        auto obs2 = engines[i]->observe(*p2s[i], *p1s[i]);
        
        for (int j = 0; j < obs_dim; j++) {
            p1_obs_ptr(i, j) = obs1[j];
            p2_obs_ptr(i, j) = obs2[j];
        }
    }
    
    py::dict obs_dict;
    obs_dict["player"] = p1_obs;
    obs_dict["boss"] = p2_obs;
    
    py::dict rew_dict;
    rew_dict["player"] = p1_rewards;
    rew_dict["boss"] = p2_rewards;
    
    py::dict done_dict;
    done_dict["player"] = all_dones;
    done_dict["boss"] = all_dones;
    done_dict["__all__"] = all_dones;
    
    py::dict p1_info;
    p1_info["damage_dealt"] = p1_dmg_dealt;
    p1_info["damage_taken"] = p1_dmg_taken;
    py::dict p2_info;
    p2_info["damage_dealt"] = p2_dmg_dealt;
    p2_info["damage_taken"] = p2_dmg_taken;
    py::dict info_dict;
    info_dict["player"] = p1_info;
    info_dict["boss"] = p2_info;
    
    return py::make_tuple(obs_dict, rew_dict, done_dict, py::none(), info_dict);
}
