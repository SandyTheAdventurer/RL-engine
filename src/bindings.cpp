#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "Engine.h"
#include "Visuals.h"
#include "Events.h"
#include "Input.h"
#include "Equipment.h"
#include "Spell.h"
#include "Economy.h"
#include "MultiEngine.h"

namespace py = pybind11;

template<size_t N>
py::array_t<float> obs_to_numpy(const std::array<float, N>& obs) {
    auto arr = py::array_t<float>(N);
    std::copy(obs.begin(), obs.end(), arr.mutable_data());
    return arr;
}

py::tuple step_interactive_frameskip(Engine& engine, const PlayerIntent& p2_intent, int frame_skip, float dt) {
    int agg_mx = 0, agg_my = 0;
    bool agg_fire = false, agg_dash = false, agg_attack = false;
    int agg_spell = 0;
    float agg_aim_x = 0.0f, agg_aim_y = 0.0f;
    bool quit = false;

    Uint64 freq = SDL_GetPerformanceFrequency();
    Uint64 target_count = SDL_GetPerformanceCounter() + static_cast<Uint64>(dt * freq);

    for (int i = 0; i < frame_skip; i++) {
        if (engine.is_done()) break;

        FrameInput frame_input = pollEvents();
        if (frame_input.quit) {
            quit = true;
            break;
        }

        PlayerIntent human = getHumanIntent(frame_input);

        if (human.mx != 0) agg_mx = human.mx;
        if (human.my != 0) agg_my = human.my;
        agg_fire = agg_fire || human.fire;
        agg_dash = agg_dash || human.dash;
        if (human.selected_spell > 0) agg_spell = human.selected_spell;
        agg_attack = agg_attack || human.attack;
        agg_aim_x = human.aim_x;
        agg_aim_y = human.aim_y;

        PlayerIntent p2_copy = p2_intent;
        engine.step(human, p2_copy, dt);
        engine.render();
        Visuals::hud(engine);
        engine.present();

        Uint64 now = SDL_GetPerformanceCounter();
        if (now < target_count) {
            Uint64 delay_ns = ((target_count - now) * 1000000000ULL) / freq;
            SDL_DelayNS(delay_ns);
        }
        target_count = SDL_GetPerformanceCounter() + static_cast<Uint64>(dt * freq);
    }

    PlayerIntent fake_intent{agg_mx, agg_my, agg_fire, agg_dash, agg_spell, agg_aim_x, agg_aim_y, agg_attack};
    return py::make_tuple(fake_intent, quit);
}

PYBIND11_MODULE(Game, m) {
    py::class_<FrameInput>(m, "FrameInput")
        .def_readonly("quit", &FrameInput::quit)
        .def_readonly("mouse_left_clicked", &FrameInput::mouse_left_clicked)
        .def_readonly("mouse_right_clicked", &FrameInput::mouse_right_clicked)
        .def_readonly("mouse_x", &FrameInput::mouse_x)
        .def_readonly("mouse_y", &FrameInput::mouse_y)
        .def_readonly("pressed_key", &FrameInput::pressed_key);

    py::class_<LevelUpIntent>(m, "LevelUpIntent")
        .def(py::init<>())
        .def_readwrite("stat_up", &LevelUpIntent::stat_up)
        .def_readwrite("buy_weapon", &LevelUpIntent::buy_weapon)
        .def_readwrite("equip_weapon", &LevelUpIntent::equip_weapon)
        .def_readwrite("weapon_upgrade_index", &LevelUpIntent::weapon_upgrade_index)
        .def_readwrite("armor_upgrade", &LevelUpIntent::armor_upgrade);

    py::class_<PlayerIntent>(m, "PlayerIntent")
        .def(py::init<int, int, bool, bool, int, float, float, bool>(),
             py::arg("mx") = 0, py::arg("my") = 0,
             py::arg("fire") = false, py::arg("dash") = false,
             py::arg("selected_spell") = 0,
             py::arg("aim_x") = 0.0f, py::arg("aim_y") = 0.0f,
             py::arg("attack") = false)
        .def_readwrite("mx", &PlayerIntent::mx)
        .def_readwrite("my", &PlayerIntent::my)
        .def_readwrite("fire", &PlayerIntent::fire)
        .def_readwrite("dash", &PlayerIntent::dash)
        .def_readwrite("selected_spell", &PlayerIntent::selected_spell)
        .def_readwrite("aim_x", &PlayerIntent::aim_x)
        .def_readwrite("aim_y", &PlayerIntent::aim_y)
        .def_readwrite("attack", &PlayerIntent::attack);

    py::enum_<WeaponType>(m, "WeaponType")
        .value("Sword", WeaponType::Sword)
        .value("Daggers", WeaponType::Daggers)
        .value("GreatSword", WeaponType::GreatSword)
        .value("Staff", WeaponType::Staff)
        .value("Axe", WeaponType::Axe);

    py::enum_<SpellType>(m, "SpellType")
        .value("Fireball", SpellType::Fireball)
        .value("IceShard", SpellType::IceShard)
        .value("LightningBolt", SpellType::LightningBolt)
        .value("ArcaneBarrage", SpellType::ArcaneBarrage);

    py::enum_<StatType>(m, "StatType")
        .value("Strength", StatType::Strength)
        .value("Vitality", StatType::Vitality)
        .value("Agility", StatType::Agility)
        .value("Reasoning", StatType::Reasoning)
        .value("Endurance", StatType::Endurance);

    py::enum_<ArmorSlot>(m, "ArmorSlot")
        .value("Head", ArmorSlot::Head)
        .value("Chest", ArmorSlot::Chest)
        .value("Legs", ArmorSlot::Legs);

    py::class_<PlayerStats>(m, "PlayerStats")
        .def_readonly("strength", &PlayerStats::strength)
        .def_readonly("vitality", &PlayerStats::vitality)
        .def_readonly("agility", &PlayerStats::agility)
        .def_readonly("reasoning", &PlayerStats::reasoning)
        .def_readonly("endurance", &PlayerStats::endurance);

    py::class_<EngagementTracker>(m, "EngagementTracker")
        .def(py::init<>())
        .def_readwrite("distance_threshold", &EngagementTracker::distance_threshold)
        .def_readwrite("damage_window", &EngagementTracker::damage_window)
        .def_readwrite("perfect_dodge_window", &EngagementTracker::perfect_dodge_window)
        .def_readwrite("teff", &EngagementTracker::teff)
        .def_readwrite("time_since_damage", &EngagementTracker::time_since_damage)
        .def_readwrite("time_since_perfect_dodge", &EngagementTracker::time_since_perfect_dodge)
        .def("is_engaged", &EngagementTracker::is_engaged)
        .def("update", &EngagementTracker::update, py::arg("dt"), py::arg("distance"))
        .def("on_damage_dealt", &EngagementTracker::on_damage_dealt)
        .def("reset", &EngagementTracker::reset);

    py::class_<DroppedDimes>(m, "DroppedDimes")
        .def(py::init<>())
        .def_readwrite("x", &DroppedDimes::x)
        .def_readwrite("y", &DroppedDimes::y)
        .def_readwrite("amount", &DroppedDimes::amount)
        .def_readwrite("time_since_drop", &DroppedDimes::time_since_drop)
        .def_readwrite("decay_start_time", &DroppedDimes::decay_start_time)
        .def_readwrite("collect_radius", &DroppedDimes::collect_radius)
        .def_readwrite("collected", &DroppedDimes::collected)
        .def("can_collect", &DroppedDimes::can_collect, py::arg("px"), py::arg("py"))
        .def("current_amount", &DroppedDimes::current_amount, py::arg("lambda") = economy_lambda);

    py::class_<Economy>(m, "Economy")
        .def_static("calculate_payout", &Economy::calculate_payout,
                     py::arg("teff"), py::arg("base") = economy_base_payout,
                     py::arg("par_time") = economy_par_time,
                     py::arg("lambda") = economy_lambda,
                     py::arg("min_multiplier") = economy_min_multiplier)
        .def_static("calculate_pity_dimes", &Economy::calculate_pity_dimes,
                     py::arg("damage_dealt"), py::arg("perfect_dodges"),
                     py::arg("parries"), py::arg("alpha") = economy_pity_alpha,
                     py::arg("beta") = economy_pity_beta,
                     py::arg("gamma") = economy_pity_gamma)
        .def_static("create_drop", &Economy::create_drop,
                     py::arg("x"), py::arg("y"), py::arg("current_dimes"),
                     py::arg("drop_fraction") = economy_drop_fraction)
        .def_static("apply_decay", &Economy::apply_decay,
                     py::arg("initial_amount"), py::arg("elapsed"),
                     py::arg("decay_delay"), py::arg("lambda"));

    py::class_<UpgradeCosts>(m, "UpgradeCosts")
        .def_static("stat_cost", &UpgradeCosts::stat_cost, py::arg("current_level"))
        .def_static("weapon_cost", &UpgradeCosts::weapon_cost, py::arg("current_level"))
        .def_static("armor_cost", &UpgradeCosts::armor_cost, py::arg("current_level"));

    py::class_<Player>(m, "Player")
        .def(py::init<float, float, float, std::string>(),
             py::arg("x"), py::arg("y"), py::arg("speed"), py::arg("name"))
        .def("move", &Player::move)
        .def("reset", &Player::reset)
        .def_readonly("health", &Player::health)
        .def_readonly("mana", &Player::mana)
        .def_readonly("stun_timer", &Player::stun_timer)
        .def_readonly("vx", &Player::vx)
        .def_readonly("vy", &Player::vy)
        .def_readonly("stats", &Player::stats)
        .def_readonly("max_hp", &Player::max_hp)
        .def_readwrite("damage_dealt_step", &Player::damage_dealt_step)
        .def_readwrite("damage_taken_step", &Player::damage_taken_step)
        .def_property_readonly("weapon", [](Player& p) { return p.equipment.weapon; })
        .def_readonly("equip_load_ratio", &Player::equip_load_ratio)
        .def_readwrite("dimes", &Player::dimes)
        .def_property_readonly("px", [](Player& p) { return p.box.x + p.box.w / 2; })
        .def_property_readonly("py", [](Player& p) { return p.box.y + p.box.h / 2; })
        .def_property_readonly("weapon_upgrade_levels", [](Player& p) {
            return std::vector<int>(p.weapon_upgrade_levels, p.weapon_upgrade_levels + weapon_count);
        })
        .def_property_readonly("armor_upgrade_levels", [](Player& p) {
            return std::vector<int>(p.armor_upgrade_levels, p.armor_upgrade_levels + 3);
        })
        .def("can_afford", &Player::can_afford)
        .def("is_weapon_owned", &Player::is_weapon_owned)
        .def("purchase_stat_upgrade", &Player::purchase_stat_upgrade)
        .def("purchase_weapon", &Player::purchase_weapon)
        .def("equip_weapon", &Player::equip_weapon)
        .def("purchase_weapon_upgrade", &Player::purchase_weapon_upgrade, py::arg("weapon_index"))
        .def("purchase_armor_upgrade", &Player::purchase_armor_upgrade);

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
        .def("observe_qm", [](Engine& self, Player& p, float match_outcome,
                              float damage_dealt, float damage_taken) {
            return obs_to_numpy(self.observe_qm(p, match_outcome, damage_dealt, damage_taken));
        }, py::arg("p"), py::arg("match_outcome"),
           py::arg("damage_dealt"), py::arg("damage_taken"))
        .def("reset", &Engine::reset,
             py::arg("p1_x") = -1.0f, py::arg("p1_y") = -1.0f,
             py::arg("p2_x") = -1.0f, py::arg("p2_y") = -1.0f)
        .def("close", &Engine::close)
        .def("is_done", &Engine::is_done)
        .def("is_death_done", &Engine::is_death_done)
        .def("player1", &Engine::player1, py::return_value_policy::reference)
        .def("player2", &Engine::player2, py::return_value_policy::reference)
        .def("get_teff", &Engine::get_teff)
        .def("on_damage_dealt", &Engine::on_damage_dealt)
        .def("try_collect_drop", &Engine::try_collect_drop, py::arg("px"), py::arg("py"))
        .def("handle_level_up", &Engine::handle_level_up)
        .def("reload_weapon_texture", &Engine::reload_weapon_texture)
        .def_property_readonly("engagement", [](Engine& self) -> EngagementTracker& {
            return self.engagement;
        }, py::return_value_policy::reference)
        .def_property_readonly("dropped_dimes", [](Engine& self) -> DroppedDimes& {
            return self.dropped_dimes;
        }, py::return_value_policy::reference);

    py::enum_<MenuResult>(m, "MenuResult")
        .value("NONE", MenuResult::NONE)
        .value("PLAY", MenuResult::PLAY)
        .value("QUIT", MenuResult::QUIT)
        .value("RESTART", MenuResult::RESTART);

    py::class_<Visuals>(m, "Visuals")
        .def_static("init", &Visuals::init)
        .def_static("start_menu", &Visuals::start_menu)
        .def_static("end_menu", &Visuals::end_menu)
        .def_static("hud", &Visuals::hud)
        .def_static("shutdown", &Visuals::shutdown)
        .def_static("start_fight_music", &Visuals::start_fight_music)
        .def_static("stop_fight_music", &Visuals::stop_fight_music);

    m.def("poll_events", &pollEvents);
    m.def("get_human_intent", &getHumanIntent);
    m.def("step_interactive_frameskip", &step_interactive_frameskip);
    
    py::class_<MultiEngine>(m, "MultiEngine")
        .def(py::init<const std::string&>(),
             py::arg("config_path"))
        .def("init_engines", [](MultiEngine& self, int num_envs) {
            init_engines(self, num_envs);
        }, py::arg("num_envs"))
        .def_readonly("frame_skip", &MultiEngine::frame_skip)
        .def("reset", &MultiEngine::reset)
        .def("step", &MultiEngine::step, py::arg("p1_actions"), py::arg("p2_actions"), py::arg("dt"));
}
