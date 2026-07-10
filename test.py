import sys, os, time
sys.path.append(os.path.abspath("build"))

import Game
from rl.bots import EasyBot, MediumBot, ExpertBot, NoopBot

SCREENW, SCREENH = 1280, 720
ENGINE_DT = 1.0 / 60.0

p1 = Game.Player(0, 0, 200.0, "player")
p2 = Game.Player(0, 0, 200.0, "bot")
engine = Game.Engine(True, True, p1, p2, SCREENW, SCREENH)
engine.reset()

Game.Visuals.init(engine, p1, p2)

bot = ExpertBot(SCREENW, SCREENH)

def run_game():
    engine.reset()
    clock = time.time()
    running = True

    while running:
        frame = Game.poll_events()
        if frame.quit:
            return False

        intent1 = Game.get_human_intent(frame)

        obs = engine.observe(p2, p1)
        mx, my, fire, dash, reload, aim_x, aim_y, attack = bot.act(obs, ENGINE_DT)
        intent2 = Game.PlayerIntent(int(mx), int(my), bool(fire), bool(dash), bool(reload), float(aim_x), float(aim_y), bool(attack))

        engine.step(intent1, intent2, ENGINE_DT)
        engine.render()
        engine.present()

        target = clock + ENGINE_DT
        now = time.time()
        if now < target:
            time.sleep(target - now)
        clock = target

        if engine.is_done():
            Game.Visuals.end_screen(engine)
            engine.present()
            while True:
                frame = Game.poll_events()
                if frame.mouse_left_clicked:
                    return False
                if frame.mouse_right_clicked:
                    break
                if frame.quit:
                    return False
                engine.present()
            engine.reset()

    return True

Game.Visuals.start_screen(engine)
engine.present()
while True:
    frame = Game.poll_events()
    if frame.mouse_left_clicked:
        if not run_game():
            break
        Game.Visuals.start_screen(engine)
        engine.present()
    if frame.quit:
        break
    engine.present()

Game.Visuals.shutdown()
engine.close()