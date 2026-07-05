import math
import random
import sys
import os

sys.path.append(os.path.abspath("./build"))
import Game

class StaticTargetBot:
    def __init__(self, screenw, screenh):
        pass

    def act(self, obs_np, dt):
        return 0, 0, False, False, False, 400.0, 300.0

class EasyBot:
    def __init__(self, screenw, screenh, player_speed=200.0, bullet_speed=750.0, aim_noise_std=40.0):
        self.screenw = screenw
        self.screenh = screenh
        self.player_speed = player_speed
        self.bullet_speed = bullet_speed
        self.aim_noise_std = aim_noise_std

        self.fire_cooldown = 0.0
        self.dash_cooldown = 0.0

    def act(self, obs_np, dt):
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

        ammo_ratio = obs_np[1]
        is_reloading = obs_np[2] > 0.5
        is_dashing = obs_np[3] > 0.5

        x = obs_np[4] * self.screenw
        y = obs_np[5] * self.screenh
        enemy_x = x + obs_np[9] * self.screenw
        enemy_y = y + obs_np[10] * self.screenh

        active_bullets = []
        for j in range(6):
            idx = 43 + j * 5
            if obs_np[idx] > 0.5:
                bx = x + obs_np[idx+1] * self.screenw
                by = y + obs_np[idx+2] * self.screenh
                bvx = obs_np[idx+3] * self.bullet_speed
                bvy = obs_np[idx+4] * self.bullet_speed
                active_bullets.append((bx, by, bvx, bvy))

        aim_x = enemy_x + random.gauss(0, self.aim_noise_std)
        aim_y = enemy_y + random.gauss(0, self.aim_noise_std)

        dodge_x, dodge_y = 0.0, 0.0
        bullet_nearby = False

        for bx, by, bvx, bvy in active_bullets:
            dx, dy = x - bx, y - by
            dist = math.hypot(dx, dy)
            bspeed = math.hypot(bvx, bvy)
            if bspeed < 1: continue

            bdx, bdy = bvx / bspeed, bvy / bspeed
            toward = (dx * bdx + dy * bdy) / max(dist, 1.0)

            if toward > 0 and dist < 350:
                bullet_nearby = True
                urgency = max(0.0, 1.0 - dist / 350.0)
                dodge_x += -bdy * urgency
                dodge_y += bdx * urgency

        dodge_mag = math.hypot(dodge_x, dodge_y)
        if dodge_mag > 0.3:
            mx = 1 if dodge_x > 0.3 else -1 if dodge_x < -0.3 else 0
            my = 1 if dodge_y > 0.3 else -1 if dodge_y < -0.3 else 0
        else:
            dx_e, dy_e = enemy_x - x, enemy_y - y
            circle_x, circle_y = -dy_e, dx_e
            cmag = math.hypot(circle_x, circle_y)
            if cmag > 1:
                circle_x /= cmag; circle_y /= cmag
            mx = 1 if circle_x > 0.3 else -1 if circle_x < -0.3 else 0
            my = 1 if circle_y > 0.3 else -1 if circle_y < -0.3 else 0

        dash = False
        if bullet_nearby and self.dash_cooldown <= 0.0 and random.random() < 0.3:
            dash = True
            self.dash_cooldown = 0.6

        reload = False
        dist_to_enemy = math.hypot(enemy_x - x, enemy_y - y)

        if not is_reloading:
            if ammo_ratio <= 0.0 or (ammo_ratio <= 2/6 and dist_to_enemy > 500 and random.random() < 0.02):
                reload = True

        self.fire_cooldown -= dt
        fire = False
        if self.fire_cooldown <= 0 and dist_to_enemy < 600 and ammo_ratio > 0 and not is_reloading and not is_dashing and not dash:
            fire = True
            self.fire_cooldown = 0.4

        return mx, my, fire, dash, reload, aim_x, aim_y

class HardenedBot:
    def __init__(self, screenw, screenh, player_speed=200.0, bullet_speed=750.0, aim_noise_std=15.0):
        self.screenw = screenw
        self.screenh = screenh
        self.player_speed = player_speed
        self.bullet_speed = bullet_speed
        self.aim_noise_std = aim_noise_std

        self.fire_cooldown = 0.0
        self.dash_cooldown = 0.0
        self.circle_dir = 1
        self.dir_timer = random.uniform(1.0, 3.0)

    def act(self, obs_np, dt):
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

        ammo_ratio = obs_np[1]
        is_reloading = obs_np[2] > 0.5
        is_dashing = obs_np[3] > 0.5

        x = obs_np[4] * self.screenw
        y = obs_np[5] * self.screenh
        enemy_x = x + obs_np[9] * self.screenw
        enemy_y = y + obs_np[10] * self.screenh

        ev_x = obs_np[11] * self.player_speed
        ev_y = obs_np[12] * self.player_speed

        dist_to_enemy = math.hypot(enemy_x - x, enemy_y - y)

        active_bullets = []
        for j in range(6):
            idx = 43 + j * 5
            if obs_np[idx] > 0.5:
                bx = x + obs_np[idx+1] * self.screenw
                by = y + obs_np[idx+2] * self.screenh
                bvx = obs_np[idx+3] * self.bullet_speed
                bvy = obs_np[idx+4] * self.bullet_speed
                active_bullets.append((bx, by, bvx, bvy))

        time_to_impact = dist_to_enemy / max(self.bullet_speed, 1.0)
        aim_x = enemy_x + (ev_x * time_to_impact) + random.gauss(0, self.aim_noise_std)
        aim_y = enemy_y + (ev_y * time_to_impact) + random.gauss(0, self.aim_noise_std)

        dodge_x, dodge_y = 0.0, 0.0
        danger_level = 0.0

        for bx, by, bvx, bvy in active_bullets:
            bspeed = math.hypot(bvx, bvy)
            if bspeed < 1: continue

            dx, dy = x - bx, y - by
            dist = math.hypot(dx, dy)
            bdx, bdy = bvx / bspeed, bvy / bspeed
            forward_dist = dx * bdx + dy * bdy

            if forward_dist > -20 and dist < 400:
                perp_dist = dx * bdy - dy * bdx
                if abs(perp_dist) < 35.0:
                    urgency = max(0.0, 1.0 - dist / 400.0)
                    escape_dir = 1.0 if perp_dist > 0 else -1.0
                    dodge_x += escape_dir * -bdy * urgency * 2.0
                    dodge_y += escape_dir * bdx * urgency * 2.0
                    danger_level += urgency

        self.dir_timer -= dt
        if self.dir_timer <= 0:
            self.circle_dir *= -1
            self.dir_timer = random.uniform(1.0, 3.5)

        move_x, move_y = 0.0, 0.0
        dodge_mag = math.hypot(dodge_x, dodge_y)

        if dodge_mag > 0.2:
            move_x, move_y = dodge_x, dodge_y
        else:
            dx_e, dy_e = enemy_x - x, enemy_y - y
            dir_ex = dx_e / max(dist_to_enemy, 1.0)
            dir_ey = dy_e / max(dist_to_enemy, 1.0)

            circle_x = -dir_ey * self.circle_dir
            circle_y = dir_ex * self.circle_dir

            dist_error = dist_to_enemy - 350.0
            kite_x = dir_ex * (dist_error / 150.0)
            kite_y = dir_ey * (dist_error / 150.0)

            move_x = circle_x + kite_x
            move_y = circle_y + kite_y

        margin = 100.0
        near_wall = x < margin or x > self.screenw - margin or y < margin or y > self.screenh - margin
        if x < margin: move_x += 2.0 * (margin - x) / margin
        elif x > self.screenw - margin: move_x -= 2.0 * (x - (self.screenw - margin)) / margin
        if y < margin: move_y += 2.0 * (margin - y) / margin
        elif y > self.screenh - margin: move_y -= 2.0 * (y - (self.screenh - margin)) / margin

        final_mag = math.hypot(move_x, move_y)
        if final_mag > 1.0:
            move_x /= final_mag; move_y /= final_mag

        mx = 1 if move_x > 0.2 else -1 if move_x < -0.2 else 0
        my = 1 if move_y > 0.2 else -1 if move_y < -0.2 else 0

        dash = False
        if self.dash_cooldown <= 0.0:
            if (danger_level > 1.2) or (near_wall and danger_level > 0.4):
                dash = True
                self.dash_cooldown = 0.6

        reload = False
        if not is_reloading:
            if ammo_ratio <= 0.0 or (ammo_ratio <= 2/6 and dist_to_enemy > 450 and danger_level == 0):
                reload = True

        self.fire_cooldown -= dt
        fire = False
        if self.fire_cooldown <= 0 and dist_to_enemy < 700 and ammo_ratio > 0 and not is_reloading and not is_dashing and not dash:
            fire = True
            self.fire_cooldown = 0.35

        return mx, my, fire, dash, reload, aim_x, aim_y

class MasterpieceBot:
    def __init__(self, screenw, screenh, player_speed=200.0, bullet_speed=750.0, aim_noise_std=8.0):
        self.screenw = screenw
        self.screenh = screenh
        self.player_speed = player_speed
        self.bullet_speed = bullet_speed
        self.aim_noise_std = aim_noise_std

        self.fire_cooldown = 0.0
        self.dash_cooldown = 0.0

        self.vel_history = []
        self.circle_dir = 1.0
        self.stance_timer = 0.0
        self.current_stance = "SKIRMISH"

    def act(self, obs_np, dt):
        if dt <= 0: dt = 0.016
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

        ammo_ratio = obs_np[1]
        is_reloading = obs_np[2] > 0.5
        is_dashing = obs_np[3] > 0.5

        x = obs_np[4] * self.screenw
        y = obs_np[5] * self.screenh
        enemy_x = x + obs_np[9] * self.screenw
        enemy_y = y + obs_np[10] * self.screenh

        ev_x = obs_np[11] * self.player_speed
        ev_y = obs_np[12] * self.player_speed
        dist_to_enemy = math.hypot(enemy_x - x, enemy_y - y)

        self.vel_history.append((ev_x, ev_y, dt))
        if len(self.vel_history) > 3: self.vel_history.pop(0)

        ea_x, ea_y = 0.0, 0.0
        if len(self.vel_history) >= 2:
            v2, v1 = self.vel_history[-1], self.vel_history[-2]
            ea_x = (v2[0] - v1[0]) / v2[2]
            ea_y = (v2[1] - v1[1]) / v2[2]

        time_to_impact = dist_to_enemy / max(self.bullet_speed, 1.0)
        pred_ex = enemy_x + (ev_x * time_to_impact) + (0.5 * ea_x * (time_to_impact ** 2))
        pred_ey = enemy_y + (ev_y * time_to_impact) + (0.5 * ea_y * (time_to_impact ** 2))
        aim_x = pred_ex + random.gauss(0, self.aim_noise_std)
        aim_y = pred_ey + random.gauss(0, self.aim_noise_std)

        active_bullets = []
        for j in range(6):
            idx = 43 + j * 5
            if obs_np[idx] > 0.5:
                bx = x + obs_np[idx+1] * self.screenw
                by = y + obs_np[idx+2] * self.screenh
                bvx = obs_np[idx+3] * self.bullet_speed
                bvy = obs_np[idx+4] * self.bullet_speed
                active_bullets.append((bx, by, bvx, bvy))

        imminent_threats = 0
        critical_iframe_window = False
        bullet_forces_x, bullet_forces_y = 0.0, 0.0

        for bx, by, bvx, bvy in active_bullets:
            bspeed = math.hypot(bvx, bvy)
            if bspeed < 1.0: continue

            dx, dy = x - bx, y - by
            bdx, bdy = bvx / bspeed, bvy / bspeed
            t_closest = (dx * bdx + dy * bdy) / bspeed

            if 0 < t_closest < 1.2:
                closest_x = bx + bvx * t_closest
                closest_y = by + bvy * t_closest
                perp_dist = math.hypot(x - closest_x, y - closest_y)

                if perp_dist < 45.0:
                    imminent_threats += 1
                    if t_closest < 0.18:
                        critical_iframe_window = True

                    repel_dir_x, repel_dir_y = x - closest_x, y - closest_y
                    r_dist = math.hypot(repel_dir_x, repel_dir_y)
                    if r_dist == 0: r_dist = 1.0
                    force_mag = (1.5 / (t_closest + 0.05)) * (45.0 / max(r_dist, 1.0))
                    bullet_forces_x += (repel_dir_x / r_dist) * force_mag
                    bullet_forces_y += (repel_dir_y / r_dist) * force_mag

        self.stance_timer -= dt
        if self.stance_timer <= 0:
            if imminent_threats >= 2:
                self.current_stance = "EVADE"
                self.stance_timer = 0.4
            elif dist_to_enemy > 450 and ammo_ratio >= 5/6:
                self.current_stance = "ASSAULT"
                self.stance_timer = random.uniform(1.0, 1.8)
            else:
                self.current_stance = "SKIRMISH"
                self.stance_timer = random.uniform(1.0, 2.5)
                if random.random() < 0.5: self.circle_dir *= -1.0

        fx, fy = bullet_forces_x, bullet_forces_y
        target_dist, speed_modifier = 350.0, 1.0

        if self.current_stance == "ASSAULT":
            target_dist, speed_modifier = 200.0, 1.25
        elif self.current_stance == "EVADE":
            target_dist, speed_modifier = 480.0, 0.95

        dx_e, dy_e = enemy_x - x, enemy_y - y
        dir_ex = dx_e / max(dist_to_enemy, 1.0)
        dir_ey = dy_e / max(dist_to_enemy, 1.0)

        dist_error = dist_to_enemy - target_dist
        fx += dir_ex * (dist_error / 100.0) * speed_modifier
        fy += dir_ey * (dist_error / 100.0) * speed_modifier
        fx += -dir_ey * self.circle_dir * 1.4 * speed_modifier
        fy += dir_ex * self.circle_dir * 1.4 * speed_modifier

        w_margin, w_force = 120.0, 3.0
        if x < w_margin: fx += w_force * ((w_margin - x) / w_margin) ** 2
        elif x > self.screenw - w_margin: fx -= w_force * ((x - (self.screenw - w_margin)) / w_margin) ** 2
        if y < w_margin: fy += w_force * ((w_margin - y) / w_margin) ** 2
        elif y > self.screenh - w_margin: fy -= w_force * ((y - (self.screenh - w_margin)) / w_margin) ** 2

        if self.current_stance != "EVADE":
            fx += random.uniform(-0.2, 0.2); fy += random.uniform(-0.2, 0.2)

        f_mag = math.hypot(fx, fy)
        if f_mag > 1.0: fx /= f_mag; fy /= f_mag
        mx = 1 if fx > 0.22 else -1 if fx < -0.22 else 0
        my = 1 if fy > 0.22 else -1 if fy < -0.22 else 0

        dash = False
        if self.dash_cooldown <= 0.0:
            if critical_iframe_window:
                dash = True
            elif self.current_stance == "ASSAULT" and dist_to_enemy > 450.0 and ammo_ratio >= 3/6:
                dash = True
            if dash: self.dash_cooldown = 0.6

        reload = False
        if not is_reloading:
            if ammo_ratio == 0.0: reload = True
            elif ammo_ratio <= 2/6 and imminent_threats == 0 and self.current_stance != "ASSAULT": reload = True

        self.fire_cooldown -= dt
        fire = False
        max_viable_range = 750.0 if self.current_stance == "ASSAULT" else 600.0

        if self.fire_cooldown <= 0 and dist_to_enemy < max_viable_range and ammo_ratio > 0 and not is_reloading and not is_dashing and not dash:
            fire = True
            self.fire_cooldown = 0.28 if self.current_stance == "ASSAULT" else 0.36

        return mx, my, fire, dash, reload, aim_x, aim_y

class Human():
    def __init__(self, screenw, screenh):
        pass
    def act(self, obs, dt):
        return Game.get_human_intent(Game.poll_events())

BOTS = {
    "easy": EasyBot,
    "static": StaticTargetBot,
    "hardened": HardenedBot,
    "masterpiece": MasterpieceBot,
    "human": Human,
}
