import pygame
import sys
import random
import math

# =========================================================================
# 1. INIT
# =========================================================================
pygame.init()
WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Trucker: Heavy Simulation Pro Edition")
clock = pygame.time.Clock()

# ── STRICT B&W PALETTE ────────────────────────────────────────────────────
BLACK   = (0,   0,   0  )
WHITE   = (255, 255, 255)
GRAY    = (120, 120, 120)
DGRAY   = (40,  40,  40 )
LGRAY   = (180, 180, 180)
MGRAY   = (80,  80,  80 )

FONT_SM = pygame.font.SysFont("Courier", 18)
FONT_MD = pygame.font.SysFont("Courier", 24)
FONT_LG = pygame.font.SysFont("Courier", 32)
FONT_XS = pygame.font.SysFont("Courier", 13)

game_state = 'MAIN_MENU'

# Developer Mode state
dev_mode = False

# Player Stats & Upgrades
credits_val    = 200  
max_fuel       = 250.0
fuel           = 250.0
max_hull       = 100.0
hull           = 100.0
throttle       = 0.0

# Cargo Hold
inventory = {"Metals": 0, "Food": 0, "Tech": 0}
max_cargo = 6  

engine_temp     = 0.0
engine_cooldown = False

world_x, world_y = 0.0, 0.0
player_angle     = 0.0
player_vx        = 0.0   
player_vy        = 0.0
turn_dir         = 0
strafe_dir       = 0

stars = []
for _ in range(200):
    stars.append({
        "x":      random.uniform(0, WIDTH),
        "y":      random.uniform(0, HEIGHT),
        "sf":     random.uniform(0.1, 1.0),
        "size":   random.choice([1, 1, 1, 2]),
        "bright": random.randint(60, 200),
    })

particles     = []  

# Warp animation variables
warp_timer = 0.0
warp_duration = 3.0

# =========================================================================
# STATIONS & ECONOMIC DATA
# =========================================================================
stations = [
    {"name": "Death Star Sector 01", "x": 4500, "y": -5000, "variant": 0, "prices": {"Metals": 55, "Food": 25, "Tech": 130}},
    {"name": "Sol Megastructure Echo", "x": -6000, "y": 4500, "variant": 1, "prices": {"Metals": 32, "Food": 35, "Tech": 90}},
    {"name": "Zeta Reticuli Outpost", "x": 7500, "y": 7000, "variant": 2, "prices": {"Metals": 48, "Food": 60, "Tech": 55}},
    {"name": "Orion Industrial Hub", "x": -4500, "y": -9500, "variant": 3, "prices": {"Metals": 12, "Food": 40, "Tech": 145}},
    {"name": "Imperial Core Station", "x": 9500, "y": -4000, "variant": 0, "prices": {"Metals": 60, "Food": 20, "Tech": 120}},
    {"name": "Kepler Dyson Depot", "x": -8000, "y": -6500, "variant": 1, "prices": {"Metals": 22, "Food": 50, "Tech": 110}},
]

def randomize_galaxy():
    """Generates new positions and prices for stations upon hyperspace jump."""
    global stations
    names = ["Death Star Sector 01", "Sol Megastructure Echo", "Zeta Reticuli Outpost", "Orion Industrial Hub", "Imperial Core Station", "Kepler Dyson Depot"]
    variants = [0, 1, 2, 3, 0, 1]
    stations = []
    for i in range(6):
        stations.append({
            "name": names[i],
            "x": random.randint(-12000, 12000),
            "y": random.randint(-12000, 12000),
            "variant": variants[i],
            "prices": {
                "Metals": random.randint(10, 70),
                "Food": random.randint(15, 65),
                "Tech": random.randint(50, 160)
            },
            "rot": random.uniform(0, 360)
        })

for st in stations:
    st["rot"] = 0.0

active_station = None

# =========================================================================
# RADIO SYSTEM
# =========================================================================
radio_messages_general = [
    "MARKET: Metal shortage reported in Death Star sector. Prices spiking!",
    "COMMS: Orion Hub reports record-breaking iron core yields.",
    "TOWER: Speed limit enforced near all stations. 120 m/s max.",
    "MARKET: Tech overproduction at Zeta Outpost. Prices dropping.",
]

current_radio_text  = "COMMS: Megastructure dimensions maximized. Dock safe."
radio_timer         = 0.0
blinking_timer      = 0.0

# =========================================================================
# DOCKING DATA
# =========================================================================
dock_ship_x, dock_ship_y = 60.0, float(HEIGHT // 2)
dock_vx, dock_vy         = 0.0, 0.0
dock_warning_flash   = 0.0
dock_landing_success = False

HANGAR_TOP = 190
HANGAR_BOT = 510
HANGAR_GRAVITY = 65.0  

dock_pads = {}
assigned_pad = None

def init_docking_bay():
    global dock_pads, assigned_pad
    assigned_pad = None
    dock_pads = {
        "01": {"x": 280, "y": HANGAR_TOP, "side": "top", "status": "FREE"},
        "02": {"x": 640, "y": HANGAR_TOP, "side": "top", "status": "FREE"},
        "03": {"x": 280, "y": HANGAR_BOT, "side": "bot", "status": "FREE"},
        "04": {"x": 640, "y": HANGAR_BOT, "side": "bot", "status": "FREE"}
    }
    pids = ["01", "02", "03", "04"]
    random.shuffle(pids)
    num_to_occupy = random.randint(1, 2)
    for i in range(num_to_occupy):
        dock_pads[pids[i]]["status"] = "OCCUPIED"

# =========================================================================
# UI HELPERS (BUTTON DRAWING & CLICK DETECTION)
# =========================================================================
def draw_ui_button(surface, rect, text, mouse_pos, active=False, flashing=False, flash_state=True):
    is_hovered = rect.collidepoint(mouse_pos)
    
    if active:
        bg_col = WHITE
        text_col = BLACK
    elif is_hovered:
        bg_col = MGRAY
        text_col = WHITE
    else:
        bg_col = DGRAY if not (flashing and not flash_state) else BLACK
        text_col = WHITE if not (flashing and not flash_state) else GRAY

    pygame.draw.rect(surface, bg_col, rect)
    pygame.draw.rect(surface, WHITE, rect, 1)
    
    txt_surf = FONT_SM.render(text, True, text_col)
    tx = rect.x + (rect.width - txt_surf.get_width()) // 2
    ty = rect.y + (rect.height - txt_surf.get_height()) // 2
    surface.blit(txt_surf, (tx, ty))
    return is_hovered

# Top Nav buttons
rect_btn_flight = pygame.Rect(10,  7, 150, 32)
rect_btn_market = pygame.Rect(170, 7, 170, 32)
rect_btn_map    = pygame.Rect(350, 7, 150, 32)

def draw_top_navigation_bar(surface, current_state, mouse_pos):
    pygame.draw.rect(surface, DGRAY, (0, 0, WIDTH, 46))
    pygame.draw.line(surface, WHITE, (0, 46), (WIDTH, 46), 2)
    
    draw_ui_button(surface, rect_btn_flight, "[1] FLIGHT SIM", mouse_pos, current_state == 'TRAVEL')
    draw_ui_button(surface, rect_btn_market, "[2] MARKET INDEX", mouse_pos, current_state == 'MARKET_INDEX')
    draw_ui_button(surface, rect_btn_map,    "[3] GALAXY MAP", mouse_pos, current_state == 'MAP')

# =========================================================================
# DRAW GIANT STATIONS (MEGASTRUCTURES)
# =========================================================================
def draw_station(surface, cx, cy, variant, rot, bt):
    R = 260 
    if variant == 0:
        pygame.draw.circle(surface, MGRAY, (cx, cy), R)
        pygame.draw.circle(surface, WHITE, (cx, cy), R, 2)
        pygame.draw.circle(surface, DGRAY, (cx - 90, cy - 90), 55)
        pygame.draw.circle(surface, WHITE, (cx - 90, cy - 90), 55, 2)
        pygame.draw.circle(surface, BLACK, (cx - 90, cy - 90), 15) 
        pygame.draw.line(surface, BLACK, (cx - R, cy), (cx + R, cy), 6)
        pygame.draw.line(surface, WHITE, (cx - R, cy - 3), (cx + R, cy - 3), 1)
        pygame.draw.line(surface, WHITE, (cx - R, cy + 3), (cx + R, cy + 3), 1)
        for i in range(-200, 250, 50):
            if i != 0:
                h = math.sqrt(max(0, R**2 - i**2))
                pygame.draw.line(surface, DGRAY, (int(cx - h), cy + i), (int(cx + h), cy + i), 1)
    elif variant == 1:
        pygame.draw.circle(surface, DGRAY, (cx, cy), R + 30, 45)
        pygame.draw.circle(surface, WHITE, (cx, cy), R + 30, 2)
        pygame.draw.circle(surface, WHITE, (cx, cy), R - 15, 2)
        pygame.draw.circle(surface, LGRAY, (cx, cy), 60)
        pygame.draw.circle(surface, WHITE, (cx, cy), 60, 3)
        for ang in range(0, 360, 30):
            a = math.radians(ang + rot * 5)
            x1 = cx + 60*math.cos(a); y1 = cy + 60*math.sin(a)
            x2 = cx + (R - 15)*math.cos(a); y2 = cy + (R - 15)*math.sin(a)
            pygame.draw.line(surface, GRAY, (int(x1), int(y1)), (int(x2), int(y2)), 2)
    elif variant == 2:
        points = []
        for i in range(6):
            angle = math.radians(i * 60 + rot * 4)
            points.append((cx + R * math.cos(angle), cy + R * math.sin(angle)))
        pygame.draw.polygon(surface, DGRAY, points)
        pygame.draw.polygon(surface, WHITE, points, 3)
        pygame.draw.circle(surface, MGRAY, (cx, cy), R // 2)
        pygame.draw.circle(surface, WHITE, (cx, cy), R // 2, 2)
        for pt in points:
            pygame.draw.line(surface, GRAY, (cx, cy), pt, 2)
    elif variant == 3:
        bw, bh = R * 1.5, R * 1.1
        pygame.draw.rect(surface, DGRAY, (cx - bw//2, cy - bh//2, bw, bh))
        pygame.draw.rect(surface, WHITE, (cx - bw//2, cy - bh//2, bw, bh), 3)
        pygame.draw.rect(surface, MGRAY, (cx - bw//3, cy - bh//2 - 40, 60, 40))
        pygame.draw.rect(surface, WHITE, (cx - bw//3, cy - bh//2 - 40, 60, 40), 2)
        pygame.draw.rect(surface, MGRAY, (cx + bw//3 - 60, cy - bh//2 - 40, 60, 40))
        pygame.draw.rect(surface, WHITE, (cx + bw//3 - 60, cy - bh//2 - 40, 60, 40), 2)
        for x_off in range(int(-bw//2) + 40, int(bw//2), 60):
            pygame.draw.line(surface, MGRAY, (cx + x_off, cy - bh//2), (cx + x_off, cy + bh//2), 2)

def draw_station_gate(surface, sx, sy, bt):
    gw, gh = 120, 24
    gx = sx - gw//2
    gy = sy + 120 
    pygame.draw.rect(surface, BLACK, (gx, gy, gw, gh))
    pygame.draw.rect(surface, WHITE, (gx, gy, gw, gh), 2)
    if (int(bt * 3) % 2 == 0):
        pygame.draw.rect(surface, LGRAY, (gx + 4, gy + 4, gw - 8, gh - 8), 1)
    txt = FONT_XS.render("MEGA DOCK BAY", True, WHITE)
    surface.blit(txt, (gx + (gw - txt.get_width())//2, gy + 4))

# =========================================================================
# 3. PLAYER SHIP & PARTICLES
# =========================================================================
def poly_transform(pts, cx, cy, angle):
    out = []
    for px, py in pts:
        rx = cx + px*math.cos(angle) - py*math.sin(angle)
        ry = cy + px*math.sin(angle) + py*math.cos(angle)
        out.append((rx, ry))
    return out

def draw_player_ship(surface, cx, cy, angle, thr, turn, strafe, bt):
    hull_pts = [
        (0,-30),(-6,-18),(-6,-7),(-15,-3),(-17,13),(-9,17),(-5,26),(5,26),(9,17),(17,13),(15,-3),(6,-7),(6,-18)
    ]
    rh = poly_transform(hull_pts, cx, cy, angle)
    pygame.draw.polygon(surface, DGRAY, rh)
    pygame.draw.polygon(surface, WHITE, rh, 2)

    if thr > 0.05:
        flicker = 0.85 + 0.15*math.sin(bt*28.0)
        base_len = thr * 24.0 * flicker
        for nozzle_off in [-7, 7]:
            base_pt = poly_transform([(nozzle_off, 26)], cx, cy, angle)[0]
            tip_m = poly_transform([(nozzle_off, 26 + base_len)], cx, cy, angle)[0]
            pygame.draw.line(surface, WHITE, base_pt, tip_m, 2)

def add_exhaust_particle(x, y, vx, vy):
    particles.append([x, y, vx + random.uniform(-10, 10), vy + random.uniform(-10, 10), random.uniform(0.15, 0.40)])

def update_and_draw_particles(surface, dt):
    for p in particles[:]:
        p[0] += p[2]*dt; p[1] += p[3]*dt; p[4] -= dt
        if p[4] <= 0: particles.remove(p); continue
        a = min(255, max(0, int(p[4] * 600)))
        pygame.draw.circle(surface, (a, a, a), (int(p[0]), int(p[1])), 2)

# =========================================================================
# HUD WINDOW LAYOUT COMPONENTS
# =========================================================================
HUD_X, HUD_Y, HUD_W, HUD_H = 10, 56, 280, 102
MM_X, MM_Y, MM_W, MM_H     = WIDTH-180, 56, 170, 115
RAD_X, RAD_Y, RAD_W, RAD_H = WIDTH-180, 178, 170, 92

def is_ship_maxed():
    """Checks if all ship systems are upgraded to their maximum values."""
    return max_fuel >= 450.0 and max_hull >= 200.0 and max_cargo >= 12

def draw_global_hud(surface):
    pygame.draw.rect(surface, BLACK, (HUD_X, HUD_Y, HUD_W, HUD_H))
    pygame.draw.rect(surface, WHITE, (HUD_X, HUD_Y, HUD_W, HUD_H), 1)
    hc = LGRAY if hull < (max_hull * 0.4) else WHITE
    fc = LGRAY if fuel < (max_fuel * 0.2) else WHITE
    surface.blit(FONT_SM.render(f"Credits: {credits_val} CR",     True, WHITE), (HUD_X+12, HUD_Y+12))
    surface.blit(FONT_SM.render(f"Fuel:    {int(fuel)}/{int(max_fuel)}L", True, fc), (HUD_X+12, HUD_Y+32))
    surface.blit(FONT_SM.render(f"Hull:    {int(hull)}/{int(max_hull)}%", True, hc), (HUD_X+12, HUD_Y+52))
    total_loaded_cargo = sum(inventory.values())
    surface.blit(FONT_SM.render(f"Cargo:   {total_loaded_cargo}/{max_cargo} T (M:{inventory['Metals']} F:{inventory['Food']} T:{inventory['Tech']})", True, LGRAY), (HUD_X+12, HUD_Y+74))
    
    # Dev mode visual indicator
    if dev_mode:
        if (int(blinking_timer * 5) % 2 == 0):
            surface.blit(FONT_SM.render("[DEV MODE ACTIVE]", True, WHITE), (HUD_X + 115, HUD_Y + 12))

def draw_minimap(surface):
    mm = pygame.Surface((MM_W, MM_H), pygame.SRCALPHA)
    mm.fill((0, 0, 0, 200))
    pygame.draw.rect(mm, GRAY, (0, 0, MM_W, MM_H), 1)
    cx4, cy4 = MM_W//2, MM_H//2
    for st in stations:
        rx = cx4 + int((st["x"]-world_x) * 0.005)
        ry = cy4 + int((st["y"]-world_y) * 0.005)
        if 2 <= rx <= MM_W-2 and 2 <= ry <= MM_H-2:
            pygame.draw.circle(mm, WHITE, (rx, ry), 4)
    pygame.draw.circle(mm, WHITE, (cx4, cy4), 2)
    surface.blit(mm, (MM_X, MM_Y))

def draw_radio_widget(surface):
    pygame.draw.rect(surface, BLACK, (RAD_X, RAD_Y, RAD_W, RAD_H))
    pygame.draw.rect(surface, GRAY, (RAD_X, RAD_Y, RAD_W, RAD_H), 1)
    surface.blit(FONT_XS.render("MARKET FEEDS", True, LGRAY), (RAD_X+6, RAD_Y+6))
    words = current_radio_text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= 20: cur += (" " if cur else "") + w
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    for i, line in enumerate(lines[:3]):
        surface.blit(FONT_XS.render(line, True, WHITE), (RAD_X+6, RAD_Y+24+i*15))

def draw_hud_gauges(surface):
    bx, by, bw, bh = 20, 175, 22, 180  
    pygame.draw.rect(surface, WHITE, (bx, by, bw, bh), 2)
    fh = int(bh * throttle)
    if fh > 0: pygame.draw.rect(surface, WHITE, (bx+2, by+bh-fh, bw-4, fh))
    surface.blit(FONT_SM.render("THR", True, WHITE), (bx-4, by-42))

    tx, ty = 20, 415  
    pygame.draw.rect(surface, WHITE, (tx, ty, bw, bh), 2)
    th = int(bh * (engine_temp / 100.0))
    if th > 0: pygame.draw.rect(surface, GRAY, (tx+2, ty+bh-th, bw-4, th))
    surface.blit(FONT_SM.render("TEMP", True, WHITE), (tx-6, ty-42))

def draw_ticker_footer(surface):
    pygame.draw.rect(surface, BLACK, (10, HEIGHT-50, WIDTH-20, 40))
    pygame.draw.rect(surface, WHITE, (10, HEIGHT-50, WIDTH-20, 40), 1)
    
    if dev_mode or is_ship_maxed():
        # Shaking jitter effect
        shake_x = random.randint(-3, 3)
        shake_y = random.randint(-2, 2)
        if (int(blinking_timer * 6) % 2 == 0):
            txt = FONT_MD.render(">> READY FOR HYPERSPACE! PRESS [F4] TO WARP NOW <<", True, WHITE)
            surface.blit(txt, (WIDTH // 2 - txt.get_width() // 2 + shake_x, HEIGHT - 42 + shake_y))
        else:
            surface.blit(FONT_SM.render(current_radio_text, True, GRAY), (20, HEIGHT-40))
    else:
        surface.blit(FONT_SM.render(current_radio_text, True, WHITE), (20, HEIGHT-40))

# =========================================================================
# 7. MAIN GAME LOOP
# =========================================================================
running = True
while running:
    dt = min(clock.tick(60) / 1000.0, 0.05)
    blinking_timer   += dt; radio_timer      += dt
    mouse_pos = pygame.mouse.get_pos()
    flash_state = (int(blinking_timer * 4) % 2 == 0)

    if radio_timer > 9.0:
        if game_state in ['TRAVEL', 'MAIN_MENU', 'MAP', 'MARKET_INDEX']:
            current_radio_text = random.choice(radio_messages_general)
        radio_timer = 0.0

    total_loaded_cargo = sum(inventory.values())

    # Developer Mode Permanent Enforcement
    if dev_mode:
        credits_val = 999999
        fuel = max_fuel
        hull = max_hull
        engine_temp = 0.0

    # ── EVENT INTERFACE MATRIX ───────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state == 'MAIN_MENU':
                if pygame.Rect(280, 250, 320, 40).collidepoint(mouse_pos): game_state = 'TRAVEL'
                elif pygame.Rect(280, 310, 320, 40).collidepoint(mouse_pos): game_state = 'SHOP_MENU'
                elif pygame.Rect(280, 370, 320, 40).collidepoint(mouse_pos): running = False
            
            elif game_state == 'SHOP_MENU':
                if pygame.Rect(100, 230, 680, 35).collidepoint(mouse_pos) and (credits_val >= 80 or dev_mode) and max_fuel < 450.0:
                    if not dev_mode: credits_val -= 80
                    max_fuel += 50.0; fuel = max_fuel
                elif pygame.Rect(100, 290, 680, 35).collidepoint(mouse_pos) and (credits_val >= 100 or dev_mode) and max_hull < 200.0:
                    if not dev_mode: credits_val -= 100
                    max_hull += 25.0; hull = max_hull
                elif pygame.Rect(100, 350, 680, 35).collidepoint(mouse_pos) and (credits_val >= 120 or dev_mode) and max_cargo < 12:
                    if not dev_mode: credits_val -= 120
                    max_cargo += 2
                elif pygame.Rect(100, 500, 400, 40).collidepoint(mouse_pos): game_state = 'MAIN_MENU'

            elif game_state == 'DOCKING':
                if assigned_pad is None and pygame.Rect(220, 110, 380, 35).collidepoint(mouse_pos):
                    free_options = [pid for pid, p in dock_pads.items() if p["status"] == "FREE"]
                    if free_options:
                        assigned_pad = random.choice(free_options)
                        current_radio_text = f"TOWER: Clear to land at Pad [{assigned_pad}]."

            elif game_state == 'STATION_MENU' and active_station:
                p_map = active_station["prices"]
                if pygame.Rect(650, 155, 110, 28).collidepoint(mouse_pos) and (credits_val >= 20 or dev_mode) and fuel < max_fuel:
                    if not dev_mode: credits_val -= 20
                    fuel = max_fuel
                elif pygame.Rect(650, 190, 110, 28).collidepoint(mouse_pos) and (credits_val >= 30 or dev_mode) and hull < max_hull:
                    if not dev_mode: credits_val -= 30
                    hull = max_hull
                elif pygame.Rect(450, 356, 80, 26).collidepoint(mouse_pos):  
                    if total_loaded_cargo < max_cargo and (credits_val >= p_map["Metals"] or dev_mode):
                        if not dev_mode: credits_val -= p_map["Metals"]
                        inventory["Metals"] += 1
                elif pygame.Rect(540, 356, 80, 26).collidepoint(mouse_pos):  
                    if inventory["Metals"] > 0:
                        if not dev_mode: credits_val += p_map["Metals"]
                        inventory["Metals"] -= 1
                elif pygame.Rect(450, 396, 80, 26).collidepoint(mouse_pos):  
                    if total_loaded_cargo < max_cargo and (credits_val >= p_map["Food"] or dev_mode):
                        if not dev_mode: credits_val -= p_map["Food"]
                        inventory["Food"] += 1
                elif pygame.Rect(540, 396, 80, 26).collidepoint(mouse_pos):  
                    if inventory["Food"] > 0:
                        if not dev_mode: credits_val += p_map["Food"]
                        inventory["Food"] -= 1
                elif pygame.Rect(450, 436, 80, 26).collidepoint(mouse_pos):  
                    if total_loaded_cargo < max_cargo and (credits_val >= p_map["Tech"] or dev_mode):
                        if not dev_mode: credits_val -= p_map["Tech"]
                        inventory["Tech"] += 1
                elif pygame.Rect(540, 436, 80, 26).collidepoint(mouse_pos):  
                    if inventory["Tech"] > 0:
                        if not dev_mode: credits_val += p_map["Tech"]
                        inventory["Tech"] -= 1
                elif pygame.Rect(250, 610, 400, 40).collidepoint(mouse_pos):
                    game_state = 'TRAVEL'; throttle = 0.0
                    player_vx += 200 * math.sin(player_angle); player_vy -= 200 * math.cos(player_angle)

            if game_state in ['TRAVEL', 'MAP', 'MARKET_INDEX']:
                if rect_btn_flight.collidepoint(mouse_pos): game_state = 'TRAVEL'
                elif rect_btn_market.collidepoint(mouse_pos): game_state = 'MARKET_INDEX'
                elif rect_btn_map.collidepoint(mouse_pos): game_state = 'MAP'

        if event.type == pygame.KEYDOWN:
            # DEV MODE TOGGLE BUTTON F3
            if event.key == pygame.K_F3:
                dev_mode = not dev_mode
                if dev_mode:
                    current_radio_text = "DEV: Developer mode ENGAGED. Godmode activated."
                else:
                    credits_val = 200
                    current_radio_text = "DEV: Developer mode DISENGAGED. Simulation normalized."

            # HYPERSPACE WARP INITIATOR F4
            if event.key == pygame.K_F4 and (game_state in ['TRAVEL', 'MAP', 'MARKET_INDEX']):
                if dev_mode or is_ship_maxed():
                    game_state = 'WARP'
                    warp_timer = 0.0
                    current_radio_text = "WARP: Hyperspace sequence initialized... Sub-space fold open."

            if game_state in ['TRAVEL', 'MAP', 'MARKET_INDEX']:
                if event.key == pygame.K_1: game_state = 'TRAVEL'
                elif event.key == pygame.K_2: game_state = 'MARKET_INDEX'
                elif event.key == pygame.K_3: game_state = 'MAP'

            if game_state == 'MAIN_MENU' and event.key == pygame.K_RETURN: game_state = 'TRAVEL'
            elif game_state == 'TRAVEL' and event.key == pygame.K_e and active_station:
                game_state = 'DOCKING'; dock_ship_x = 60.0; dock_ship_y = float(HEIGHT // 2)
                dock_vx, dock_vy = 0.0, 0.0; dock_landing_success = False; init_docking_bay()
            elif game_state == 'DOCKING' and event.key == pygame.K_ESCAPE: game_state = 'TRAVEL'

    keys = pygame.key.get_pressed()

    # ======================================================================
    # TRAVEL SIMULATOR PHYSICS
    # ======================================================================
    if game_state == 'TRAVEL':
        turn_dir, strafe_dir = 0, 0
        if engine_cooldown:
            throttle = max(0.0, throttle - 2.0*dt); engine_temp = max(0.0, engine_temp - 25.0*dt)
            if engine_temp <= 20.0: engine_cooldown = False
        else:
            if keys[pygame.K_w]: throttle = min(1.0, throttle + 1.2*dt)
            if keys[pygame.K_s]: throttle = max(0.0, throttle - 1.2*dt)

        if throttle > 0.75:
            engine_temp += throttle * 32.0 * dt
            if engine_temp >= 100.0: engine_temp = 100.0; engine_cooldown = True
        else: engine_temp = max(0.0, engine_temp - 12.0*dt)

        if keys[pygame.K_LEFT]: player_angle -= 3.0 * dt; turn_dir = -1
        if keys[pygame.K_RIGHT]: player_angle += 3.0 * dt; turn_dir = 1

        fx, fy = math.sin(player_angle), -math.cos(player_angle)
        player_vx += fx * throttle * 280.0 * dt; player_vy += fy * throttle * 280.0 * dt

        sx2, sy2 = math.cos(player_angle), math.sin(player_angle)
        if keys[pygame.K_a] and (fuel > 0 or dev_mode):
            player_vx -= sx2 * 140 * dt; player_vy -= sy2 * 140 * dt; fuel -= 0.6 * dt; strafe_dir = -1
        if keys[pygame.K_d] and (fuel > 0 or dev_mode):
            player_vx += sx2 * 140 * dt; player_vy += sy2 * 140 * dt; fuel -= 0.6 * dt; strafe_dir = 1

        if not keys[pygame.K_a] and not keys[pygame.K_d]:
            side_vel = player_vx * sx2 + player_vy * sy2
            damp_amount = side_vel * 0.8 * dt
            player_vx -= sx2 * damp_amount; player_vy -= sy2 * damp_amount

        spd = math.hypot(player_vx, player_vy)
        if spd > 380.0: player_vx = (player_vx / spd) * 380.0; player_vy = (player_vy / spd) * 380.0

        if fuel > 0 or spd > 0 or dev_mode:
            world_x += player_vx * dt; world_y += player_vy * dt
            if throttle > 0 or strafe_dir != 0: fuel -= (0.4 + throttle * 2.8) * dt

        for star in stars:
            star["x"] -= player_vx * dt * star["sf"] * 0.4; star["y"] -= player_vy * dt * star["sf"] * 0.4
            if star["x"] < 0:      star["x"] += WIDTH
            if star["x"] > WIDTH:  star["x"] -= WIDTH
            if star["y"] < 0:      star["y"] += HEIGHT
            if star["y"] > HEIGHT: star["y"] -= HEIGHT

        if throttle > 0.1 and (fuel > 0 or dev_mode) and random.random() < 0.5:
            add_exhaust_particle(WIDTH//2 - fx*25, HEIGHT//2 - fy*25, -fx*80, -fy*80)

        for st in stations: st["rot"] = (st["rot"] + 0.5*dt) % 360.0

        active_station = None
        for st in stations:
            if math.hypot(world_x - st["x"], world_y - st["y"]) < 380:
                active_station = st

    # ======================================================================
    # HYPERSPACE WARP ANIMATION CORE
    # ======================================================================
    elif game_state == 'WARP':
        warp_timer += dt
        for star in stars:
            star["x"] += (star["x"] - WIDTH//2) * 5.0 * dt
            star["y"] += (star["y"] - HEIGHT//2) * 5.0 * dt
            if star["x"] < 0 or star["x"] > WIDTH or star["y"] < 0 or star["y"] > HEIGHT:
                star["x"] = random.uniform(WIDTH//2 - 20, WIDTH//2 + 20)
                star["y"] = random.uniform(HEIGHT//2 - 20, HEIGHT//2 + 20)

        if warp_timer >= warp_duration:
            randomize_galaxy()
            world_x, world_y = 0.0, 0.0
            player_vx, player_vy = 0.0, 0.0
            throttle = 0.0
            game_state = 'TRAVEL'
            current_radio_text = "GALAXY: Shift Complete. Arrived at new unmapped cluster sector."

    # ======================================================================
    # DOCKING PHYSICS
    # ======================================================================
    elif game_state == 'DOCKING':
        dock_vy += HANGAR_GRAVITY * dt
        if keys[pygame.K_w] and (fuel > 0 or dev_mode): dock_vy -= 220 * dt; fuel -= 0.8 * dt
        if keys[pygame.K_s] and (fuel > 0 or dev_mode): dock_vy += 160 * dt; fuel -= 0.8 * dt
        if keys[pygame.K_a] and (fuel > 0 or dev_mode): dock_vx -= 190 * dt; fuel -= 0.8 * dt
        if keys[pygame.K_d] and (fuel > 0 or dev_mode): dock_vx += 190 * dt; fuel -= 0.8 * dt

        dock_vx *= (1.0 - 1.2 * dt); dock_vy *= (1.0 - 1.0 * dt)
        dock_ship_x += dock_vx * dt; dock_ship_y += dock_vy * dt

        if dock_ship_x < 45:  dock_ship_x = 45.0; dock_vx = 0
        if dock_ship_x > WIDTH - 45: dock_ship_x = WIDTH - 45.0; dock_vx = 0
        if dock_ship_y < HANGAR_TOP + 15: dock_ship_y = HANGAR_TOP + 15.0; dock_vy = 0
        if dock_ship_y > HANGAR_BOT - 15: dock_ship_y = HANGAR_BOT - 15.0; dock_vy = 0

        p_rect = pygame.Rect(dock_ship_x - 22, dock_ship_y - 13, 44, 26)
        for pid, pad in dock_pads.items():
            if pad["status"] == "OCCUPIED":
                t_rect = pygame.Rect(pad["x"] - 37, pad["y"], 74, 34) if pad["side"] == "top" else pygame.Rect(pad["x"] - 37, pad["y"] - 34, 74, 34)
                if p_rect.colliderect(t_rect):
                    if not dev_mode: hull = max(0.0, hull - 20.0)
                    current_radio_text = "TOWER: HANGAR IMPACT WARNING!"
                    dock_vx = -140 if dock_ship_x < pad["x"] else 140
                    dock_vy = 140 if pad["side"] == "top" else -140
                    if hull <= 0: hull = max_hull; credits_val = max(0, credits_val - 40); game_state = 'MAIN_MENU'

        if assigned_pad:
            pad = dock_pads[assigned_pad]
            if abs(dock_ship_x - pad["x"]) < 20:
                aligned = False
                if pad["side"] == "top" and abs(dock_ship_y - (HANGAR_TOP + 18)) < 8: aligned = True
                elif pad["side"] == "bot" and abs(dock_ship_y - (HANGAR_BOT - 18)) < 8: aligned = True
                if aligned:
                    if math.hypot(dock_vx, dock_vy) < 45 or dev_mode: dock_landing_success = True; game_state = 'STATION_MENU'
                    else: dock_warning_flash = 0.2
        if dock_warning_flash > 0: dock_warning_flash -= dt

    # ======================================================================
    # RENDERING ENGINE
    # ======================================================================
    screen.fill(BLACK)

    if game_state == 'MAIN_MENU':
        screen.blit(FONT_LG.render("=== SPACE TRUCKER: SIMULATOR ===", True, WHITE), (160, 160))
        draw_ui_button(screen, pygame.Rect(280, 250, 320, 40), "LAUNCH SIMULATION", mouse_pos)
        draw_ui_button(screen, pygame.Rect(280, 310, 320, 40), "SHIP UPGRADE SHOP", mouse_pos)
        draw_ui_button(screen, pygame.Rect(280, 370, 320, 40), "EXIT SIMULATOR", mouse_pos)

    elif game_state == 'SHOP_MENU':
        screen.blit(FONT_LG.render("=== MAIN SHIP UPGRADE SHOP ===", True, WHITE), (180, 60))
        screen.blit(FONT_MD.render(f"Available Balance: {credits_val} CR", True, WHITE), (100, 140))
        
        draw_ui_button(screen, pygame.Rect(100, 230, 680, 35), f"Upgrade Fuel Tank (Max: {int(max_fuel)}L) -> Cost: 80 CR", mouse_pos)
        draw_ui_button(screen, pygame.Rect(100, 290, 680, 35), f"Reinforce Hull Plating (Max: {int(max_hull)}%) -> Cost: 100 CR", mouse_pos)
        
        cargo_txt = f"Expand Cargo Hold Capacity (Max: {max_cargo}T) -> Cost: 120 CR" if max_cargo < 12 else "Cargo Hold Capacity Maxed Out (12T)"
        draw_ui_button(screen, pygame.Rect(100, 350, 680, 35), cargo_txt, mouse_pos)
        
        draw_ui_button(screen, pygame.Rect(100, 500, 250, 40), "RETURN TO MENU", mouse_pos)

    elif game_state == 'TRAVEL':
        draw_top_navigation_bar(screen, game_state, mouse_pos)
        for star in stars:
            c5 = star["bright"]
            pygame.draw.circle(screen, (c5, c5, c5), (int(star["x"]), int(star["y"])), star["size"])

        update_and_draw_particles(screen, dt)
        
        for st in stations:
            sx3, sy3 = int(WIDTH//2 + (st["x"] - world_x)), int(HEIGHT//2 + (st["y"] - world_y))
            if -500 <= sx3 <= WIDTH+500 and -500 <= sy3 <= HEIGHT+500:
                pygame.draw.circle(screen, MGRAY, (sx3, sy3), 360, 1)
                draw_station(screen, sx3, sy3, st["variant"], st["rot"], blinking_timer)
                draw_station_gate(screen, sx3, sy3, blinking_timer)
                screen.blit(FONT_MD.render(st["name"], True, WHITE), (sx3 - 120, sy3 - 310))

        draw_player_ship(screen, WIDTH//2, HEIGHT//2, player_angle, throttle, turn_dir, strafe_dir, blinking_timer)
        draw_hud_gauges(screen); draw_global_hud(screen); draw_minimap(screen); draw_radio_widget(screen)

    elif game_state == 'WARP':
        for star in stars:
            pygame.draw.line(screen, WHITE, (int(star["x"]), int(star["y"])), 
                             (int(star["x"] - (star["x"] - WIDTH//2)*0.1), int(star["y"] - (star["y"] - HEIGHT//2)*0.1)), 2)
        flash_val = int(abs(math.sin(blinking_timer * 15)) * 40)
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((flash_val, flash_val, flash_val))
        screen.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        
        txt_w = FONT_LG.render(">>> HYPERSPACE WARP ACTIVE <<<", True, WHITE)
        screen.blit(txt_w, (WIDTH//2 - txt_w.get_width()//2, HEIGHT//2 - 20))

    elif game_state == 'MAP':
        draw_top_navigation_bar(screen, game_state, mouse_pos)
        screen.blit(FONT_MD.render("GALAXY POSITION NAVIGATOR", True, WHITE), (300, 70))
        scale6 = 0.018
        for st in stations:
            mx6, my6 = int(WIDTH//2 + (st["x"] - world_x)*scale6), int(HEIGHT//2 + (st["y"] - world_y)*scale6)
            pygame.draw.circle(screen, WHITE, (mx6, my6), 6, 2)
            screen.blit(FONT_XS.render(st["name"][:16], True, WHITE), (mx6+10, my6-5))
        pygame.draw.circle(screen, WHITE, (WIDTH//2, HEIGHT//2), 4)

    elif game_state == 'MARKET_INDEX':
        draw_top_navigation_bar(screen, game_state, mouse_pos)
        screen.blit(FONT_MD.render("GALACTIC REAL-TIME COMMODITY INDEX", True, WHITE), (240, 70))
        
        gy = 130
        for st in stations:
            pygame.draw.rect(screen, DGRAY, (40, gy, WIDTH-80, 40))
            pygame.draw.rect(screen, WHITE, (40, gy, WIDTH-80, 40), 1)
            screen.blit(FONT_XS.render(f"{st['name']:24}", True, WHITE), (60, gy+12))
            p_str = f"METALS: {st['prices']['Metals']:3d} CR | FOOD: {st['prices']['Food']:3d} CR | TECH: {st['prices']['Tech']:3d} CR"
            screen.blit(FONT_SM.render(p_str, True, LGRAY), (320, gy+10))
            gy += 48

    elif game_state == 'DOCKING':
        pygame.draw.line(screen, WHITE, (40, HANGAR_TOP), (WIDTH, HANGAR_TOP), 3)
        pygame.draw.line(screen, WHITE, (40, HANGAR_BOT), (WIDTH, HANGAR_BOT), 3)
        for dec_x in range(120, WIDTH, 160): pygame.draw.line(screen, DGRAY, (dec_x, HANGAR_TOP+2), (dec_x, HANGAR_BOT-2), 1)

        for pid, pad in dock_pads.items():
            is_top = (pad["side"] == "top")
            px, py = pad["x"], pad["y"]
            y_off = 10 if is_top else -10
            pygame.draw.rect(screen, DGRAY, (px-45, py, 90, y_off))
            pygame.draw.line(screen, WHITE, (px-45, py+y_off), (px+45, py+y_off), 2)
            col_lbl = WHITE
            if pid == assigned_pad:
                col_lbl = WHITE if flash_state else GRAY
                pygame.draw.circle(screen, col_lbl, (px, py + (24 if is_top else -24)), 4)
            screen.blit(FONT_MD.render(f"P{pid}", True, col_lbl), (px-15, py + 12 if is_top else py - 26))
            if pad["status"] == "OCCUPIED":
                sh_y = py if is_top else py - 24
                pygame.draw.rect(screen, MGRAY, (px - 34, sh_y, 68, 24))
                pygame.draw.rect(screen, LGRAY, (px - 34, sh_y, 68, 24), 2)

        update_and_draw_particles(screen, dt)
        sx, sy = int(dock_ship_x), int(dock_ship_y)
        pygame.draw.rect(screen, DGRAY, (sx-22, sy-13, 44, 26)); pygame.draw.rect(screen, WHITE, (sx-22, sy-13, 44, 26), 2)

        screen.blit(FONT_LG.render("DOCKING NAVIGATION CHANNEL", True, WHITE), (220, 45))
        
        if assigned_pad:
            screen.blit(FONT_MD.render(f"ASSIGNED ZONE: PAD {assigned_pad} | GRAVITY ACTIVE", True, WHITE), (50, 115))
        else:
            draw_ui_button(screen, pygame.Rect(220, 110, 380, 35), "CONTACT TOWER: ALLOCATE PAD", mouse_pos, flashing=True, flash_state=flash_state)

        if dock_warning_flash > 0 and flash_state:
            screen.blit(FONT_MD.render("!! DECREASE APPROACH SPEED !!", True, WHITE), (WIDTH//2-160, HEIGHT//2 - 10))

    elif game_state == 'STATION_MENU':
        nm = active_station['name'] if active_station else 'MEGASTRUCTURE TERMINAL'
        p_map = active_station["prices"] if active_station else {"Metals":0, "Food":0, "Tech":0}
        
        screen.blit(FONT_LG.render(f"STATION HIGH-DOCK: {nm}", True, WHITE), (60, 40))
        pygame.draw.line(screen, WHITE, (50, 90), (850, 90), 2)
        
        screen.blit(FONT_MD.render("STATION LOGISTICS & REPAIRS:", True, WHITE), (60, 115))
        screen.blit(FONT_SM.render(f"Fuel Reserve: {int(fuel)}/{int(max_fuel)}L      Hull Plating Integrity: {int(hull)}%", True, LGRAY), (80, 155))
        draw_ui_button(screen, pygame.Rect(650, 155, 110, 28), "REFUEL (20)", mouse_pos, active=(fuel>=max_fuel))
        draw_ui_button(screen, pygame.Rect(650, 190, 110, 28), "REPAIR (30)", mouse_pos, active=(hull>=max_hull))
        
        screen.blit(FONT_MD.render("LOCAL COMMODITY COMMERCE TERMINAL:", True, WHITE), (60, 250))
        pygame.draw.rect(screen, DGRAY, (60, 295, 780, 200))
        pygame.draw.rect(screen, WHITE, (60, 295, 780, 200), 1)
        
        screen.blit(FONT_SM.render("COMMODITY      MARKET PRICE    ORDER ACTIONS", True, LGRAY), (80, 310))
        pygame.draw.line(screen, GRAY, (80, 330), (820, 330), 1)
        
        commodities_meta = [("Heavy Metals", "Metals", 350), ("Hydro Food", "Food", 390), ("Cyber Tech", "Tech", 430)]
        for label, key, y in commodities_meta:
            screen.blit(FONT_SM.render(f"{label:15} {p_map[key]:3d} CR / Ton", True, WHITE), (80, y+4))
            draw_ui_button(screen, pygame.Rect(450, y, 80, 26), "BUY", mouse_pos)
            draw_ui_button(screen, pygame.Rect(540, y, 80, 26), "SELL", mouse_pos)
        
        screen.blit(FONT_MD.render(f"Cargo Bay Loading Ledger: {total_loaded_cargo} / {max_cargo} Tons Inventory Loaded", True, WHITE), (60, 520))
        screen.blit(FONT_SM.render(f"Current Cargo Hold Manifest -> Metals: {inventory['Metals']} | Food: {inventory['Food']} | Tech: {inventory['Tech']}", True, LGRAY), (60, 550))
        
        draw_ui_button(screen, pygame.Rect(250, 610, 400, 40), "UNDOCK CARGO VESSEL INTO SPACE", mouse_pos)

    if game_state in ['TRAVEL', 'DOCKING', 'MAP', 'MARKET_INDEX']:
        draw_ticker_footer(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()