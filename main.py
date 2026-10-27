"""Lion Merchant: an 8-bit shop game. Serve customers with correct coins and prices."""
import math
import random
import sys

import pygame

from game_logic import (
    COIN_VALUES, check_order, haggle_accept, haggle_counter, make_order, short, tray_total,
)

W, H, SCALE = 320, 180, 3
PATIENCE = 45.0
MAX_LIVES = 3

# NES-ish palette
BLACK = (20, 12, 28)
WALL = (68, 36, 52)
WALL2 = (89, 49, 66)
WOOD = (133, 76, 48)
WOOD2 = (99, 55, 40)
FLOOR = (48, 52, 68)
WHITE = (238, 238, 238)
RED = (208, 70, 72)
GREEN = (109, 194, 202)
LIME = (117, 200, 79)
YELLOW = (218, 212, 94)
SKIN = (222, 170, 130)
COPPER = (196, 108, 60)
SILVER = (190, 198, 210)
GOLD = (240, 200, 60)
TIER_COLORS = [COPPER, COPPER, COPPER, COPPER, SILVER, SILVER, GOLD, GOLD]

# 12x16 customer sprite; letters map to a per-customer palette
CUSTOMER = [
    "....hhhh....",
    "...hhhhhh...",
    "..hhhhhhhh..",
    "..hssssssh..",
    "..hsesseshh.",
    "..hssssssh..",
    "...ssmmss...",
    "....ssss....",
    "..cccccccc..",
    ".cccccccccc.",
    "sccccccccccs",
    "sccccccccccs",
    ".cccccccccc.",
    "..cccccccc..",
    "..pp....pp..",
    ".bbb....bbb.",
]


def build_sprite(rows, palette, scale=1):
    surf = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in palette:
                surf.set_at((x, y), palette[ch])
    return surf


def random_customer():
    hair = random.choice([(60, 40, 30), (200, 160, 60), (150, 60, 60), (100, 100, 160), (30, 30, 40)])
    cloth = random.choice([(80, 120, 200), (90, 170, 90), (170, 90, 170), (200, 140, 60), (120, 120, 130)])
    pal = {"h": hair, "s": SKIN, "e": BLACK, "m": (160, 70, 70), "c": cloth, "p": (60, 60, 90), "b": (70, 45, 35)}
    return pygame.transform.scale(build_sprite(CUSTOMER, pal), (24, 32))


def make_coin_sprite(index):
    big = index % 2 == 1 or index == 7
    r = 6 if big else 5
    surf = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
    col = TIER_COLORS[index]
    dark = tuple(int(c * 0.6) for c in col)
    pygame.draw.circle(surf, dark, (r, r), r)
    pygame.draw.circle(surf, col, (r, r), r - 1)
    surf.set_at((r - 2, r - 2), WHITE)
    surf.set_at((r - 1, r - 2), WHITE)
    return surf


class Particle:
    def __init__(self, x, y, color):
        a = random.uniform(0, math.tau)
        s = random.uniform(15, 50)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * s, math.sin(a) * s - 20
        self.color = color
        self.life = random.uniform(0.4, 0.9)

    def update(self, dt):
        self.life -= dt
        self.vy += 90 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt


class Game:
    def __init__(self):
        pygame.init()
        self.window = pygame.display.set_mode((W * SCALE, H * SCALE))
        pygame.display.set_caption("Lion Merchant")
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 14)
        self.big = pygame.font.Font(None, 28)
        self.coin_sprites = [make_coin_sprite(i) for i in range(8)]
        self.coin_rects = [pygame.Rect(8 + i * 38, 138, 32, 36) for i in range(8)]
        self.ok_rect = pygame.Rect(W - 58, 100, 54, 14)
        self.clear_rect = pygame.Rect(W - 58, 118, 54, 14)
        self.high = 0
        self.reset()

    def reset(self):
        self.score = 0
        self.lives = MAX_LIVES
        self.served = 0
        self.over = False
        self.particles = []
        self.t = 0.0
        self.next_customer()

    def next_customer(self):
        level = 1 + self.served // 3
        self.order = make_order(level)
        self.sprite = random_customer()
        self.tray = {}
        self.typed = ""
        self.patience = max(20.0, PATIENCE - level * 3)
        self.max_patience = self.patience
        self.cx = -20.0
        self.phase = "enter"  # enter -> wait -> leave
        self.leave_dir = 1
        self.mood = ""
        self.msg = ""
        self.msg_timer = 0.0

    # --- actions -------------------------------------------------------
    def submit(self):
        if self.phase != "wait":
            return
        if self.order.kind == "haggle":
            self.haggle(accept=False)
            return
        ok, msg = check_order(self.order, self.tray, self.typed)
        self.msg, self.msg_timer = msg, 2.0
        if ok:
            bonus = int(self.patience / self.max_patience * 100)
            self.score += 100 + bonus
            self.served += 1
            self.burst(GOLD)
            self.mood = "happy"
        else:
            self.lives -= 1
            self.burst(RED)
            self.mood = "angry"
        self.phase = "leave"
        self.leave_dir = 1

    def haggle(self, accept):
        o = self.order
        if accept:
            status, msg = haggle_accept(o)
        elif self.typed.isdigit():
            status, msg = haggle_counter(o, int(self.typed))
        else:
            self.msg, self.msg_timer = "Type a counter price first", 1.5
            return
        self.msg, self.msg_timer = msg, 2.0
        self.typed = ""
        if status == "new_offer":
            self.burst(YELLOW)
            return
        if status == "sold":
            profit_pct = (o.offer - o.cost) * 100 // o.cost
            self.score += 100 + int(self.patience / self.max_patience * 100) + min(100, profit_pct)
            self.served += 1
            self.burst(GOLD)
            self.mood = "happy"
        elif status == "walked":
            self.mood = "angry"
            self.burst(YELLOW)
        else:
            self.lives -= 1
            self.mood = "angry"
            self.burst(RED)
        self.phase = "leave"

    def burst(self, color):
        for _ in range(30):
            self.particles.append(Particle(self.cx + 6, 60, color))

    def add_coin(self, i, delta):
        if self.phase != "wait" or not self.order.uses_tray:
            return
        v = COIN_VALUES[i]
        n = max(0, self.tray.get(v, 0) + delta)
        if n:
            self.tray[v] = n
        else:
            self.tray.pop(v, None)

    # --- loop ----------------------------------------------------------
    def handle(self, e):
        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if self.over:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                self.reset()
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_RETURN:
                self.submit()
            elif e.key == pygame.K_BACKSPACE:
                self.typed = self.typed[:-1]
            elif e.key == pygame.K_c:
                self.tray = {}
            elif e.unicode.isdigit() and not self.order.uses_tray and len(self.typed) < 8:
                self.typed += e.unicode
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            pos = (e.pos[0] // SCALE, e.pos[1] // SCALE)
            for i, r in enumerate(self.coin_rects):
                if r.collidepoint(pos):
                    self.add_coin(i, 1 if e.button == 1 else -1)
            if e.button == 1:
                if self.ok_rect.collidepoint(pos):
                    self.submit()
                elif self.clear_rect.collidepoint(pos):
                    if self.order.kind == "haggle":
                        if self.phase == "wait":
                            self.haggle(accept=True)
                    else:
                        self.tray = {}

    def update(self, dt):
        self.t += dt
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        self.msg_timer = max(0, self.msg_timer - dt)
        if self.over:
            return
        if self.phase == "enter":
            self.cx += 70 * dt
            if self.cx >= 40:
                self.cx, self.phase = 40, "wait"
        elif self.phase == "wait":
            self.patience -= dt
            if self.patience <= 0:
                self.lives -= 1
                self.msg, self.msg_timer = "Too slow!", 2.0
                self.mood = "angry"
                self.burst(RED)
                self.phase = "leave"
        elif self.phase == "leave":
            self.cx += 90 * dt
            if self.cx > W + 10:
                if self.lives <= 0:
                    self.over = True
                    self.high = max(self.high, self.score)
                else:
                    self.next_customer()

    # --- drawing -------------------------------------------------------
    def text(self, s, x, y, color=WHITE, font=None, center=False):
        img = (font or self.font).render(s, False, color)
        r = img.get_rect()
        if center:
            r.midtop = (x, y)
        else:
            r.topleft = (x, y)
        self.canvas.blit(img, r)

    def draw(self):
        c = self.canvas
        c.fill(WALL)
        for y in range(0, 90, 8):
            for x in range((y // 8 % 2) * 8, W, 16):
                pygame.draw.rect(c, WALL2, (x, y, 14, 6))
        pygame.draw.rect(c, FLOOR, (0, 90, W, 90))
        # shop window with a sun
        pygame.draw.rect(c, BLACK, (230, 14, 70, 44))
        pygame.draw.rect(c, (120, 170, 220), (232, 16, 66, 40))
        pygame.draw.circle(c, YELLOW, (280, 30), 6)
        # counter
        pygame.draw.rect(c, WOOD, (0, 84, W, 14))
        pygame.draw.rect(c, WOOD2, (0, 98, W, 4))

        if self.phase != "enter" or True:
            bob = int(abs(math.sin(self.t * 8)) * 2) if self.phase != "wait" else int(math.sin(self.t * 3) > 0.6)
            sx, sy = int(self.cx), 84 - 32 - bob
            c.blit(self.sprite, (sx, sy))
            if self.mood == "happy":
                self.text("^_^", sx + 6, sy - 10, LIME, center=True)
            elif self.mood == "angry":
                self.text(">:(", sx + 6, sy - 10, RED, center=True)

        # speech bubble
        if self.phase == "wait" or (self.phase == "leave" and not self.mood):
            bx, by = 62, 14
            pygame.draw.rect(c, WHITE, (bx, by, 150, 40))
            pygame.draw.rect(c, BLACK, (bx, by, 150, 40), 1)
            pygame.draw.polygon(c, WHITE, [(bx + 4, by + 40), (bx + 14, by + 40), (bx - 6, by + 52)])
            for i, line in enumerate(self.order.lines):
                self.text(line, bx + 5, by + 4 + i * 11, BLACK)

        # patience bar
        frac = max(0, self.patience / self.max_patience)
        pygame.draw.rect(c, BLACK, (8, 76, 42, 5))
        col = LIME if frac > 0.5 else YELLOW if frac > 0.25 else RED
        pygame.draw.rect(c, col, (9, 77, int(40 * frac), 3))

        # HUD
        self.text(f"SCORE {self.score}", 6, 4, YELLOW)
        self.text(f"BEST {self.high}", 6, 15, SILVER)
        for i in range(MAX_LIVES):
            col = RED if i < self.lives else (70, 50, 60)
            x, y = 190 + i * 11, 5
            pygame.draw.rect(c, col, (x, y + 1, 3, 3))
            pygame.draw.rect(c, col, (x + 4, y + 1, 3, 3))
            pygame.draw.rect(c, col, (x, y + 3, 7, 3))
            pygame.draw.rect(c, col, (x + 1, y + 6, 5, 1))
            pygame.draw.rect(c, col, (x + 2, y + 7, 3, 1))

        # tray / typed answer panel
        pygame.draw.rect(c, BLACK, (6, 104, W - 70, 30))
        if self.order.uses_tray:
            self.text(f"TRAY: {tray_total(self.tray):,} lion", 10, 108, WHITE)
            self.text("L-click add  R-click remove", 10, 120, SILVER)
        else:
            blink = "_" if int(self.t * 2) % 2 == 0 else " "
            self.text(f"ANSWER: {self.typed}{blink} {self.order.unit}", 10, 108, WHITE)
            hint = "Type counter, Enter" if self.order.kind == "haggle" else "Type digits, Enter to submit"
            self.text(hint, 10, 120, SILVER)

        for i, (r, spr) in enumerate(zip(self.coin_rects, self.coin_sprites)):
            pygame.draw.rect(c, WOOD2, r)
            pygame.draw.rect(c, BLACK, r, 1)
            c.blit(spr, spr.get_rect(center=(r.centerx, r.y + 12)))
            self.text(short(COIN_VALUES[i]), r.centerx, r.y + 22, WHITE, center=True)
            n = self.tray.get(COIN_VALUES[i], 0)
            if n:
                self.text(f"x{n}", r.right - 2, r.y + 1, YELLOW)

        haggling = self.order.kind == "haggle"
        buttons = ((self.ok_rect, "COUNTER" if haggling else "SERVE", LIME),
                   (self.clear_rect, "ACCEPT" if haggling else "CLEAR", YELLOW if haggling else RED))
        for r, label, col in buttons:
            pygame.draw.rect(c, col, r)
            pygame.draw.rect(c, BLACK, r, 1)
            self.text(label, r.centerx, r.y + 3, BLACK, center=True)

        if self.msg_timer > 0:
            self.text(self.msg, W // 2, 76, WHITE if self.mood == "happy" else RED, center=True)

        for p in self.particles:
            c.fill(p.color, (int(p.x), int(p.y), 2, 2))

        if self.over:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((0, 0, 0, 170))
            c.blit(s, (0, 0))
            self.text("SHOP CLOSED", W // 2, 55, RED, self.big, True)
            self.text(f"Score {self.score}   Served {self.served}", W // 2, 85, WHITE, center=True)
            self.text("Press Enter to play again", W // 2, 105, YELLOW, center=True)

        pygame.transform.scale(c, self.window.get_size(), self.window)
        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000
            for e in pygame.event.get():
                self.handle(e)
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()
