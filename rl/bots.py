import math
import random
import sys
import os

sys.path.append(os.path.abspath("./build"))
import Game
class EasyCodedBot:
    def __init__(self, screenw, screenh, aim_noise_std=40.0):

        self.screenw = screenw
        self.screenh = screenh

        self.aim_noise_std = aim_noise_std

        self.fire_cooldown = 0.0

    def act(self, obs_np, dt):
        x = obs_np[2]
        y = obs_np[3]

        enemy_x = obs_np[4]
        enemy_y = obs_np[5]
        enemy_bullets = obs_np[34:46].reshape(-1, 2)
        enemy_bullet_vels = obs_np[58:70].reshape(-1, 2)

        aim_x = enemy_x + random.gauss(0, self.aim_noise_std)
        aim_y = enemy_y + random.gauss(0, self.aim_noise_std)

        dodge_x, dodge_y = 0.0, 0.0

        for i in range(6):
            bx, by = enemy_bullets[i]
            if bx < 0 or by < 0:
                continue

            bvx, bvy = enemy_bullet_vels[i]

            dx = x - bx
            dy = y - by

            dist = math.hypot(dx, dy)

            bspeed = math.hypot(bvx, bvy)

            if bspeed < 1:
                continue

            bdx = bvx / bspeed
            bdy = bvy / bspeed

            toward = (dx * bdx + dy * bdy) / max(dist, 1.0)

            if toward > 0 and dist < 350:
                perp_x = -bdy
                perp_y = bdx
                urgency = max(0.0, 1.0 - dist / 350.0)
                dodge_x += perp_x * urgency
                dodge_y += perp_y * urgency

        dodge_mag = math.hypot(dodge_x, dodge_y)

        if dodge_mag > 0.3:
            mx = 1 if dodge_x > 0.3 else -1 if dodge_x < -0.3 else 0
            my = 1 if dodge_y > 0.3 else -1 if dodge_y < -0.3 else 0
        else:
            dx_e = enemy_x - x
            dy_e = enemy_y - y

            circle_x = -dy_e
            circle_y = dx_e
            cmag = math.hypot(circle_x, circle_y)

            if cmag > 1:
                circle_x /= cmag
                circle_y /= cmag

            mx = 1 if circle_x > 0.3 else -1 if circle_x < -0.3 else 0
            my = 1 if circle_y > 0.3 else -1 if circle_y < -0.3 else 0

        self.fire_cooldown -= dt
        dist_to_enemy = math.hypot(enemy_x - x, enemy_y - y)

        if self.fire_cooldown <= 0 and dist_to_enemy < 600:
            fire = True
            self.fire_cooldown = 0.4
        else:
            fire = False

        return mx, my, fire, aim_x, aim_y

class StaticTargetBot:
    def __init__(self, screenw, screenh):
        pass

    def act(self, obs_np, dt):
        return 0, 0, False, 400.0, 300.0

class HardenedBot:
    def __init__(self, screenw, screenh, aim_noise_std=15.0):
        self.screenw = screenw
        self.screenh = screenh
        self.aim_noise_std = aim_noise_std
        self.fire_cooldown = 0.0
        
        self.circle_dir = 1
        self.dir_timer = random.uniform(1.0, 3.0)
        self.last_enemy_pos = None

    def act(self, obs_np, dt):
        x = obs_np[2]
        y = obs_np[3]
        enemy_x = obs_np[4]
        enemy_y = obs_np[5]

        enemy_bullets = obs_np[34:46].reshape(-1, 2)
        enemy_bullet_vels = obs_np[58:70].reshape(-1, 2)

        if self.last_enemy_pos and dt > 0:
            ev_x = (enemy_x - self.last_enemy_pos[0]) / dt
            ev_y = (enemy_y - self.last_enemy_pos[1]) / dt
        else:
            ev_x, ev_y = 0.0, 0.0
            
        self.last_enemy_pos = (enemy_x, enemy_y)

        dist_to_enemy = math.hypot(enemy_x - x, enemy_y - y)
        time_to_impact = dist_to_enemy / 800.0
        
        aim_x = enemy_x + (ev_x * time_to_impact) + random.gauss(0, self.aim_noise_std)
        aim_y = enemy_y + (ev_y * time_to_impact) + random.gauss(0, self.aim_noise_std)

        dodge_x, dodge_y = 0.0, 0.0
        for i in range(6):
            bx, by = enemy_bullets[i]
            if bx < 0 or by < 0: continue
            
            bvx, bvy = enemy_bullet_vels[i]
            bspeed = math.hypot(bvx, bvy)
            if bspeed < 1: continue
                
            dx = x - bx
            dy = y - by
            dist = math.hypot(dx, dy)
            
            bdx = bvx / bspeed
            bdy = bvy / bspeed
            
            forward_dist = dx * bdx + dy * bdy 
            
            if forward_dist > -20 and dist < 400:
                perp_dist = dx * bdy - dy * bdx
                
                if abs(perp_dist) < 35.0:
                    urgency = max(0.0, 1.0 - dist / 400.0)
                    escape_dir = 1.0 if perp_dist > 0 else -1.0
                    dodge_x += escape_dir * -bdy * urgency * 2.0
                    dodge_y += escape_dir * bdx * urgency * 2.0

        self.dir_timer -= dt
        if self.dir_timer <= 0:
            self.circle_dir *= -1
            self.dir_timer = random.uniform(1.0, 3.5)

        move_x, move_y = 0.0, 0.0
        dodge_mag = math.hypot(dodge_x, dodge_y)
        
        if dodge_mag > 0.2:
            move_x, move_y = dodge_x, dodge_y
        else:
            dx_e = enemy_x - x
            dy_e = enemy_y - y
            
            dir_e_x = dx_e / max(dist_to_enemy, 1.0)
            dir_e_y = dy_e / max(dist_to_enemy, 1.0)
            
            circle_x = -dir_e_y * self.circle_dir
            circle_y = dir_e_x * self.circle_dir
            
            optimal_dist = 350.0
            dist_error = dist_to_enemy - optimal_dist
            kite_x = dir_e_x * (dist_error / 150.0)
            kite_y = dir_e_y * (dist_error / 150.0)
            
            move_x = circle_x + kite_x
            move_y = circle_y + kite_y

        margin = 100.0
        repel_strength = 2.0
        if x < margin: move_x += repel_strength * (margin - x) / margin
        elif x > self.screenw - margin: move_x -= repel_strength * (x - (self.screenw - margin)) / margin
        
        if y < margin: move_y += repel_strength * (margin - y) / margin
        elif y > self.screenh - margin: move_y -= repel_strength * (y - (self.screenh - margin)) / margin

        final_mag = math.hypot(move_x, move_y)
        if final_mag > 1.0:
            move_x /= final_mag
            move_y /= final_mag

        mx = 1 if move_x > 0.2 else -1 if move_x < -0.2 else 0
        my = 1 if move_y > 0.2 else -1 if move_y < -0.2 else 0

        self.fire_cooldown -= dt
        if self.fire_cooldown <= 0 and dist_to_enemy < 700:
            fire = True
            self.fire_cooldown = 0.35
        else:
            fire = False

        return mx, my, fire, aim_x, aim_y

class MasterpieceBot:
    def __init__(self, screenw, screenh, aim_noise_std=10.0):
        self.screenw = screenw
        self.screenh = screenh
        self.aim_noise_std = aim_noise_std
        self.fire_cooldown = 0.0

        self.enemy_history = []
        self.circle_dir = 1.0
        self.stance_timer = 0.0
        self.current_stance = "SKIRMISH"
        self._last_self_x = 0.0
        self._last_self_y = 0.0

    def _clamp(self, value, minimum, maximum):
        return minimum if value < minimum else maximum if value > maximum else value

    def _update_motion_history(self, enemy_x, enemy_y, dt):
        self.enemy_history.append((enemy_x, enemy_y, dt))
        if len(self.enemy_history) > 4:
            self.enemy_history.pop(0)

        ev_x, ev_y = 0.0, 0.0
        ea_x, ea_y = 0.0, 0.0

        if len(self.enemy_history) >= 2:
            p2 = self.enemy_history[-1]
            p1 = self.enemy_history[-2]
            ev_x = (p2[0] - p1[0]) / max(p2[2], 1e-6)
            ev_y = (p2[1] - p1[1]) / max(p2[2], 1e-6)

        if len(self.enemy_history) >= 3:
            p3 = self.enemy_history[-1]
            p2 = self.enemy_history[-2]
            p1 = self.enemy_history[-3]
            v2_x = (p3[0] - p2[0]) / max(p3[2], 1e-6)
            v2_y = (p3[1] - p2[1]) / max(p3[2], 1e-6)
            v1_x = (p2[0] - p1[0]) / max(p2[2], 1e-6)
            v1_y = (p2[1] - p1[1]) / max(p2[2], 1e-6)
            ea_x = (v2_x - v1_x) / max(p3[2], 1e-6)
            ea_y = (v2_y - v1_y) / max(p3[2], 1e-6)

        return ev_x, ev_y, ea_x, ea_y

    def _select_stance(self, health, enemy_health, dist_to_enemy, imminent_threats, dt):
        self.stance_timer -= dt
        if self.stance_timer > 0:
            return

        health_bias = self._clamp((health - enemy_health) / 35.0, -1.0, 1.0)

        if imminent_threats >= 2 or (health < 30 and enemy_health >= health):
            self.current_stance = "EVADE"
            self.stance_timer = 0.35 if imminent_threats >= 2 else 0.6
            return

        if health_bias > 0.25 and dist_to_enemy < 520:
            self.current_stance = "ASSAULT"
            self.stance_timer = random.uniform(0.8, 1.4)
            return

        if health_bias < -0.25 and dist_to_enemy > 280:
            self.current_stance = "SKIRMISH"
            self.stance_timer = random.uniform(0.9, 1.8)
            self.circle_dir *= -1.0 if random.random() < 0.55 else 1.0
            return

        if dist_to_enemy > 470 and random.random() < 0.45:
            self.current_stance = "ASSAULT"
            self.stance_timer = random.uniform(0.9, 1.7)
        else:
            self.current_stance = "SKIRMISH"
            self.stance_timer = random.uniform(1.2, 2.6)
            if random.random() < 0.35:
                self.circle_dir *= -1.0

    def _predict_aim(self, x, y, enemy_x, enemy_y, ev_x, ev_y, dist_to_enemy, health, enemy_health):
        health_bias = self._clamp((health - enemy_health) / 35.0, -1.0, 1.0)
        bullet_speed = 750.0
        rel_x = enemy_x - x
        rel_y = enemy_y - y

        a = (ev_x * ev_x) + (ev_y * ev_y) - (bullet_speed * bullet_speed)
        b = 2.0 * ((rel_x * ev_x) + (rel_y * ev_y))
        c = (rel_x * rel_x) + (rel_y * rel_y)

        lead_time = 0.0
        if abs(a) < 1e-6:
            if abs(b) > 1e-6:
                lead_time = -c / b
        else:
            discriminant = (b * b) - (4.0 * a * c)
            if discriminant >= 0.0:
                sqrt_disc = math.sqrt(discriminant)
                t1 = (-b - sqrt_disc) / (2.0 * a)
                t2 = (-b + sqrt_disc) / (2.0 * a)
                candidates = [t for t in (t1, t2) if t > 0.0]
                if candidates:
                    lead_time = min(candidates)

        if lead_time <= 0.0:
            lead_time = dist_to_enemy / bullet_speed

        lead_time = self._clamp(lead_time, 0.03, 1.3)
        lead_time *= 0.98 if health_bias > 0 else 1.01

        if dist_to_enemy < 180:
            lead_time *= 0.45
        elif dist_to_enemy < 350:
            lead_time *= 0.75

        pred_ex = enemy_x + (ev_x * lead_time)
        pred_ey = enemy_y + (ev_y * lead_time)

        aim_noise = self.aim_noise_std
        if dist_to_enemy < 180:
            aim_noise *= 0.05
        elif dist_to_enemy < 320:
            aim_noise *= 0.1
        elif dist_to_enemy < 500:
            aim_noise *= 0.18
        else:
            aim_noise *= 0.28

        if health_bias < 0:
            aim_noise *= 0.7
        elif health_bias > 0.5:
            aim_noise *= 1.0

        if self.current_stance == "ASSAULT":
            aim_noise *= 0.6
        elif self.current_stance == "EVADE":
            aim_noise *= 0.8

        aim_x = pred_ex + random.gauss(0, aim_noise)
        aim_y = pred_ey + random.gauss(0, aim_noise)
        return self._clamp(aim_x, 0.0, self.screenw), self._clamp(aim_y, 0.0, self.screenh)

    def act(self, obs_np, dt):
        if dt <= 0:
            dt = 0.016

        health = obs_np[0]
        enemy_health = obs_np[1]
        x, y = obs_np[2], obs_np[3]
        enemy_x, enemy_y = obs_np[4], obs_np[5]
        own_vx, own_vy = obs_np[6], obs_np[7]
        enemy_vx_obs, enemy_vy_obs = obs_np[8], obs_np[9]
        dist_to_enemy = math.hypot(enemy_x - x, enemy_y - y)

        enemy_bullets = obs_np[34:46].reshape(-1, 2)
        enemy_bullet_vels = obs_np[58:70].reshape(-1, 2)

        ev_x, ev_y, ea_x, ea_y = self._update_motion_history(enemy_x, enemy_y, dt)
        ev_x = 0.45 * ev_x + 0.55 * enemy_vx_obs
        ev_y = 0.45 * ev_y + 0.55 * enemy_vy_obs
        ea_x *= 0.75
        ea_y *= 0.75

        if abs(enemy_vx_obs) < 0.5:
            ev_x *= 0.5
        if abs(enemy_vy_obs) < 0.5:
            ev_y *= 0.5

        aim_x, aim_y = self._predict_aim(x, y, enemy_x, enemy_y, ev_x, ev_y, dist_to_enemy, health, enemy_health)

        imminent_threats = 0
        bullet_forces_x, bullet_forces_y = 0.0, 0.0

        for i in range(6):
            bx, by = enemy_bullets[i]
            if bx < 0 or by < 0: continue
            
            bvx, bvy = enemy_bullet_vels[i]
            bspeed = math.hypot(bvx, bvy)
            if bspeed < 1.0: continue

            dx, dy = x - bx, y - by
            bdx, bdy = bvx / bspeed, bvy / bspeed

            t_closest = (dx * bdx + dy * bdy) / bspeed

            if t_closest > 0 and t_closest < 1.2:
                closest_x = bx + bvx * t_closest
                closest_y = by + bvy * t_closest
                perp_dist = math.hypot(x - closest_x, y - closest_y)

                if perp_dist < 45.0:
                    imminent_threats += 1
                    repel_dir_x = x - closest_x
                    repel_dir_y = y - closest_y
                    r_dist = math.hypot(repel_dir_x, repel_dir_y)
                    if r_dist == 0: r_dist = 1.0

                    force_mag = (1.5 / (t_closest + 0.05)) * (45.0 / max(r_dist, 1.0))
                    bullet_forces_x += (repel_dir_x / r_dist) * force_mag
                    bullet_forces_y += (repel_dir_y / r_dist) * force_mag

        self._select_stance(health, enemy_health, dist_to_enemy, imminent_threats, dt)

        fx, fy = 0.0, 0.0

        fx += bullet_forces_x
        fy += bullet_forces_y

        health_bias = self._clamp((health - enemy_health) / 35.0, -1.0, 1.0)
        target_dist = 340.0 - (55.0 * health_bias)
        speed_modifier = 1.0

        if self.current_stance == "ASSAULT":
            target_dist = 220.0 if health_bias >= 0 else 250.0
            speed_modifier = 1.25
        elif self.current_stance == "EVADE":
            target_dist = 510.0
            speed_modifier = 0.82

        dx_e = enemy_x - x
        dy_e = enemy_y - y

        dir_ex = dx_e / max(dist_to_enemy, 1.0)
        dir_ey = dy_e / max(dist_to_enemy, 1.0)

        velocity_push_x = -own_vx / 220.0
        velocity_push_y = -own_vy / 220.0

        dist_error = dist_to_enemy - target_dist
        fx += dir_ex * (dist_error / 120.0) * speed_modifier
        fy += dir_ey * (dist_error / 120.0) * speed_modifier

        orbit_strength = 1.15 if self.current_stance == "ASSAULT" else 1.35
        fx += -dir_ey * self.circle_dir * orbit_strength * speed_modifier
        fy += dir_ex * self.circle_dir * orbit_strength * speed_modifier

        fx += velocity_push_x
        fy += velocity_push_y

        if self.current_stance == "ASSAULT":
            fx += dir_ex * 0.25
            fy += dir_ey * 0.25
        elif self.current_stance == "EVADE":
            fx -= dir_ex * 0.35
            fy -= dir_ey * 0.35

        w_margin = 120.0
        w_force = 2.5
        if x < w_margin: fx += w_force * ((w_margin - x) / w_margin) ** 2
        elif x > self.screenw - w_margin: fx -= w_force * ((x - (self.screenw - w_margin)) / w_margin) ** 2
        
        if y < w_margin: fy += w_force * ((w_margin - y) / w_margin) ** 2
        elif y > self.screenh - w_margin: fy -= w_force * ((y - (self.screenh - w_margin)) / w_margin) ** 2

        if self.current_stance != "EVADE":
            fx += random.uniform(-0.25, 0.25)
            fy += random.uniform(-0.25, 0.25)

        f_mag = math.hypot(fx, fy)
        if f_mag > 1.0:
            fx /= f_mag
            fy /= f_mag

        mx = 1 if fx > 0.18 else -1 if fx < -0.18 else 0
        my = 1 if fy > 0.18 else -1 if fy < -0.18 else 0

        self.fire_cooldown -= dt
        max_viable_range = 780.0 if self.current_stance == "ASSAULT" else 640.0
        if health < 25:
            max_viable_range = 560.0
        elif health_bias > 0.5:
            max_viable_range = 820.0

        if self.fire_cooldown <= 0 and dist_to_enemy < max_viable_range:
            fire = True
            self.fire_cooldown = 0.24 if self.current_stance == "ASSAULT" else 0.34 if self.current_stance == "SKIRMISH" else 0.42
        else:
            fire = False

        return mx, my, fire, aim_x, aim_y

class Human():
    def __init__(self, screenw, screenh):
        pass
    def act(self, obs, dt):
        return Game.get_human_intent(Game.poll_events())

BOTS = {
    "easy": EasyCodedBot,
    "static": StaticTargetBot,
    "hardened": HardenedBot,
    "masterpiece": MasterpieceBot,
    "human": Human,
}
