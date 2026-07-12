import math
import random
import sys
import os

sys.path.append(os.path.abspath("./build"))
import Game

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
MAX_HEALTH = 100
MAX_MANA = 50 + 20 * 2
MAX_PLAYER_VEL = 200
AIM_RADIUS = 1000.0
MAX_DIST = 1468.6
SPELL_NAMES = ["Fireball", "IceShard", "LightningBolt", "Barrage"]

MOVE_LEFT, MOVE_STAY_X, MOVE_RIGHT = -1, 0, 1
MOVE_DOWN, MOVE_STAY_Y, MOVE_UP = -1, 0, 1


class BaseBot:
    def parse_observation(self, obs):
        state = {
            "health": obs[0] * MAX_HEALTH,
            "mana": obs[1] * MAX_MANA,
            "stunned": bool(obs[2]),
            "is_dashing": bool(obs[3]),
            "cx": obs[4] * SCREEN_WIDTH,
            "cy": obs[5] * SCREEN_HEIGHT,
            "vx": obs[6] * MAX_PLAYER_VEL,
            "vy": obs[7] * MAX_PLAYER_VEL,
            "enemy_health": obs[8] * MAX_HEALTH,
            "dx": obs[9] * SCREEN_WIDTH,
            "dy": obs[10] * SCREEN_HEIGHT,
            "enemy_vx": obs[11] * MAX_PLAYER_VEL,
            "enemy_vy": obs[12] * MAX_PLAYER_VEL,
            "dist": obs[61] * MAX_DIST,
            "enemy_attacking": bool(obs[62]),
            "combo_stage": obs[63] * 2,
            "enemy_projectiles": [],
        }
        for j in range(12):
            base_idx = 13 + j * 5
            if obs[base_idx] > 0:
                state["enemy_projectiles"].append({
                    "rel_x": obs[base_idx + 1] * SCREEN_WIDTH,
                    "rel_y": obs[base_idx + 2] * SCREEN_HEIGHT,
                    "vx": obs[base_idx + 3] * 500,
                    "vy": obs[base_idx + 4] * 500,
                })
        return state

    def get_movement_towards(self, dx, dy, threshold=20):
        mx = MOVE_RIGHT if dx > threshold else MOVE_LEFT if dx < -threshold else MOVE_STAY_X
        my = MOVE_UP if dy > threshold else MOVE_DOWN if dy < -threshold else MOVE_STAY_Y
        return mx, my


class EasyBot(BaseBot):
    def __init__(self, screenw=SCREEN_WIDTH, screenh=SCREEN_HEIGHT):
        self.screenw = screenw
        self.screenh = screenh
        self.fire_cooldown = 0.0
        self.dash_cooldown = 0.0
        self.melee_cooldown = 0.0
        self.frame_counter = 0
        self.current_mx = MOVE_STAY_X
        self.current_my = MOVE_STAY_Y

    def act(self, obs_np, dt):
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.melee_cooldown = max(0.0, self.melee_cooldown - dt)

        state = self.parse_observation(obs_np)
        self.frame_counter += 1

        if self.frame_counter % 30 == 0:
            self.current_mx = random.choice([MOVE_LEFT, MOVE_STAY_X, MOVE_RIGHT])
            self.current_my = random.choice([MOVE_DOWN, MOVE_STAY_Y, MOVE_UP])

        fire = False
        spell = 0
        if self.fire_cooldown <= 0 and random.random() < 0.25 and state["mana"] > 15:
            fire = True
            self.fire_cooldown = 0.4
            spell = random.randint(0, 3)

        dash = False
        if self.dash_cooldown <= 0 and random.random() < 0.02:
            dash = True
            self.dash_cooldown = 0.3

        attack = False
        if self.melee_cooldown <= 0 and state["dist"] < 65 and random.random() < 0.3:
            attack = True
            self.melee_cooldown = 0.2

        aim_x = state["cx"] + state["dx"] + random.gauss(0, 60)
        aim_y = state["cy"] + state["dy"] + random.gauss(0, 60)

        return self.current_mx, self.current_my, fire, dash, spell, aim_x, aim_y, attack


class MediumBot(BaseBot):
    def __init__(self, screenw=SCREEN_WIDTH, screenh=SCREEN_HEIGHT):
        self.screenw = screenw
        self.screenh = screenh
        self.fire_cooldown = 0.0
        self.dash_cooldown = 0.0
        self.melee_cooldown = 0.0

    def act(self, obs_np, dt):
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.melee_cooldown = max(0.0, self.melee_cooldown - dt)

        state = self.parse_observation(obs_np)
        mx, my = self.get_movement_towards(state["dx"], state["dy"])

        aim_x = state["cx"] + state["dx"] + random.gauss(0, 30)
        aim_y = state["cy"] + state["dy"] + random.gauss(0, 30)

        fire = False
        spell = 0
        if self.fire_cooldown <= 0 and state["mana"] > 15 and state["dist"] < 800:
            fire = True
            self.fire_cooldown = 0.4
            spell = random.randint(0, 3)

        attack = False
        if self.melee_cooldown <= 0 and state["dist"] < 65:
            attack = True
            self.melee_cooldown = 0.2

        dash = False
        if self.dash_cooldown <= 0 and state["dist"] < 200:
            dash = True
            self.dash_cooldown = 0.3

        return mx, my, fire, dash, spell, aim_x, aim_y, attack


class HardBot(BaseBot):
    def __init__(self, screenw=SCREEN_WIDTH, screenh=SCREEN_HEIGHT):
        self.screenw = screenw
        self.screenh = screenh
        self.fire_cooldown = 0.0
        self.dash_cooldown = 0.0
        self.melee_cooldown = 0.0
        self.circle_dir = 1
        self.dir_timer = random.uniform(1.0, 3.0)

    def act(self, obs_np, dt):
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.melee_cooldown = max(0.0, self.melee_cooldown - dt)

        state = self.parse_observation(obs_np)

        OPTIMAL_MIN = 350
        OPTIMAL_MAX = 550
        MARGIN = 100

        mx, my = MOVE_STAY_X, MOVE_STAY_Y
        dash = False

        dodge_x, dodge_y = 0.0, 0.0
        danger_level = 0.0
        for b in state["enemy_projectiles"]:
            bspeed = math.hypot(b["vx"], b["vy"])
            if bspeed < 1:
                continue
            bdx, bdy = b["vx"] / bspeed, b["vy"] / bspeed
            forward = b["rel_x"] * bdx + b["rel_y"] * bdy
            if forward > -20 and math.hypot(b["rel_x"], b["rel_y"]) < 400:
                perp = b["rel_x"] * bdy - b["rel_y"] * bdx
                if abs(perp) < 35:
                    urgency = max(0.0, 1.0 - math.hypot(b["rel_x"], b["rel_y"]) / 400.0)
                    escape_dir = 1.0 if perp > 0 else -1.0
                    dodge_x += escape_dir * -bdy * urgency * 2.0
                    dodge_y += escape_dir * bdx * urgency * 2.0
                    danger_level += urgency

        dodge_mag = math.hypot(dodge_x, dodge_y)
        if dodge_mag > 0.2:
            mx, my = self.get_movement_towards(dodge_x, dodge_y, threshold=1)
        elif state["dist"] > OPTIMAL_MAX:
            mx, my = self.get_movement_towards(state["dx"], state["dy"])
        elif state["dist"] < OPTIMAL_MIN:
            mx, my = self.get_movement_towards(-state["dx"], -state["dy"])

        if self.dash_cooldown <= 0:
            if danger_level > 1.0 or (state["dist"] < 150):
                dash = True
                self.dash_cooldown = 0.3

        fire = False
        spell = 0
        if self.fire_cooldown <= 0 and state["mana"] > 15 and state["dist"] < 700:
            fire = True
            self.fire_cooldown = 0.35
            if state["dist"] < 200:
                spell = 2
            elif random.random() < 0.4:
                spell = random.randint(0, 1)
            else:
                spell = random.randint(0, 3)

        attack = False
        if self.melee_cooldown <= 0 and state["dist"] < 65:
            attack = True
            self.melee_cooldown = 0.2

        aim_x = state["cx"] + state["dx"] + random.gauss(0, 15)
        aim_y = state["cy"] + state["dy"] + random.gauss(0, 15)

        return mx, my, fire, dash, spell, aim_x, aim_y, attack


class ExpertBot(BaseBot):
    def __init__(self, screenw=SCREEN_WIDTH, screenh=SCREEN_HEIGHT):
        self.screenw = screenw
        self.screenh = screenh
        self.fire_cooldown = 0.0
        self.dash_cooldown = 0.0
        self.melee_cooldown = 0.0
        self.circle_dir = 1.0
        self.stance_timer = 0.0
        self.current_stance = "SKIRMISH"
        self.vel_history = []

    def act(self, obs_np, dt):
        if dt <= 0:
            dt = 0.016
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.melee_cooldown = max(0.0, self.melee_cooldown - dt)

        state = self.parse_observation(obs_np)

        self.vel_history.append((state["enemy_vx"], state["enemy_vy"], dt))
        if len(self.vel_history) > 3:
            self.vel_history.pop(0)
        ea_x, ea_y = 0.0, 0.0
        if len(self.vel_history) >= 2:
            v2, v1 = self.vel_history[-1], self.vel_history[-2]
            ea_x = (v2[0] - v1[0]) / v2[2]
            ea_y = (v2[1] - v1[1]) / v2[2]

        time_to_hit = state["dist"] / max(500, 1.0)
        pred_enemy_x = state["cx"] + state["dx"] + (state["enemy_vx"] * time_to_hit) + (0.5 * ea_x * time_to_hit ** 2)
        pred_enemy_y = state["cy"] + state["dy"] + (state["enemy_vy"] * time_to_hit) + (0.5 * ea_y * time_to_hit ** 2)
        aim_x = pred_enemy_x + random.gauss(0, 8)
        aim_y = pred_enemy_y + random.gauss(0, 8)

        imminent_threats = 0
        critical_iframe = False
        dodge_x, dodge_y = 0.0, 0.0
        for b in state["enemy_projectiles"]:
            bspeed = math.hypot(b["vx"], b["vy"])
            if bspeed < 1:
                continue
            bdx, bdy = b["vx"] / bspeed, b["vy"] / bspeed
            t_closest = (b["rel_x"] * bdx + b["rel_y"] * bdy) / bspeed
            if 0 < t_closest < 1.2:
                closest_x = b["rel_x"] - b["vx"] * t_closest
                closest_y = b["rel_y"] - b["vy"] * t_closest
                perp = math.hypot(closest_x, closest_y)
                if perp < 45:
                    imminent_threats += 1
                    if t_closest < 0.18:
                        critical_iframe = True
                    repel_x, repel_y = -closest_x, -closest_y
                    r = math.hypot(repel_x, repel_y)
                    if r == 0:
                        r = 1
                    force = (1.5 / (t_closest + 0.05)) * (45.0 / max(r, 1.0))
                    dodge_x += (repel_x / r) * force
                    dodge_y += (repel_y / r) * force

        self.stance_timer -= dt
        if self.stance_timer <= 0:
            if imminent_threats >= 2:
                self.current_stance = "EVADE"
                self.stance_timer = 0.4
            elif state["dist"] > 450 and state["mana"] >= 30:
                self.current_stance = "ASSAULT"
                self.stance_timer = random.uniform(1.0, 1.8)
            else:
                self.current_stance = "SKIRMISH"
                self.stance_timer = random.uniform(1.0, 2.5)
                if random.random() < 0.5:
                    self.circle_dir *= -1.0

        target_dist = 350
        speed_mod = 1.0
        if self.current_stance == "ASSAULT":
            target_dist = 200
            speed_mod = 1.25
        elif self.current_stance == "EVADE":
            target_dist = 480
            speed_mod = 0.95

        fx, fy = dodge_x, dodge_y
        dist_error = state["dist"] - target_dist
        dir_ex = state["dx"] / max(state["dist"], 1.0)
        dir_ey = state["dy"] / max(state["dist"], 1.0)
        fx += dir_ex * (dist_error / 100.0) * speed_mod
        fy += dir_ey * (dist_error / 100.0) * speed_mod
        fx += -dir_ey * self.circle_dir * 1.4 * speed_mod
        fy += dir_ex * self.circle_dir * 1.4 * speed_mod

        w_margin, w_force = 120, 3.0
        if state["cx"] < w_margin:
            fx += w_force * ((w_margin - state["cx"]) / w_margin) ** 2
        elif state["cx"] > self.screenw - w_margin:
            fx -= w_force * ((state["cx"] - (self.screenw - w_margin)) / w_margin) ** 2
        if state["cy"] < w_margin:
            fy += w_force * ((w_margin - state["cy"]) / w_margin) ** 2
        elif state["cy"] > self.screenh - w_margin:
            fy -= w_force * ((state["cy"] - (self.screenh - w_margin)) / w_margin) ** 2

        if self.current_stance != "EVADE":
            fx += random.uniform(-0.2, 0.2)
            fy += random.uniform(-0.2, 0.2)

        f_mag = math.hypot(fx, fy)
        if f_mag > 1.0:
            fx /= f_mag
            fy /= f_mag
        mx = 1 if fx > 0.22 else -1 if fx < -0.22 else 0
        my = 1 if fy > 0.22 else -1 if fy < -0.22 else 0

        dash = False
        if self.dash_cooldown <= 0.0:
            if critical_iframe:
                dash = True
            elif self.current_stance == "ASSAULT" and state["dist"] > 450 and state["mana"] >= 20:
                dash = True
            if dash:
                self.dash_cooldown = 0.3

        fire = False
        spell = 0
        max_range = 750 if self.current_stance == "ASSAULT" else 600
        if self.fire_cooldown <= 0 and state["dist"] < max_range and state["mana"] > 15:
            fire = True
            self.fire_cooldown = 0.28 if self.current_stance == "ASSAULT" else 0.36
            if self.current_stance == "ASSAULT":
                spell = 0
            elif imminent_threats >= 2:
                spell = 1
            elif state["dist"] > 450 and state["mana"] > 20:
                spell = random.randint(2, 3)
            else:
                spell = random.randint(0, 3)

        attack = False
        if self.melee_cooldown <= 0 and state["dist"] < 65:
            attack = True
            self.melee_cooldown = 0.2

        return mx, my, fire, dash, spell, aim_x, aim_y, attack


class Human():
    def __init__(self, screenw, screenh):
        pass
    def act(self, obs, dt):
        return Game.get_human_intent(Game.poll_events())

class NoopBot():
    def __init__(self, screenw, screenh):
        pass
    def act(self, obs, dt):
        return 0, 0, 0, 0, 0, 0, 0, 0

BOTS = {
    "easy": EasyBot,
    "medium": MediumBot,
    "hard": HardBot,
    "expert": ExpertBot,
    "human": Human,
}
