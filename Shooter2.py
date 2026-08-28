import pygame
import random
import json
import os
import sys
import math

try:
    pygame.mixer.init()
except:
    pass

pygame.init()
pygame.joystick.init()

W, H = 480, 640
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Star Mission All In One")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 28)
small = pygame.font.Font(None, 22)
big = pygame.font.Font(None, 58)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (16, 20, 38)
GREEN = (0, 210, 110)
RED = (230, 70, 70)
GOLD = (255, 215, 90)
GRAY = (100, 100, 110)
CYAN = (90, 230, 255)
BROWN = (140, 95, 55)
PINK = (255, 130, 185)
PURPLE = (160, 110, 255)
ORANGE = (255, 170, 70)

SAVE_FILE = "save.json"
WAVE_SIZE = 4
WAVE_PAUSE_MS = 10000
WAVE_ACTIVE_MS = 4500
BOSS_EVERY = 5
SHIELD_DURATION = 25000

QUESTS = [
    ("Kill 5", 5),
    ("Kill 10", 10),
    ("Kill 25", 25),
    ("Survive 60s", 60),
    ("Survive 300s", 300),
]

SHOP_ITEMS = [
    ("Bullet Speed +1", 15, "bullet_speed"),
    ("Fire Rate +1", 20, "fire_rate"),
    ("Max Health +1", 25, "max_health"),
    ("Move Speed +1", 15, "move_speed"),
    ("Shield 25s", 30, "shield"),
]

MAPS = [
    {"bg": (16, 20, 38), "stars": (90, 230, 255), "accent": (255, 130, 185), "planet": (70, 70, 120)},
    {"bg": (18, 28, 28), "stars": (255, 215, 90), "accent": (90, 230, 255), "planet": (55, 110, 85)},
    {"bg": (32, 18, 40), "stars": (160, 110, 255), "accent": (255, 170, 70), "planet": (100, 70, 130)},
    {"bg": (20, 30, 48), "stars": (255, 255, 255), "accent": (130, 255, 180), "planet": (60, 95, 140)},
]

screen_shake = 0
wave_banner_t = 0
particles = []
sounds = {}

def load_snd(name):
    try:
        return pygame.mixer.Sound(name)
    except:
        return None

def play_snd(name):
    s = sounds.get(name)
    if s:
        s.play()

def txt(s, x, y, c=WHITE, f=font):
    screen.blit(f.render(str(s), True, c), (x, y))

def draw_glass(rect, fill=(255, 255, 255), border=WHITE, alpha=160, border_w=2, radius=18):
    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(surf, (*fill, alpha), (0, 0, rect.width, rect.height), border_radius=radius)
    if border_w > 0:
        pygame.draw.rect(surf, (*border, 180), (0, 0, rect.width, rect.height), border_w, border_radius=radius)
    screen.blit(surf, rect.topleft)

def draw_button(rect, label, fill=(70, 70, 120), outline=WHITE, text_color=WHITE, font_obj=font):
    draw_glass(rect, fill, outline, 175, 2, 16)
    txt(label, rect.x + 16, rect.y + (rect.height // 2 - 10), text_color, font_obj)

def load_save():
    default = {
        "best_score": 0,
        "coins": 0,
        "upgrades": {"bullet_speed": 0, "fire_rate": 0, "max_health": 0, "move_speed": 0},
        "sound": True,
        "selected_skin": "default",
    }
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
            default["best_score"] = data.get("best_score", default["best_score"])
            default["coins"] = data.get("coins", default["coins"])
            default["sound"] = data.get("sound", default["sound"])
            default["selected_skin"] = data.get("selected_skin", default["selected_skin"])
            if "upgrades" in data:
                for k in default["upgrades"]:
                    default["upgrades"][k] = data["upgrades"].get(k, default["upgrades"][k])
        except:
            pass
    return default

save_data = load_save()

def save_game():
    with open(SAVE_FILE, "w") as f:
        json.dump(save_data, f)

try:
    sounds["shoot"] = load_snd("shoot.wav")
    sounds["hit"] = load_snd("hit.wav")
    sounds["coin"] = load_snd("coin.wav")
    sounds["upgrade"] = load_snd("upgrade.wav")
    sounds["boom"] = load_snd("boom.wav")
except:
    pass

def reset_run():
    mhp = 15 + save_data["upgrades"]["max_health"]
    return {
        "basket": pygame.Rect(W // 2 - 40, H - 80, 80, 20),
        "bullets": [],
        "enemy_bullets": [],
        "score": 0,
        "health": mhp,
        "max_health": mhp,
        "speed": 2,
        "bullet_speed": 8 + save_data["upgrades"]["bullet_speed"] * 2,
        "fire_cd": max(60, 220 - save_data["upgrades"]["fire_rate"] * 20),
        "last_fire": 0,
        "coins": save_data["coins"],
        "shop_open": False,
        "run_start": pygame.time.get_ticks(),
    }

run = reset_run()
state = "menu"

wave_num = 1
wave_state = "pause"
wave_start = pygame.time.get_ticks()
wave_enemies = []
map_theme = random.randint(0, len(MAPS) - 1)
map_scroll = 0
boss_active = False
boss = None

shield_active = False
shield_start = 0

def make_ship(x, t):
    bob = int(math.sin(t * 0.01) * 2)
    return {
        "body": pygame.Rect(x, H - 90 + bob, 70, 28),
        "wingL": pygame.Rect(x - 14, H - 82 + bob, 18, 10),
        "wingR": pygame.Rect(x + 66, H - 82 + bob, 18, 10),
        "nose": pygame.Rect(x + 26, H - 110 + bob, 18, 24),
    }

def spawn_enemy():
    kind = random.choices(["normal", "fast", "tank"], weights=[60, 25, 15], k=1)[0]
    if kind == "fast":
        color, hp, spd, size, score, shoot_cd = ORANGE, 1, random.randint(3, 4), 16, 2, 1100
    elif kind == "tank":
        color, hp, spd, size, score, shoot_cd = PURPLE, 2, 1, 24, 3, 900
    else:
        color, hp, spd, size, score, shoot_cd = random.choice([GOLD, CYAN, PINK]), 1, 2, 20, 1, 1300
    x = random.randint(10, W - size - 10)
    return {
        "rect": pygame.Rect(x, -size, size, size),
        "delay": pygame.time.get_ticks() + WAVE_PAUSE_MS,
        "color": color,
        "hp": hp,
        "speed": spd,
        "score": score,
        "kind": kind,
        "spawn_t": pygame.time.get_ticks(),
        "last_shot": pygame.time.get_ticks(),
        "shoot_cd": shoot_cd,
    }

def spawn_boss():
    return {
        "rect": pygame.Rect(W // 2 - 45, -90, 90, 70),
        "hp": 25,
        "max_hp": 25,
        "speed": 1,
        "color": PURPLE,
        "last_shot": 0,
        "dir": 1,
    }

def button_hit(rect, mouse, click):
    return rect.collidepoint(mouse) and click

def controller_move():
    move_left = False
    move_right = False
    shoot = False
    for i in range(pygame.joystick.get_count()):
        joy = pygame.joystick.Joystick(i)
        if not joy.get_init():
            joy.init()
        if joy.get_numaxes() > 0:
            ax = joy.get_axis(0)
            if ax < -0.4:
                move_left = True
            if ax > 0.4:
                move_right = True
        if joy.get_numbuttons() > 0 and joy.get_button(0):
            shoot = True
    return move_left, move_right, shoot

def fire_bullet():
    now = pygame.time.get_ticks()
    if now - run["last_fire"] >= run["fire_cd"]:
        run["last_fire"] = now
        run["bullets"].append(pygame.Rect(run["basket"].centerx - 3, run["basket"].top - 10, 6, 10))
        play_snd("shoot")

def add_explosion(pos, base_color=GOLD, count=22):
    for _ in range(count):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(1.5, 5.5)
        life = random.randint(18, 40)
        particles.append({
            "x": float(pos[0]),
            "y": float(pos[1]),
            "vx": math.cos(ang) * spd,
            "vy": math.sin(ang) * spd,
            "life": life,
            "max": life,
            "color": random.choice([base_color, ORANGE, WHITE]),
            "size": random.randint(2, 4),
        })

def start_wave():
    global wave_state, wave_start, wave_enemies, map_theme, wave_banner_t, boss_active, boss
    if (wave_num % BOSS_EVERY) == 0:
        boss_active = True
        boss = spawn_boss()
        wave_enemies = []
    else:
        boss_active = False
        boss = None
        wave_enemies = [spawn_enemy() for _ in range(WAVE_SIZE)]
    wave_state = "pause"
    wave_start = pygame.time.get_ticks()
    wave_banner_t = pygame.time.get_ticks()
    map_theme = random.randint(0, len(MAPS) - 1)

def force_wave_leave():
    global wave_enemies, screen_shake
    if wave_enemies:
        run["health"] -= len(wave_enemies)
        for en in wave_enemies:
            add_explosion(en["rect"].center, en["color"], 10)
        wave_enemies = []
        screen_shake = 12

def draw_background():
    global map_scroll
    theme = MAPS[map_theme]
    screen.fill(theme["bg"])
    map_scroll = (map_scroll + 1) % W
    for i in range(24):
        x = (i * 87 + map_scroll) % W
        y = (i * 53 + map_scroll // 2) % H
        pygame.draw.circle(screen, theme["stars"], (x, y), 1)
    pygame.draw.circle(screen, theme["planet"], (W - 70, 100), 46)
    pygame.draw.circle(screen, theme["accent"], (80, 110), 26, 2)
    pygame.draw.circle(screen, theme["accent"], (W // 2, 60), 16, 2)

def draw_particles():
    for p in particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.06
        p["life"] -= 1
        if p["life"] <= 0:
            particles.remove(p)
            continue
        alpha = int(255 * (p["life"] / p["max"]))
        size = max(1, p["size"])
        surf = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*p["color"], alpha), (size + 1, size + 1), size)
        screen.blit(surf, (int(p["x"]) - size - 1, int(p["y"]) - size - 1))

def draw_hud(survive):
    top = pygame.Rect(0, 0, W, 82)
    draw_glass(top, (10, 12, 24), WHITE, 85, 0, 0)
    txt(f"Score: {run['score']}", 10, 10)
    txt(f"HP: {run['health']}/{run['max_health']}", 10, 64, WHITE, small)
    txt(f"Best: {save_data['best_score']}", 300, 10)
    txt(f"Coins: {run['coins']}", 300, 34)
    txt(f"Time: {survive}s", 330, 64, WHITE, small)
    y = 95
    txt("Quests:", 160, 10)
    for i, (qname, qgoal) in enumerate(QUESTS):
        progress = run["score"] if i < 3 else survive
        done = progress >= qgoal
        marker = "✓" if done else "-"
        txt(f"{marker} {qname}: {min(progress, qgoal)}/{qgoal}", 110, y, GREEN if done else WHITE, small)
        y += 20

def draw_wave_banner():
    now = pygame.time.get_ticks()
    if now - wave_banner_t < 1400:
        a = 255 - int((now - wave_banner_t) / 1400 * 255)
        surf = pygame.Surface((W, 60), pygame.SRCALPHA)
        pygame.draw.rect(surf, (30, 40, 70, max(0, a // 2)), (60, 0, 360, 46), border_radius=16)
        pygame.draw.rect(surf, (255, 255, 255, max(0, a)), (60, 0, 360, 46), 2, border_radius=16)
        screen.blit(surf, (0, 95))
        txt(f"WAVE {wave_num}", 185, 108, GOLD, font)

def draw_player():
    t = pygame.time.get_ticks()
    ship = make_ship(run["basket"].x, t)
    pygame.draw.polygon(screen, CYAN, [(ship["body"].left, ship["body"].bottom), (ship["body"].centerx, ship["nose"].top), (ship["body"].right, ship["body"].bottom)])
    pygame.draw.rect(screen, BROWN, ship["body"])
    pygame.draw.rect(screen, PINK, ship["wingL"])
    pygame.draw.rect(screen, PINK, ship["wingR"])
    pygame.draw.rect(screen, WHITE, ship["nose"])
    if shield_active:
        r = 45 + int(3 * math.sin(t * 0.01))
        pygame.draw.circle(screen, CYAN, run["basket"].center, r, 3)
        pygame.draw.circle(screen, WHITE, run["basket"].center, r + 5, 1)

def draw_controls():
    left_btn = pygame.Rect(10, H - 90, 90, 70)
    right_btn = pygame.Rect(105, H - 90, 90, 70)
    shoot_btn = pygame.Rect(W - 100, H - 90, 90, 70)
    shop_btn = pygame.Rect(W // 2 - 40, H - 90, 80, 28)
    draw_button(left_btn, "<", fill=(70, 70, 110), font_obj=big)
    draw_button(right_btn, ">", fill=(70, 70, 110), font_obj=big)
    draw_button(shoot_btn, "FIRE", fill=(70, 70, 110), font_obj=font)
    draw_button(shop_btn, "SHOP", fill=(90, 100, 145), font_obj=small)
    return left_btn, right_btn, shoot_btn, shop_btn

def draw_shop_overlay():
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((5, 8, 18, 110))
    screen.blit(overlay, (0, 0))
    panel = pygame.Rect(32, 60, 416, 500)
    draw_glass(panel, (40, 52, 90), WHITE, 165, 2, 18)
    txt("SHOP", 203, 76, GOLD, big)
    txt(f"Coins: {run['coins']}", 176, 125, WHITE, font)
    y = 170
    buttons = []
    for label, cost, key in SHOP_ITEMS:
        r = pygame.Rect(52, y, 376, 54)
        buttons.append((r, label, cost, key))
        fill = (58, 68, 104) if run["coins"] >= cost else (48, 48, 60)
        draw_glass(r, fill, WHITE, 180, 2, 16)
        txt(label, 68, y + 16, WHITE, font)
        txt(f"{cost} coins", 302, y + 16, GOLD, font)
        y += 74
    back = pygame.Rect(165, 515, 150, 42)
    draw_button(back, "BACK", fill=(85, 95, 140))
    return buttons, back

def handle_shop_purchase(key, cost):
    global shield_active, shield_start
    if run["coins"] < cost:
        return
    run["coins"] -= cost
    save_data["coins"] = run["coins"]

    if key == "shield":
        shield_active = True
        shield_start = pygame.time.get_ticks()
        play_snd("upgrade")
        save_game()
        return

    save_data["upgrades"][key] += 1
    if key == "bullet_speed":
        run["bullet_speed"] += 2
    elif key == "fire_rate":
        run["fire_cd"] = max(60, run["fire_cd"] - 20)
    elif key == "max_health":
        run["max_health"] += 1
        run["health"] += 1
    elif key == "move_speed":
        pass

    play_snd("upgrade")
    save_game()

def lose_screen():
    while True:
        click = False
        mouse = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                click = True
        screen.fill((45, 12, 12))
        txt("YOU LOSE", 145, 135, WHITE, big)
        txt(f"Score: {run['score']}", 170, 215, WHITE, font)
        again = pygame.Rect(150, 300, 180, 48)
        menu = pygame.Rect(150, 372, 180, 48)
        draw_button(again, "RESTART", fill=(120, 70, 70))
        draw_button(menu, "MAIN MENU", fill=(120, 70, 70))
        if button_hit(again, mouse, click):
            return "play"
        if button_hit(menu, mouse, click):
            return "menu"
        pygame.display.flip()
        clock.tick(60)

def success_screen():
    while True:
        click = False
        mouse = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                click = True
        screen.fill((10, 40, 15))
        txt("MISSION SUCCESS", 55, 135, WHITE, big)
        txt(f"Score: {run['score']}", 170, 215, WHITE, font)
        again = pygame.Rect(145, 300, 190, 48)
        menu = pygame.Rect(145, 372, 190, 48)
        draw_button(again, "PLAY AGAIN", fill=(70, 110, 80))
        draw_button(menu, "MAIN MENU", fill=(70, 110, 80))
        if button_hit(again, mouse, click):
            return "play"
        if button_hit(menu, mouse, click):
            return "menu"
        pygame.display.flip()
        clock.tick(60)

def update_boss(t):
    global boss
    if boss is None:
        return
    boss["rect"].x += boss["dir"] * 2
    if boss["rect"].left < 20 or boss["rect"].right > W - 20:
        boss["dir"] *= -1
    if boss["rect"].y < 60:
        boss["rect"].y += 1
    if t - boss["last_shot"] > 700:
        boss["last_shot"] = t
        run["enemy_bullets"].append([pygame.Rect(boss["rect"].centerx - 3, boss["rect"].bottom, 6, 12), 6])
    if not shield_active and boss["rect"].colliderect(run["basket"]):
        run["health"] -= 1
        add_explosion(run["basket"].center, RED, 14)
        play_snd("hit")

start_wave()

while True:
    click = False
    mouse = pygame.mouse.get_pos()

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            save_data["coins"] = run["coins"]
            save_game()
            pygame.quit()
            sys.exit()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            click = True
        if state == "play" and e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                fire_bullet()
            if e.key == pygame.K_EQUALS and (e.mod & pygame.KMOD_SHIFT):
                run["coins"] += 100
                save_data["coins"] = run["coins"]
                play_snd("coin")
                save_game()
            if e.key == pygame.K_EQUALS and (e.mod & pygame.KMOD_CTRL):
                run["shop_open"] = not run["shop_open"]
            if e.key in (pygame.K_SLASH, pygame.K_s, pygame.K_KP_PLUS):
                run["shop_open"] = not run["shop_open"]

    if state == "menu":
        screen.fill(BLUE)
        play = pygame.Rect(160, 220, 160, 48)
        shop = pygame.Rect(160, 285, 160, 48)
        quitb = pygame.Rect(160, 350, 160, 48)
        txt("STAR MISSION", 120, 80, GOLD, big)
        txt("Mobile + controller friendly", 95, 140, WHITE, small)
        draw_button(play, "PLAY")
        draw_button(shop, "SHOP")
        draw_button(quitb, "QUIT")
        txt(f"Best: {save_data['best_score']}  Coins: {save_data['coins']}", 80, 430)
        if button_hit(play, mouse, click):
            run = reset_run()
            wave_num = 1
            wave_state = "pause"
            wave_start = pygame.time.get_ticks()
            wave_enemies = []
            particles = []
            run["enemy_bullets"] = []
            shield_active = False
            map_theme = random.randint(0, len(MAPS) - 1)
            start_wave()
            state = "play"
        if button_hit(shop, mouse, click):
            state = "shop"
        if button_hit(quitb, mouse, click):
            save_data["coins"] = run["coins"]
            save_game()
            pygame.quit()
            sys.exit()
        pygame.display.flip()
        clock.tick(60)
        continue

    if state == "shop":
        buttons, back = draw_shop_overlay()
        for r, label, cost, key in buttons:
            if button_hit(r, mouse, click):
                handle_shop_purchase(key, cost)
        if button_hit(back, mouse, click):
            state = "menu"
        pygame.display.flip()
        clock.tick(60)
        continue

    if state == "play":
        keys = pygame.key.get_pressed()
        joy_left, joy_right, joy_shoot = controller_move()

        move = 6 + save_data["upgrades"]["move_speed"]
        if (keys[pygame.K_LEFT] or joy_left) and run["basket"].left > 0:
            run["basket"].x -= move
        if (keys[pygame.K_RIGHT] or joy_right) and run["basket"].right < W:
            run["basket"].x += move

        left_btn, right_btn, shoot_btn, shop_btn = draw_controls()

        if click:
            if left_btn.collidepoint(mouse):
                run["basket"].x = max(0, run["basket"].x - move)
            if right_btn.collidepoint(mouse):
                run["basket"].x = min(W - run["basket"].width, run["basket"].x + move)
            if shoot_btn.collidepoint(mouse):
                fire_bullet()
            if shop_btn.collidepoint(mouse):
                run["shop_open"] = not run["shop_open"]

        if joy_shoot:
            fire_bullet()

        draw_background()

        t = pygame.time.get_ticks()
        survive = (t - run["run_start"]) // 1000

        if shield_active and t - shield_start >= SHIELD_DURATION:
            shield_active = False

        if not wave_enemies and not boss_active and wave_state != "active":
            start_wave()

        if wave_state == "pause":
            if t - wave_start >= WAVE_PAUSE_MS:
                wave_state = "active"
                wave_start = t

        elif wave_state == "active":
            if boss_active and boss is not None:
                update_boss(t)
                for b in run["bullets"][:]:
                    if b.colliderect(boss["rect"]):
                        run["bullets"].remove(b)
                        boss["hp"] -= 1
                        add_explosion(b.center, CYAN, 6)
                        play_snd("hit")
                        if boss["hp"] <= 0:
                            add_explosion(boss["rect"].center, GOLD, 40)
                            play_snd("boom")
                            run["score"] += 20
                            run["coins"] += 20
                            save_data["coins"] = run["coins"]
                            save_data["best_score"] = max(save_data["best_score"], run["score"])
                            boss_active = False
                            boss = None
                            wave_num += 1
                            wave_state = "pause"
                            wave_start = t
                            start_wave()
                        break

                for eb in run["enemy_bullets"][:]:
                    eb[0].y += eb[1]
                    if eb[0].top > H:
                        run["enemy_bullets"].remove(eb)
                    elif eb[0].colliderect(run["basket"]):
                        run["enemy_bullets"].remove(eb)
                        if not shield_active:
                            run["health"] -= 1
                            add_explosion(run["basket"].center, RED, 14)
                            play_snd("hit")

            else:
                for en in wave_enemies[:]:
                    if t >= en["delay"]:
                        en["rect"].y += en["speed"]

                    if t - en["last_shot"] >= en["shoot_cd"] and t >= en["delay"]:
                        en["last_shot"] = t
                        run["enemy_bullets"].append([pygame.Rect(en["rect"].centerx - 3, en["rect"].bottom, 5, 10), random.randint(4, 6)])

                    if en["rect"].top > H:
                        if not shield_active:
                            run["health"] -= 1
                        add_explosion(en["rect"].center, RED, 10)
                        play_snd("hit")
                        wave_enemies.remove(en)
                        continue

                    if en["rect"].colliderect(run["basket"]):
                        if not shield_active:
                            run["health"] -= 1
                        add_explosion(en["rect"].center, RED, 10)
                        play_snd("hit")
                        wave_enemies.remove(en)
                        continue

                    for b in run["bullets"][:]:
                        if b.colliderect(en["rect"]):
                            run["bullets"].remove(b)
                            en["hp"] -= 1
                            add_explosion(b.center, en["color"], 8)
                            play_snd("hit")
                            if en["hp"] <= 0:
                                if en in wave_enemies:
                                    wave_enemies.remove(en)
                                run["score"] += en["score"]
                                run["coins"] += en["score"]
                                save_data["coins"] = run["coins"]
                                save_data["best_score"] = max(save_data["best_score"], run["score"])
                                play_snd("coin")
                                screen_shake = 10
                            break

                if not wave_enemies:
                    wave_num += 1
                    wave_state = "pause"
                    wave_start = t
                    start_wave()
                elif t - wave_start >= WAVE_PAUSE_MS + WAVE_ACTIVE_MS:
                    force_wave_leave()
                    wave_num += 1
                    wave_state = "pause"
                    wave_start = t
                    start_wave()

        for b in run["bullets"][:]:
            b.y -= run["bullet_speed"]
            if b.bottom < 0:
                run["bullets"].remove(b)

        for eb in run["enemy_bullets"][:]:
            eb[0].y += eb[1]
            if eb[0].top > H:
                run["enemy_bullets"].remove(eb)
            elif eb[0].colliderect(run["basket"]):
                run["enemy_bullets"].remove(eb)
                if not shield_active:
                    run["health"] -= 1
                    add_explosion(run["basket"].center, RED, 14)
                    play_snd("hit")

        if screen_shake > 0:
            ox = random.randint(-screen_shake, screen_shake)
            oy = random.randint(-screen_shake, screen_shake)
            screen_shake -= 1
        else:
            ox = oy = 0

        frame = pygame.Surface((W, H))
        frame.blit(screen, (0, 0))
        screen.fill(BLACK)
        screen.blit(frame, (ox, oy))

        draw_player()

        for en in wave_enemies:
            rr = en["rect"]
            pulse_r = max(2, rr.width // 2 + int(math.sin(t * 0.01 + rr.x) * 2))
            pygame.draw.circle(screen, en["color"], rr.center, pulse_r)
            pygame.draw.circle(screen, WHITE, rr.center, pulse_r, 2)

        if boss_active and boss is not None:
            pygame.draw.rect(screen, boss["color"], boss["rect"], border_radius=14)
            pygame.draw.rect(screen, WHITE, boss["rect"], 2, border_radius=14)
            hpw = int(120 * boss["hp"] / boss["max_hp"])
            pygame.draw.rect(screen, RED, (180, 140, 120, 10), border_radius=6)
            pygame.draw.rect(screen, GREEN, (180, 140, hpw, 10), border_radius=6)

        for eb in run["enemy_bullets"]:
            pygame.draw.rect(screen, ORANGE, eb[0], border_radius=2)

        for b in run["bullets"]:
            pygame.draw.rect(screen, WHITE, b, border_radius=2)

        draw_particles()
        draw_hud(survive)
        draw_wave_banner()

        pygame.draw.rect(screen, RED, (10, 45, 150, 15), border_radius=8)
        pygame.draw.rect(screen, GREEN, (10, 45, min(150, int(150 * run["health"] / run["max_health"])), 15), border_radius=8)

        if run["shop_open"]:
            buttons, back = draw_shop_overlay()
            for r, label, cost, key in buttons:
                if button_hit(r, mouse, click):
                    handle_shop_purchase(key, cost)
            if button_hit(back, mouse, click):
                run["shop_open"] = False

        if run["score"] >= 25 or survive >= 300:
            save_data["coins"] = run["coins"]
            save_game()
            state = "success"
            continue

        if run["health"] <= 0:
            save_data["coins"] = run["coins"]
            save_game()
            state = "lose"
            continue

        pygame.display.flip()
        clock.tick(60)
        continue

    if state == "lose":
        state = lose_screen()
        if state == "play":
            run = reset_run()
            wave_num = 1
            wave_state = "pause"
            wave_start = pygame.time.get_ticks()
            wave_enemies = []
            particles = []
            run["enemy_bullets"] = []
            boss_active = False
            boss = None
            shield_active = False
            map_theme = random.randint(0, len(MAPS) - 1)
            start_wave()
            state = "play"
        continue

    if state == "success":
        state = success_screen()
        if state == "play":
            run = reset_run()
            wave_num = 1
            wave_state = "pause"
            wave_start = pygame.time.get_ticks()
            wave_enemies = []
            particles = []
            run["enemy_bullets"] = []
            boss_active = False
            boss = None
            shield_active = False
            map_theme = random.randint(0, len(MAPS) - 1)
            start_wave()
            state = "play"
        continue