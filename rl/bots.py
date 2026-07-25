import math
import random
import sys
import os

sys.path.append(os.path.abspath("./build"))
import Game
from rl.config import screenw as cfg_screenw, screenh as cfg_screenh, aim_radius as cfg_aim_radius

SCREEN_WIDTH = cfg_screenw()
SCREEN_HEIGHT = cfg_screenh()
MAX_HEALTH = 100
MAX_MANA = 50 + 20 * 2
MAX_PLAYER_VEL = 200
AIM_RADIUS = cfg_aim_radius()
MAX_DIST = 1468.6
SPELL_NAMES = ["Fireball", "IceShard", "LightningBolt", "Barrage"]

MOVE_LEFT, MOVE_STAY_X, MOVE_RIGHT = -1, 0, 1
MOVE_DOWN, MOVE_STAY_Y, MOVE_UP = -1, 0, 1


class BaseBot:
    # C++ Engine::observe layout (obs_dim = 88, max_proj_obs = 6):
    #   [0-7]    self: health, mana, stunned, dashing, cx, cy, vx, vy
    #   [8-12]   enemy base: health, dx, dy, enemy_vx, enemy_vy
    #   [13-42]  SELF projectiles (6 x [active, rx, ry, vx, vy])
    #   [43-72]  ENEMY projectiles (6 x [active, rx, ry, vx, vy])
    #   [73]     dist, [74] self attacking, [75] self combo
    #   [76]     enemy attacking, [77] enemy combo, [78] enemy dashing
    #   [79]     enemy stunned, [80] enemy weapon
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
            "dist": obs[73] * MAX_DIST,
            "enemy_attacking": bool(obs[76]),
            "enemy_combo_stage": obs[77] * 2,
            "enemy_is_dashing": bool(obs[78]),
            "enemy_stunned": bool(obs[79]),
            "enemy_weapon": obs[80],
            "enemy_projectiles": [],
        }
        for j in range(6):
            base = 43 + j * 5
            if obs[base] > 0:
                state["enemy_projectiles"].append({
                    "rel_x": obs[base + 1] * SCREEN_WIDTH,
                    "rel_y": obs[base + 2] * SCREEN_HEIGHT,
                    "vx": obs[base + 3] * 500,
                    "vy": obs[base + 4] * 500,
                })
        return state

    def get_movement_towards(self, dx, dy, threshold=20):
        mx = MOVE_RIGHT if dx > threshold else MOVE_LEFT if dx < -threshold else MOVE_STAY_X
        my = MOVE_UP if dy > threshold else MOVE_DOWN if dy < -threshold else MOVE_STAY_Y
        return mx, my

    def _avoid_walls(self, fx, fy, cx, cy):
        w_margin, w_force = 120, 3.0
        if cx < w_margin:
            fx += w_force * ((w_margin - cx) / w_margin) ** 2
        elif cx > self.screenw - w_margin:
            fx -= w_force * ((cx - (self.screenw - w_margin)) / w_margin) ** 2
        if cy < w_margin:
            fy += w_force * ((w_margin - cy) / w_margin) ** 2
        elif cy > self.screenh - w_margin:
            fy -= w_force * ((cy - (self.screenh - w_margin)) / w_margin) ** 2
        return fx, fy

    def _to_discrete(self, fx, fy):
        f_mag = math.hypot(fx, fy)
        if f_mag > 1.0:
            fx /= f_mag
            fy /= f_mag
        mx = 1 if fx > 0.22 else -1 if fx < -0.22 else 0
        my = 1 if fy > 0.22 else -1 if fy < -0.22 else 0
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
    """Average player: competent but flawed. Dodges most projectiles, keeps
    mid distance, fires on a loose cadence, and makes occasional mistakes."""

    def __init__(self, screenw=SCREEN_WIDTH, screenh=SCREEN_HEIGHT):
        self.screenw = screenw
        self.screenh = screenh
        self.fire_cooldown = 0.0
        self.dash_cooldown = 0.0
        self.melee_cooldown = 0.0
        self.mistake_timer = 0.0
        self.last_health = MAX_HEALTH

    def act(self, obs_np, dt):
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.melee_cooldown = max(0.0, self.melee_cooldown - dt)
        self.mistake_timer -= dt

        state = self.parse_observation(obs_np)

        # aim at current enemy position with moderate (average) error
        aim_x = state["cx"] + state["dx"] + random.gauss(0, 42)
        aim_y = state["cy"] + state["dy"] + random.gauss(0, 42)

        # dodge enemy projectiles ~70% of the time (average reflexes)
        dodge_x, dodge_y = 0.0, 0.0
        danger = 0.0
        for b in state["enemy_projectiles"]:
            bspeed = math.hypot(b["vx"], b["vy"])
            if bspeed < 1:
                continue
            bdx, bdy = b["vx"] / bspeed, b["vy"] / bspeed
            t = (b["rel_x"] * bdx + b["rel_y"] * bdy) / bspeed
            if 0 < t < 1.2:
                cx = b["rel_x"] - b["vx"] * t
                cy = b["rel_y"] - b["vy"] * t
                perp = math.hypot(cx, cy)
                if perp < 50 and random.random() < 0.7:
                    rx, ry = -cx, -cy
                    r = math.hypot(rx, ry) or 1
                    f = (1.2 / (t + 0.1)) * (50.0 / max(r, 1.0))
                    dodge_x += rx / r * f
                    dodge_y += ry / r * f
                    danger += 1.0

        # range keeping: hover around mid distance
        target_dist = 400
        dist_err = state["dist"] - target_dist
        dir_ex = state["dx"] / max(state["dist"], 1.0)
        dir_ey = state["dy"] / max(state["dist"], 1.0)
        fx = dodge_x + dir_ex * (dist_err / 120.0)
        fy = dodge_y + dir_ey * (dist_err / 120.0)

        # occasional mistake: briefly move the wrong way
        if self.mistake_timer <= 0 and random.random() < 0.01:
            self.mistake_timer = random.uniform(0.2, 0.5)
        if self.mistake_timer > 0:
            fx = -fx * 0.5 + random.uniform(-0.3, 0.3)
            fy = -fy * 0.5 + random.uniform(-0.3, 0.3)

        fx, fy = self._avoid_walls(fx, fy, state["cx"], state["cy"])

        mx, my = self._to_discrete(fx, fy)

        # actions: fire on a loose, inconsistent cadence
        fire = False
        spell = 0
        attack = False
        dash = False
        if state["dist"] < 70 and self.melee_cooldown <= 0:
            attack = True
            self.melee_cooldown = 0.25
        elif self.fire_cooldown <= 0 and state["mana"] > 15 and state["dist"] < 650:
            fire = True
            spell = random.randint(0, 3)
            self.fire_cooldown = random.uniform(0.35, 0.55)
        if self.dash_cooldown <= 0 and danger > 1.0 and random.random() < 0.5:
            dash = True
            self.dash_cooldown = 0.3

        return mx, my, fire, dash, spell, aim_x, aim_y, attack


class ExpertBot(BaseBot):
    """Master player: aggressive, predictive, and punishes openings.
    Reads enemy stun/attack state to dash in and combo, leads aim by
    enemy velocity, and adapts pressure based on damage taken."""

    def __init__(self, screenw=SCREEN_WIDTH, screenh=SCREEN_HEIGHT):
        self.screenw = screenw
        self.screenh = screenh
        self.fire_cooldown = 0.0
        self.dash_cooldown = 0.0
        self.melee_cooldown = 0.0
        self.circle_dir = 1.0
        self.stance_timer = 0.0
        self.current_stance = "PRESSURE"
        self.vel_history = []
        self.last_health = MAX_HEALTH
        self.aggression = 1.0

    def act(self, obs_np, dt):
        if dt <= 0:
            dt = 0.016
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.melee_cooldown = max(0.0, self.melee_cooldown - dt)
        self.stance_timer -= dt

        state = self.parse_observation(obs_np)
        dist = state["dist"]

        # --- enemy velocity / acceleration estimation ---
        self.vel_history.append((state["enemy_vx"], state["enemy_vy"], dt))
        if len(self.vel_history) > 3:
            self.vel_history.pop(0)
        ea_x, ea_y = 0.0, 0.0
        if len(self.vel_history) >= 2:
            v2, v1 = self.vel_history[-1], self.vel_history[-2]
            ea_x = (v2[0] - v1[0]) / v2[2]
            ea_y = (v2[1] - v1[1]) / v2[2]

        # lead the aim: where the enemy will be when our spell arrives
        proj_speed = 500.0
        t_hit = dist / max(proj_speed, 1.0)
        pred_ex = state["cx"] + state["dx"] + state["enemy_vx"] * t_hit + 0.5 * ea_x * t_hit * t_hit
        pred_ey = state["cy"] + state["dy"] + state["enemy_vy"] * t_hit + 0.5 * ea_y * t_hit * t_hit
        aim_x = pred_ex + random.gauss(0, 4)   # master is precise
        aim_y = pred_ey + random.gauss(0, 4)

        # --- dodge enemy projectiles (hard commitment) ---
        dodge_x, dodge_y = 0.0, 0.0
        danger = 0.0
        imminent = 0
        for b in state["enemy_projectiles"]:
            bspeed = math.hypot(b["vx"], b["vy"])
            if bspeed < 1:
                continue
            bdx, bdy = b["vx"] / bspeed, b["vy"] / bspeed
            t = (b["rel_x"] * bdx + b["rel_y"] * bdy) / bspeed
            if 0 < t < 1.0:
                cx = b["rel_x"] - b["vx"] * t
                cy = b["rel_y"] - b["vy"] * t
                perp = math.hypot(cx, cy)
                if perp < 45:
                    imminent += 1
                    rx, ry = -cx, -cy
                    r = math.hypot(rx, ry) or 1
                    f = (1.8 / (t + 0.05)) * (45.0 / max(r, 1.0))
                    dodge_x += rx / r * f
                    dodge_y += ry / r * f
                    danger += 1.0 - t

        # --- damage-taken adaptation: back off if getting hit hard ---
        dmg_taken = self.last_health - state["health"]
        self.last_health = state["health"]
        self.aggression = max(0.7, min(1.4, self.aggression + (0.03 if dmg_taken < 0.5 else -0.06)))

        # --- stance selection (punish windows) ---
        enemy_stunned = state["enemy_stunned"]
        enemy_attacking = state["enemy_attacking"]
        if enemy_stunned:
            self.current_stance = "PUNISH"
            self.stance_timer = 0.5
        elif imminent >= 2:
            self.current_stance = "EVADE"
            self.stance_timer = 0.3
        elif self.stance_timer <= 0:
            if dist > 380 and state["mana"] >= 25:
                self.current_stance = "ASSAULT"
                self.stance_timer = random.uniform(0.8, 1.5)
            elif enemy_attacking and dist < 130:
                self.current_stance = "SPACE"
                self.stance_timer = 0.3
            else:
                self.current_stance = "PRESSURE"
                self.stance_timer = random.uniform(0.8, 1.6)
                if random.random() < 0.4:
                    self.circle_dir *= -1.0

        stance = self.current_stance
        target_dist = {"PUNISH": 90, "ASSAULT": 200, "PRESSURE": 260,
                       "SPACE": 320, "EVADE": 420}[stance]

        # --- movement: dodge + range control + circle strafe ---
        fx, fy = dodge_x, dodge_y
        dist_err = dist - target_dist
        dir_ex = state["dx"] / max(dist, 1.0)
        dir_ey = state["dy"] / max(dist, 1.0)
        fx += dir_ex * (dist_err / 100.0) * self.aggression
        fy += dir_ey * (dist_err / 100.0) * self.aggression
        strafe = 1.6 if stance in ("PRESSURE", "ASSAULT") else 0.6
        fx += -dir_ey * self.circle_dir * strafe
        fy += dir_ex * self.circle_dir * strafe

        fx, fy = self._avoid_walls(fx, fy, state["cx"], state["cy"])

        if stance != "EVADE":
            fx += random.uniform(-0.15, 0.15)
            fy += random.uniform(-0.15, 0.15)

        mx, my = self._to_discrete(fx, fy)

        # --- offensive actions ---
        fire = False
        spell = 0
        attack = False
        dash = False

        # melee when in range; always press the advantage on a stunned enemy
        if dist < 70 and self.melee_cooldown <= 0:
            if enemy_stunned or enemy_attacking or random.random() < 0.7:
                attack = True
                self.melee_cooldown = 0.18

        # ranged spell: zone at range, burst on a stunned enemy
        max_range = 780 if stance == "ASSAULT" else 650
        if self.fire_cooldown <= 0 and state["mana"] > 15 and dist < max_range:
            fire = True
            self.fire_cooldown = 0.26 if stance == "ASSAULT" else 0.34
            if enemy_stunned:
                spell = 2
            elif imminent >= 1:
                spell = 1
            elif dist > 450 and state["mana"] > 25:
                spell = random.randint(2, 3)
            else:
                spell = random.randint(0, 3)

        # dash: close for a punish, escape when overwhelmed, or engage from afar
        if self.dash_cooldown <= 0:
            if enemy_stunned and 90 < dist < 300:
                dash = True
                self.dash_cooldown = 0.28
            elif stance == "EVADE" and danger > 0.8:
                dash = True
                self.dash_cooldown = 0.28
            elif stance == "ASSAULT" and dist > 300 and state["mana"] >= 20:
                dash = True
                self.dash_cooldown = 0.3

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
