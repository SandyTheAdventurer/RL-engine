#pragma once
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <vector>
#include <memory>
#include "Engine.h"

namespace py = pybind11;

class MultiEngine {
public:
    int num_envs;
    int frame_skip;
    std::vector<std::unique_ptr<Player>> p1s;
    std::vector<std::unique_ptr<Player>> p2s;
    std::vector<std::unique_ptr<Engine>> engines;
    std::vector<float> prev_p1_healths;
    std::vector<float> prev_p2_healths;
    
    MultiEngine(int num_envs, int frame_skip, float p1_x, float p1_y, float p1_speed, float p2_x, float p2_y, float p2_speed, int screenw, int screenh);
    
    py::tuple reset();
    py::tuple step(py::array_t<float> p1_actions, py::array_t<float> p2_actions, float dt);

private:
    PlayerIntent decode_action(const float* action, const Player& p);
};
