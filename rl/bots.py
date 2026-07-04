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
        return 0, 0, False, 400.0, 300.0

class EasyCodedBot:
    def __init__(self, screenw, screenh, aim_noise_std=40.0):
        self.screenw = screenw
        self.screenh = screenh
        self.aim_noise_std = aim_noise_std
        self.fire_cooldown = 0.0
        
        # New States
        self.ammo = 10
        self.dash_cooldown = 0.0
        self.reload_timer = 0.0

    def act(self, obs_np, dt):
        # Update Timers
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.reload_timer = max(0.0, self.reload_timer - dt)

        x, y = obs_np[2], obs_np[3]
        enemy_x, enemy_y = obs_np[4], obs_np[5]
        enemy_bullets = obs_np[34:46].reshape(-1, 2)
        enemy_bullet_vels = obs_np[58:70].reshape(-1, 2)

        aim_x = enemy_x + random.gauss(0, self.aim_noise_std)
        aim_y = enemy_y + random.gauss(0, self.aim_noise_std)

        dodge_x, dodge_y = 0.0, 0.0
        bullet_nearby = False

        for i in range(6):
            bx, by = enemy_bullets[i]
            if bx < 0 or by < 0: continue
            bvx, bvy = enemy_bullet_vels[i]
            dx, dy = x - bx, y - by
            dist = math.hypot(dx, dy)
            bspeed = math.hypot(bvx, bvy)
            if bspeed < 1: continue
            
            bdx, bdy = bvx / bspeed, bvy / bspeed
            toward = (dx * bdx + dy * bdy) / max(dist, 1.0)
            
            if toward > 0 and dist < 350:
                bullet_nearby = True
                perp_x, perp_y = -bdy, bdx
                urgency = max(0.0, 1.0 - dist / 350.0)
                dodge_x += perp_x * urgency
                dodge_y += perp_y * urgency

        # Movement directional intent
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

        # Dash Logic (Panic dash if bullet is very close)
        dash = False
        if bullet_nearby and self.dash_cooldown <= 0.0 and random.random() < 0.3:
            dash = True
            self.dash_cooldown = 0.6

        # Reload Logic
        reload = False
        dist_to_enemy = math.hypot(enemy_x - x, enemy_y - y)
        if self.reload_timer <= 0.0:
            if self.ammo <= 0 or (self.ammo < 10 and dist_to_enemy > 550 and random.random() < 0.02):
                reload = True
                self.ammo = 10
                self.reload_timer = 1.2

        # Firing Logic
        self.fire_cooldown -= dt
        fire = False
        if self.fire_cooldown <= 0 and dist_to_enemy < 600 and self.ammo > 0 and self.reload_timer <= 0 and not dash:
            fire = True
            self.ammo -= 1
            self.fire_cooldown = 0.4

        return mx, my, fire, dash, reload, aim_x, aim_y

class HardenedBot:
    def __init__(self, screenw, screenh, aim_noise_std=15.0):
        self.screenw = screenw
        self.screenh = screenh
        self.aim_noise_std = aim_noise_std
        self.fire_cooldown = 0.0
        
        self.circle_dir = 1
        self.dir_timer = random.uniform(1.0, 3.0)
        self.last_enemy_pos = None

        # Combat Resources
        self.ammo = 10
        self.dash_cooldown = 0.0
        self.reload_timer = 0.0

    def act(self, obs_np, dt):
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.reload_timer = max(0.0, self.reload_timer - dt)

        x, y = obs_np[2], obs_np[3]
        enemy_x, enemy_y = obs_np[4], obs_np[5]
        enemy_bullets = obs_np[34:46].reshape(-1, 2)
        enemy_bullet_vels = obs_np[58:70].reshape(-1, 2)

        # Predictive Aiming
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

        # Precision Dodging 
        dodge_x, dodge_y = 0.0, 0.0
        danger_level = 0.0
        
        for i in range(6):
            bx, by = enemy_bullets[i]
            if bx < 0 or by < 0: continue
            bvx, bvy = enemy_bullet_vels[i]
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

        # Movement Vectors
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

        # Wall Avoidance
        margin = 100.0
        near_wall = False
        if x < margin or x > self.screenw - margin or y < margin or y > self.screenh - margin:
            near_wall = True

        if x < margin: move_x += 2.0 * (margin - x) / margin
        elif x > self.screenw - margin: move_x -= 2.0 * (x - (self.screenw - margin)) / margin
        if y < margin: move_y += 2.0 * (margin - y) / margin
        elif y > self.screenh - margin: move_y -= 2.0 * (y - (self.screenh - margin)) / margin

        # Tactical Dash Decisions (Defensive or Escape Wall Trap)
        dash = False
        if self.dash_cooldown <= 0.0:
            if (danger_level > 1.2) or (near_wall and danger_level > 0.4):
                dash = True
                self.dash_cooldown = 0.6

        # Action Formatting
        final_mag = math.hypot(move_x, move_y)
        if final_mag > 1.0:
            move_x /= final_mag; move_y /= final_mag

        mx = 1 if move_x > 0.2 else -1 if move_x < -0.2 else 0
        my = 1 if move_y > 0.2 else -1 if move_y < -0.2 else 0

        # Smart Reloading
        reload = False
        if self.reload_timer <= 0.0:
            if self.ammo <= 0 or (self.ammo <= 4 and dist_to_enemy > 450 and danger_level == 0):
                reload = True
                self.ammo = 10
                self.reload_timer = 1.2

        # Firing Logic
        self.fire_cooldown -= dt
        fire = False
        if self.fire_cooldown <= 0 and dist_to_enemy < 700 and self.ammo > 0 and self.reload_timer <= 0 and not dash:
            fire = True
            self.ammo -= 1
            self.fire_cooldown = 0.35

        return mx, my, fire, dash, reload, aim_x, aim_y

class MasterpieceBot:
    def __init__(self, screenw, screenh, aim_noise_std=8.0):
        self.screenw = screenw
        self.screenh = screenh
        self.aim_noise_std = aim_noise_std
        self.fire_cooldown = 0.0
        
        self.enemy_history = []
        self.circle_dir = 1.0
        self.stance_timer = 0.0
        self.current_stance = "SKIRMISH" # ASSAULT, SKIRMISH, EVADE

        # Resource Profiles
        self.ammo = 10
        self.dash_cooldown = 0.0
        self.reload_timer = 0.0

    def act(self, obs_np, dt):
        if dt <= 0: dt = 0.016
        
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.reload_timer = max(0.0, self.reload_timer - dt)

        x, y = obs_np[2], obs_np[3]
        enemy_x, enemy_y = obs_np[4], obs_np[5]
        dist_to_enemy = math.hypot(enemy_x - x, enemy_y - y)
        enemy_bullets = obs_np[34:46].reshape(-1, 2)
        enemy_bullet_vels = obs_np[58:70].reshape(-1, 2)

        # 1. Acceleration-Aware Tracking
        self.enemy_history.append((enemy_x, enemy_y, dt))
        if len(self.enemy_history) > 4: self.enemy_history.pop(0)

        ev_x, ev_y = 0.0, 0.0
        ea_x, ea_y = 0.0, 0.0
        if len(self.enemy_history) >= 2:
            p2, p1 = self.enemy_history[-1], self.enemy_history[-2]
            ev_x = (p2[0] - p1[0]) / p2[2]
            ev_y = (p2[1] - p1[1]) / p2[2]
        if len(self.enemy_history) >= 3:
            p3, p2, p1 = self.enemy_history[-1], self.enemy_history[-2], self.enemy_history[-3]
            v2_x, v2_y = (p3[0] - p2[0]) / p3[2], (p3[1] - p2[1]) / p3[2]
            v1_x, v1_y = (p2[0] - p1[0]) / p2[2], (p2[1] - p1[1]) / p2[2]
            ea_x, ea_y = (v2_x - v1_x) / p3[2], (v2_y - v1_y) / p3[2]

        # 2. Advanced Predictive Aim
        bullet_speed = 850.0  
        time_to_impact = dist_to_enemy / bullet_speed
        pred_ex = enemy_x + (ev_x * time_to_impact) + (0.5 * ea_x * (time_to_impact ** 2))
        pred_ey = enemy_y + (ev_y * time_to_impact) + (0.5 * ea_y * (time_to_impact ** 2))
        aim_x = pred_ex + random.gauss(0, self.aim_noise_std)
        aim_y = pred_ey + random.gauss(0, self.aim_noise_std)

        # 3. Micro Time-To-Collision Tracking (Iframe Bypass Strategy)
        imminent_threats = 0
        critical_iframe_window = False
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
            
            if 0 < t_closest < 1.2:
                closest_x = bx + bvx * t_closest
                closest_y = by + bvy * t_closest
                perp_dist = math.hypot(x - closest_x, y - closest_y)

                if perp_dist < 45.0:
                    imminent_threats += 1
                    # Is a bullet hitting us within the next few frames?
                    if t_closest < 0.18:
                        critical_iframe_window = True

                    repel_dir_x, repel_dir_y = x - closest_x, y - closest_y
                    r_dist = math.hypot(repel_dir_x, repel_dir_y)
                    if r_dist == 0: r_dist = 1.0
                    force_mag = (1.5 / (t_closest + 0.05)) * (45.0 / max(r_dist, 1.0))
                    bullet_forces_x += (repel_dir_x / r_dist) * force_mag
                    bullet_forces_y += (repel_dir_y / r_dist) * force_mag

        # 4. Neural Stance Machine
        self.stance_timer -= dt
        if self.stance_timer <= 0:
            if imminent_threats >= 2:
                self.current_stance = "EVADE"
                self.stance_timer = 0.4
            elif dist_to_enemy > 450 and self.ammo >= 7:
                self.current_stance = "ASSAULT"
                self.stance_timer = random.uniform(1.0, 1.8)
            else:
                self.current_stance = "SKIRMISH"
                self.stance_timer = random.uniform(1.0, 2.5)
                if random.random() < 0.5: self.circle_dir *= -1.0

        # 5. Potential Fields Calculations
        fx, fy = bullet_forces_x, bullet_forces_y
        target_dist = 350.0
        speed_modifier = 1.0
        
        if self.current_stance == "ASSAULT":
            target_dist = 200.0
            speed_modifier = 1.25
        elif self.current_stance == "EVADE":
            target_dist = 480.0
            speed_modifier = 0.95

        dx_e, dy_e = enemy_x - x, enemy_y - y
        dir_ex = dx_e / max(dist_to_enemy, 1.0)
        dir_ey = dy_e / max(dist_to_enemy, 1.0)

        dist_error = dist_to_enemy - target_dist
        fx += dir_ex * (dist_error / 100.0) * speed_modifier
        fy += dir_ey * (dist_error / 100.0) * speed_modifier
        fx += -dir_ey * self.circle_dir * 1.4 * speed_modifier
        fy += dir_ex * self.circle_dir * 1.4 * speed_modifier

        # Exponential Border Mapping
        w_margin = 120.0; w_force = 3.0
        if x < w_margin: fx += w_force * ((w_margin - x) / w_margin) ** 2
        elif x > self.screenw - w_margin: fx -= w_force * ((x - (self.screenw - w_margin)) / w_margin) ** 2
        if y < w_margin: fy += w_force * ((w_margin - y) / w_margin) ** 2
        elif y > self.screenh - w_margin: fy -= w_force * ((y - (self.screenh - w_margin)) / w_margin) ** 2

        if self.current_stance != "EVADE":
            fx += random.uniform(-0.2, 0.2)
            fy += random.uniform(-0.2, 0.2)

        # 6. Ultra-Tactical Dash Controller
        dash = False
        if self.dash_cooldown <= 0.0:
            # Condition A: Exploit iframe invulnerability to completely bypass guaranteed impacts
            if critical_iframe_window:
                dash = True
            # Condition B: Kinetic Gap Close during assault states if enemy tries to run
            elif self.current_stance == "ASSAULT" and dist_to_enemy > 450.0 and self.ammo >= 5:
                dash = True
            
            if dash:
                self.dash_cooldown = 0.6

        # Convert continuous forces to clean motor inputs
        f_mag = math.hypot(fx, fy)
        if f_mag > 1.0:
            fx /= f_mag; fy /= f_mag

        mx = 1 if fx > 0.22 else -1 if fx < -0.22 else 0
        my = 1 if fy > 0.22 else -1 if fy < -0.22 else 0

        # 7. Preemptive / Forced Reload Management
        reload = False
        if self.reload_timer <= 0.0:
            # Force reload if completely empty
            if self.ammo <= 0:
                reload = True
            # Preemptive reload: low ammo, safe stance, and enemy not in active engagement range
            elif self.ammo <= 3 and imminent_threats == 0 and self.current_stance != "ASSAULT":
                reload = True
            
            if reload:
                self.ammo = 10
                self.reload_timer = 1.2

        # 8. Fire Execution (Blocked automatically if dashing)
        self.fire_cooldown -= dt
        fire = False
        max_viable_range = 750.0 if self.current_stance == "ASSAULT" else 600.0
        
        if self.fire_cooldown <= 0 and dist_to_enemy < max_viable_range and self.ammo > 0 and self.reload_timer <= 0 and not dash:
            fire = True
            self.ammo -= 1
            self.fire_cooldown = 0.28 if self.current_stance == "ASSAULT" else 0.36

        return mx, my, fire, dash, reload, aim_x, aim_y

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
