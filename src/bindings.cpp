#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "Engine.h"
#include "Visuals.h"
#include "Events.h"
#include "Input.h"
#include "Equipment.h"

namespace py = pybind11;

py::array_t<float> obs_to_numpy(const std::array<float, obs_dim>& obs) {
    auto arr = py::array_t<float>(obs_dim);
    std::copy(obs.begin(), obs.end(), arr.mutable_data());
    return arr;
}

PYBIND11_MODULE(Game, m) {
    py::class_<FrameInput>(m, "FrameInput")
        .def_readonly("quit", &FrameInput::quit)
        .def_readonly("mouse_left_clicked", &FrameInput::mouse_left_clicked)
        .def_readonly("mouse_right_clicked", &FrameInput::mouse_right_clicked)
        .def_readonly("mouse_x", &FrameInput::mouse_x)
        .def_readonly("mouse_y", &FrameInput::mouse_y);

    py::class_<PlayerIntent>(m, "PlayerIntent")
        .def(py::init<int, int, bool, bool, bool, float, float, bool>(),
             py::arg("mx") = 0, py::arg("my") = 0,
             py::arg("fire") = false, py::arg("dash") = false,
             py::arg("reload") = false,
             py::arg("aim_x") = 0.0f, py::arg("aim_y") = 0.0f,
             py::arg("attack") = false)
        .def_readwrite("mx", &PlayerIntent::mx)
        .def_readwrite("my", &PlayerIntent::my)
        .def_readwrite("fire", &PlayerIntent::fire)
        .def_readwrite("dash", &PlayerIntent::dash)
        .def_readwrite("reload", &PlayerIntent::reload)
        .def_readwrite("aim_x", &PlayerIntent::aim_x)
        .def_readwrite("aim_y", &PlayerIntent::aim_y)
        .def_readwrite("attack", &PlayerIntent::attack);

    py::enum_<WeaponType>(m, "WeaponType")
        .value("Katana", WeaponType::Katana)
        .value("ShortSword", WeaponType::ShortSword)
        .value("Daggers", WeaponType::Daggers)
        .value("GreatSword", WeaponType::GreatSword)
        .value("Shield", WeaponType::Shield)
        .value("Staff", WeaponType::Staff);

    py::class_<PlayerStats>(m, "PlayerStats")
        .def_readonly("strength", &PlayerStats::strength)
        .def_readonly("vitality", &PlayerStats::vitality)
        .def_readonly("agility", &PlayerStats::agility)
        .def_readonly("reasoning", &PlayerStats::reasoning)
        .def_readonly("endurance", &PlayerStats::endurance);

    py::class_<Player>(m, "Player")
        .def(py::init<float, float, float, std::string>(),
             py::arg("x"), py::arg("y"), py::arg("speed"), py::arg("name"))
        .def("move", &Player::move)
        .def("reset", &Player::reset)
        .def_readonly("health", &Player::health)
        .def_readonly("ammo", &Player::ammo)
        .def_readonly("is_reloading", &Player::is_reloading)
        .def_readonly("vx", &Player::vx)
        .def_readonly("vy", &Player::vy)
        .def_readonly("stats", &Player::stats)
        .def_property_readonly("weapon", [](Player& p) { return p.equipment.weapon; })
        .def_readonly("equip_load_ratio", &Player::equip_load_ratio);

    py::class_<Engine>(m, "Engine")
        .def(py::init<bool, bool, Player&, Player&, int, int>(),
             py::arg("vsync"), py::arg("render"),
             py::arg("p1"), py::arg("p2"),
             py::arg("screenw"), py::arg("screenh"))
        .def("step", &Engine::step)
        .def("render", &Engine::render)
        .def("present", &Engine::present)
        .def("observe", [](Engine& self, Player& self_player, Player& enemy) {
            return obs_to_numpy(self.observe(self_player, enemy));
        })
        .def("reset", &Engine::reset,
             py::arg("p1_x") = -1.0f, py::arg("p1_y") = -1.0f,
             py::arg("p2_x") = -1.0f, py::arg("p2_y") = -1.0f)
        .def("close", &Engine::close)
        .def("is_done", &Engine::is_done)
        .def("player1", &Engine::player1, py::return_value_policy::reference)
        .def("player2", &Engine::player2, py::return_value_policy::reference);

    py::class_<Visuals>(m, "Visuals")
        .def_static("init", &Visuals::init)
        .def_static("start_screen", &Visuals::start_screen)
        .def_static("training_screen", &Visuals::training_screen)
        .def_static("end_screen", &Visuals::end_screen)
        .def_static("hud", &Visuals::hud)
        .def_static("shutdown", &Visuals::shutdown);

    m.def("poll_events", &pollEvents);
    m.def("get_human_intent", &getHumanIntent);
}
