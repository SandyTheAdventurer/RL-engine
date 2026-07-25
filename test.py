import sys
import os
import time
sys.path.append(os.path.abspath("build"))

import Game
from rl.bots import HardBot

SCREENW, SCREENH = 1280, 720
ENGINE_DT = 1.0 / 60.0

p1 = Game.Player(0, 0, 200.0, "player")
p2 = Game.Player(0, 0, 200.0, "bot")
engine = Game.Engine(True, True, p1, p2, SCREENW, SCREENH)
engine.reset()

Game.Visuals.init(engine, p1, p2)

bot = HardBot(SCREENW, SCREENH)

def run_game():
    engine.reset()
    Game.Visuals.start_fight_music()
    clock = time.time()
    running = True

    while running:
        frame = Game.poll_events()
        if frame.quit:
            return False

        if not engine.is_done():
            intent1 = Game.get_human_intent(frame)

            obs = engine.observe(p2, p1)
            mx, my, fire, dash, spell, aim_x, aim_y, attack = bot.act(obs, ENGINE_DT)
            intent2 = Game.PlayerIntent(int(mx), int(my), bool(fire), bool(dash), int(spell), float(aim_x), float(aim_y), bool(attack))

            engine.step(intent1, intent2, ENGINE_DT)
            engine.try_collect_drop(p1.px, p1.py)
        # When a player dies the engine feeds neutral inputs itself and keeps
        # is_done() false until the death animation finishes, so the normal
        # step/render cycle above plays it out with no special-casing here.

        engine.render()
        Game.Visuals.hud(engine)
        engine.present()

        target = clock + ENGINE_DT
        now = time.time()
        if now < target:
            time.sleep(target - now)
        clock = target

        if engine.is_done():
            Game.Visuals.stop_fight_music()
            teff = engine.get_teff()
            p2_health_before = p2.max_hp

            if p2.health <= 0:
                payout = Game.Economy.calculate_payout(teff)
                p1.dimes += payout
                print(f"WIN! teff={teff:.1f}s, payout={payout:.0f} dimes, total={p1.dimes:.0f}")
            else:
                damage_dealt = p2_health_before - max(0, p2.health)
                pity = Game.Economy.calculate_pity_dimes(damage_dealt, 0, 0)
                p1.dimes += pity
                drop = Game.Economy.create_drop(p1.px, p1.py, p1.dimes)
                engine.dropped_dimes.amount = drop.amount
                engine.dropped_dimes.x = drop.x
                engine.dropped_dimes.y = drop.y
                engine.dropped_dimes.collected = False
                engine.dropped_dimes.time_since_drop = 0.0
                print(f"LOSS! teff={teff:.1f}s, pity={pity:.0f} dimes, dropped={drop.amount:.0f}")
                print(f"  Collect drop at ({drop.x:.0f}, {drop.y:.0f}) to recover")

            while True:
                frame = Game.poll_events()
                if frame.quit:
                    return False
                res = Game.Visuals.end_menu(engine, frame)
                if res == Game.MenuResult.RESTART:
                    break
                if res == Game.MenuResult.QUIT:
                    return False

            engine.reset()
            Game.Visuals.start_fight_music()
            clock = time.time()

    return True

running = True
while running:
    frame = Game.poll_events()
    if frame.quit:
        break
    res = Game.Visuals.start_menu(engine, frame)
    if res == Game.MenuResult.PLAY:
        if not run_game():
            break
    elif res == Game.MenuResult.QUIT:
        break

Game.Visuals.shutdown()
engine.close()
