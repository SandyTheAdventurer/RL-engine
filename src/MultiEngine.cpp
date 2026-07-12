#include "MultiEngine.h"
#include <cmath>

MultiEngine::MultiEngine(int num_envs, int frame_skip, float p1_x, float p1_y, float p1_speed, float p2_x, float p2_y, float p2_speed, int screenw, int screenh) 
    : num_envs(num_envs), frame_skip(frame_skip) {
    
    for (int i = 0; i < num_envs; i++) {
        p1s.push_back(std::make_unique<Player>(p1_x, p1_y, p1_speed, "player"));
        p2s.push_back(std::make_unique<Player>(p2_x, p2_y, p2_speed, "boss"));
        engines.push_back(std::make_unique<Engine>(false, false, *p1s.back(), *p2s.back(), screenw, screenh));
        
        prev_p1_healths.push_back(p1s.back()->health);
        prev_p2_healths.push_back(p2s.back()->health);
    }
}



PlayerIntent MultiEngine::decode_action(const float* action, const Player& p) {
    int mx = static_cast<int>(action[0]) - 1;
    int my = static_cast<int>(action[1]) - 1;
    bool fire = action[2] > 0.5f;
    bool dash = action[3] > 0.5f;
    int spell = action[4] > 0.5f ? 1 : 0;
    
    float angle = static_cast<int>(action[5]) * (2.0f * M_PI / 16.0f);
    float aim_x = p.box.x + p.box.w / 2.0f + std::cos(angle) * 1000.0f;
    float aim_y = p.box.y + p.box.h / 2.0f + std::sin(angle) * 1000.0f;
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
        prev_p1_healths[i] = p1s[i]->health;
        prev_p2_healths[i] = p2s[i]->health;
        
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
    
    auto p1_obs_ptr = p1_obs.mutable_unchecked<2>();
    auto p2_obs_ptr = p2_obs.mutable_unchecked<2>();
    auto p1_rew_ptr = p1_rewards.mutable_unchecked<1>();
    auto p2_rew_ptr = p2_rewards.mutable_unchecked<1>();
    auto all_dones_ptr = all_dones.mutable_unchecked<1>();
    
    #pragma omp parallel for
    for (int i = 0; i < num_envs; i++) {
        PlayerIntent i1 = decode_action(&p1_act_ptr(i, 0), *p1s[i]);
        PlayerIntent i2 = decode_action(&p2_act_ptr(i, 0), *p2s[i]);
        
        for (int f = 0; f < frame_skip; f++) {
            engines[i]->step(i1, i2, dt);
            if (engines[i]->is_done()) break;
        }
        
        bool done = engines[i]->is_done();
        all_dones_ptr(i) = done ? 1.0f : 0.0f;
        
        float delta_p1 = p1s[i]->health - prev_p1_healths[i];
        float delta_p2 = p2s[i]->health - prev_p2_healths[i];
        p1_rew_ptr(i) = delta_p1 - delta_p2;
        p2_rew_ptr(i) = delta_p2 - delta_p1;
        
        if (done) {
            engines[i]->reset(-1.0f, -1.0f, -1.0f, -1.0f);
        }
        
        prev_p1_healths[i] = p1s[i]->health;
        prev_p2_healths[i] = p2s[i]->health;
        
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
    
    return py::make_tuple(obs_dict, rew_dict, done_dict, py::none(), py::none());
}
