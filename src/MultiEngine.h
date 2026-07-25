#pragma once
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <vector>
#include <memory>
#include "Engine.h"
#include "Config.h"

namespace py = pybind11;

class MultiEngine {
public:
    int num_envs;
    int frame_skip;
    GameConfig config;
    std::vector<std::unique_ptr<Player>> p1s;
    std::vector<std::unique_ptr<Player>> p2s;
    std::vector<std::unique_ptr<Engine>> engines;
    
    MultiEngine(const std::string& config_path);
    
    py::tuple reset();
    py::tuple step(py::array_t<float> p1_actions, py::array_t<float> p2_actions, float dt);

private:
    PlayerIntent decode_action(const float* action, const Player& p);
};

void init_engines(MultiEngine& me, int num_envs);
