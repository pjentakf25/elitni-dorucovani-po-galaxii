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

# All "color" aliases now map to grayscale
GREEN  = WHITE
RED    = LGRAY
YELLOW = WHITE
CYAN   = LGRAY
ORANGE = GRAY
BLUE   = DGRAY
PURPLE = MGRAY

FONT_SM = pygame.font.SysFont("Courier", 18)
FONT_MD = pygame.font.SysFont("Courier", 24)
FONT_LG = pygame.font.SysFont("Courier", 32)
FONT_XS = pygame.font.SysFont("Courier", 13)

game_state = 'MAIN_MENU'

credits_val = 100
max_fuel    = 250.0
fuel        = 250.0
hull        = 100.0
cargo       = None
throttle    = 0.0

engine_temp     = 0.0
engine_cooldown = False

world_x, world_y = 0.0, 0.0
player_angle     = 0.0
player_vx        = 0.0   # actual velocity vector (inertia)
player_vy        = 0.0
turn_dir         = 0
strafe_dir       = 0

player_queue_position = -1
queue_timer           = 0.0

stars = []
for _ in range(200):
    stars.append({
        "x":      random.uniform(0, WIDTH),
        "y":      random.uniform(0, HEIGHT),
        "sf":     random.uniform(0.1, 1.0),
        "size":   random.choice([1, 1, 1, 2]),
        "bright": random.randint(60, 200),
    })

particles     = []  # engine exhaust
rcs_particles = []  # RCS puffs

# =========================================================================
# STATIONS
# =========================================================================
stations = [
    {"name": "Alfa Centauri Prime",   "x":  3500, "y": -4000, "variant": 0, "pad_id": "DOCK-01"},
    {"name": "Sol Station Echo",      "x": -5000, "y":  3000, "variant": 1, "pad_id": "DOCK-02"},
    {"name": "Zeta Reticuli Outpost", "x":  6000, "y":  5500, "variant": 2, "pad_id": "DOCK-03"},
    {"name": "Orion Mining Hub",      "x": -2500, "y": -7500, "variant": 3, "pad_id": "DOCK-04"},
    {"name": "Sirius Junction",       "x":  7500, "y": -3000, "variant": 0, "pad_id": "DOCK-05"},
    {"name": "Kepler Depot",          "x": -6000, "y": -4500, "variant": 2, "pad_id": "DOCK-06"},
]

QUEUE_SPACING = 55.0
QUEUE_SPEED   = 18.0
GATE_PASS_T   = 4.5

for st in stations:
    st["queue_ships"] = [40.0, 95.0, 150.0, 205.0]
    st["rot"] = 0.0

active_station = None

# =========================================================================
# RADIO SYSTEM
# =========================================================================
radio_messages_general = [
    "COMMS: Gravitational anomaly near sector G-14. Reduce speed.",
    "COMMS: Engine temp warning above 70C. Throttle back.",
    "TOWER: All vessels — file cargo manifest on channel 7.",
    "COMMS: Debris field reported in outer belt. Stay alert.",
    "COMMS: RCS thrusters nominal across all docking corridors.",
    "TOWER: Speed limit enforced near all stations. 120 m/s max.",
]

current_radio_text  = "COMMS: System online. All frequencies clear."
radio_secondary     = ""          # docking hint line
radio_timer         = 0.0
radio_icon_phase    = 0.0         # for animated radio icon
blinking_timer      = 0.0

def make_dock_hint(st_name, queue_pos):
    pad = next((s["pad_id"] for s in stations if s["name"] == st_name), "DOCK-??")
    if queue_pos == 0:
        return f"TOWER: {st_name[:16]} — [{pad}] READY. Press [E] to enter."
    elif queue_pos > 0:
        return f"TOWER: {st_name[:16]} — [{pad}] Queue pos: {queue_pos}. Standby."
    else:
        return f"TOWER: {st_name[:16]} approaching. Reduce speed, join queue."

# =========================================================================
# DOCKING
# =========================================================================
dock_ship_x, dock_ship_y = float(WIDTH // 2), 120.0
dock_vx, dock_vy         = 0.0, 0.0
GRAVITY = 55.0                   # gentler gravity for better feel
dock_traffic_ships   = []
dock_interior        = []
dock_warning_flash   = 0.0
dock_landing_success = False

def gen_dock_interior():
    global dock_interior
    dock_interior = []
    for xi in [80, 220, 450, 680, 820]:
        dock_interior.append({"type": "column", "x": xi})
    for xi in range(40, WIDTH - 40, 70):
        dock_interior.append({"type": "floor_light", "x": xi, "phase": random.uniform(0, 2)})
    for yi in [210, 370, 530]:
        dock_interior.append({"type": "panel", "x": 8,        "y": yi})
        dock_interior.append({"type": "panel", "x": WIDTH-55, "y": yi})
    for xi in range(140, WIDTH - 140, 120):
        dock_interior.append({"type": "crane", "x": xi})

def gen_dock_traffic():
    global dock_traffic_ships
    dock_traffic_ships = []
    berths = [
        {"x": 180,       "y": 148,          "label": "A1", "side": "top"},
        {"x": WIDTH-180, "y": 148,          "label": "A2", "side": "top"},
        {"x": 180,       "y": HEIGHT-178,   "label": "B1", "side": "bot"},
        {"x": WIDTH-180, "y": HEIGHT-178,   "label": "B2", "side": "bot"},
    ]
    for k in berths:
        k["occupied"] = random.random() > 0.35
        k["type"]     = "BERTH"
        k["blink"]    = random.uniform(0, 2.0)
        dock_traffic_ships.append(k)
    gen_dock_interior()

# =========================================================================
# 2. DRAW STATIONS — B&W, 4 variants
# =========================================================================
def draw_station(surface, cx, cy, variant, rot, bt):
    def rot_pt(px, py, a):
        return (cx + px*math.cos(a) - py*math.sin(a),
                cy + px*math.sin(a) + py*math.cos(a))

    if variant == 0:
        # Toroidal ring station
        pygame.draw.circle(surface, LGRAY, (cx, cy), 42, 2)
        pygame.draw.circle(surface, DGRAY, (cx, cy), 42, 1)
        pygame.draw.circle(surface, MGRAY, (cx, cy), 16)
        pygame.draw.circle(surface, WHITE, (cx, cy), 16, 2)
        for ang in [0, 60, 120, 180, 240, 300]:
            a = math.radians(ang + rot * 20)
            x1 = cx + 17*math.cos(a); y1 = cy + 17*math.sin(a)
            x2 = cx + 39*math.cos(a); y2 = cy + 39*math.sin(a)
            pygame.draw.line(surface, GRAY, (int(x1), int(y1)), (int(x2), int(y2)), 1)
        for ang in [90, 270]:
            a = math.radians(ang + rot * 20)
            base = (cx + 42*math.cos(a), cy + 42*math.sin(a))
            tip  = (cx + 82*math.cos(a), cy + 82*math.sin(a))
            pw = 30
            pax = -math.sin(a)*pw/2; pay = math.cos(a)*pw/2
            pts = [(base[0]+pax, base[1]+pay),(base[0]-pax, base[1]-pay),
                   (tip[0]-pax,  tip[1]-pay), (tip[0]+pax,  tip[1]+pay)]
            pygame.draw.polygon(surface, DGRAY, pts)
            pygame.draw.polygon(surface, GRAY, pts, 1)
            for fi in [0.33, 0.66]:
                mx = base[0] + (tip[0]-base[0])*fi
                my = base[1] + (tip[1]-base[1])*fi
                pygame.draw.line(surface, MGRAY,
                                 (int(mx+pax), int(my+pay)),
                                 (int(mx-pax), int(my-pay)), 1)
        # Nav lights
        for ang in [0, 90, 180, 270]:
            a   = math.radians(ang + rot * 20)
            lx  = int(cx + 44*math.cos(a))
            ly  = int(cy + 44*math.sin(a))
            lc  = WHITE if int(bt*2 + ang*0.02)%2 == 0 else DGRAY
            pygame.draw.circle(surface, lc, (lx, ly), 3)

    elif variant == 1:
        # Cylindrical industrial
        pygame.draw.rect(surface, MGRAY,  (cx-28, cy-20, 56, 40))
        pygame.draw.rect(surface, LGRAY,  (cx-28, cy-20, 56, 40), 2)
        for seg in [-10, 0, 10]:
            pygame.draw.line(surface, GRAY, (cx-28, cy+seg), (cx+28, cy+seg), 1)
        for side in [-1, 1]:
            dx2 = cx + side*28
            pygame.draw.rect(surface, DGRAY, (dx2+side*2, cy-8, side*12, 16))
            pygame.draw.rect(surface, LGRAY, (dx2+side*2, cy-8, side*12, 16), 1)
        for side in [-1, 1]:
            mx2 = cx + side*55
            pygame.draw.rect(surface, MGRAY, (mx2-8, cy-14, 16, 28))
            pygame.draw.rect(surface, GRAY,  (mx2-8, cy-14, 16, 28), 1)
        for side2 in [-1, 1]:
            py2 = cy + side2*38
            pts = [(cx-40,py2),(cx+40,py2),(cx+40,py2+side2*14),(cx-40,py2+side2*14)]
            pygame.draw.polygon(surface, DGRAY, pts)
            pygame.draw.polygon(surface, GRAY, pts, 1)
            for xi in range(cx-36, cx+36, 16):
                pygame.draw.line(surface, MGRAY, (xi,py2), (xi, py2+side2*14), 1)
        n = FONT_XS.render("STN-02", True, LGRAY)
        surface.blit(n, (cx-18, cy-8))
        for lpos in [(-28,-20),(28,-20),(-28,20),(28,20)]:
            lc2 = WHITE if int(bt*1.5 + lpos[0]*0.05)%2 == 0 else DGRAY
            pygame.draw.circle(surface, lc2, (cx+lpos[0], cy+lpos[1]), 3)

    elif variant == 2:
        # Hex military outpost
        hex_pts = []
        for i in range(6):
            a = math.radians(i*60 + rot*15)
            hex_pts.append((cx+22*math.cos(a), cy+22*math.sin(a)))
        pygame.draw.polygon(surface, MGRAY, hex_pts)
        pygame.draw.polygon(surface, LGRAY, hex_pts, 2)
        for i in range(6):
            a   = math.radians(i*60 + rot*15)
            tx2 = cx + 22*math.cos(a); ty2 = cy + 22*math.sin(a)
            pygame.draw.circle(surface, DGRAY, (int(tx2), int(ty2)), 6)
            pygame.draw.circle(surface, LGRAY, (int(tx2), int(ty2)), 6, 1)
            gun_a = math.radians(i*60 + rot*15)
            pygame.draw.line(surface, LGRAY,
                             (int(tx2), int(ty2)),
                             (int(tx2+12*math.cos(gun_a)), int(ty2+12*math.sin(gun_a))), 2)
        for i in range(12):
            a1 = math.radians(i*30 + rot*15)
            a2 = math.radians(i*30 + 20 + rot*15)
            pygame.draw.line(surface, GRAY,
                             (int(cx+52*math.cos(a1)), int(cy+52*math.sin(a1))),
                             (int(cx+52*math.cos(a2)), int(cy+52*math.sin(a2))), 2)
        rc = WHITE if int(bt*3)%2 == 0 else GRAY
        pygame.draw.circle(surface, rc, (cx, cy), 7)
        pygame.draw.circle(surface, LGRAY, (cx, cy), 7, 2)

    elif variant == 3:
        # Mining rig
        pygame.draw.rect(surface, MGRAY,  (cx-18, cy-18, 36, 36))
        pygame.draw.rect(surface, LGRAY,  (cx-18, cy-18, 36, 36), 2)
        for ang2, alen in [(0, 55),(90, 45),(180, 55),(270, 45)]:
            a2 = math.radians(ang2 + rot*10)
            ex = cx + alen*math.cos(a2); ey = cy + alen*math.sin(a2)
            pygame.draw.line(surface, LGRAY, (cx, cy), (int(ex), int(ey)), 2)
            pygame.draw.rect(surface, DGRAY, (int(ex)-7, int(ey)-5, 14, 10))
            pygame.draw.rect(surface, LGRAY, (int(ex)-7, int(ey)-5, 14, 10), 1)
            drill_a = a2 + math.radians(bt*120)
            for di in [-4, 0, 4]:
                ddx = int(ex) + di - int(3*math.cos(drill_a))
                ddy = int(ey)     - int(3*math.sin(drill_a))
                pygame.draw.circle(surface, WHITE, (ddx, ddy), 2)
        for cpos in [(-30,-8),(30,-8),(-30,8),(30,8)]:
            pygame.draw.rect(surface, DGRAY, (cx+cpos[0]-8, cy+cpos[1]-4, 14, 8))
            pygame.draw.rect(surface, GRAY,  (cx+cpos[0]-8, cy+cpos[1]-4, 14, 8), 1)


def draw_station_gate(surface, sx, sy, bt):
    gw, gh = 170, 18
    gx = sx - gw//2
    gy = sy + 85
    pygame.draw.rect(surface, DGRAY, (gx, gy, gw, gh))
    pygame.draw.rect(surface, WHITE, (gx, gy, gw, gh), 2)
    pygame.draw.rect(surface, LGRAY, (gx-6, gy-15, 8, gh+20), 1)
    pygame.draw.rect(surface, LGRAY, (gx+gw-2, gy-15, 8, gh+20), 1)
    lc = WHITE if int(bt*2)%2 == 0 else DGRAY
    pygame.draw.rect(surface, lc, (gx+5, gy+4, 10, gh-8))
    pygame.draw.rect(surface, lc, (gx+gw-15, gy+4, 10, gh-8))
    scan_x = gx + int((math.sin(bt*2)+1)/2 * gw)
    pygame.draw.line(surface, LGRAY, (scan_x, gy+1), (scan_x, gy+gh-1), 1)
    surface.blit(FONT_XS.render("ENTRANCE", True, GRAY), (gx+38, gy+22))


# =========================================================================
# 3. PLAYER SHIP — improved RCS and engine flame
# =========================================================================
def poly_transform(pts, cx, cy, angle):
    out = []
    for px, py in pts:
        rx = cx + px*math.cos(angle) - py*math.sin(angle)
        ry = cy + px*math.sin(angle) + py*math.cos(angle)
        out.append((rx, ry))
    return out


def draw_player_ship(surface, cx, cy, angle, thr, turn, strafe, bt):
    # Main hull
    hull_pts = [
        (0,-30),(-6,-18),(-6,-7),(-15,-3),(-17,13),(-9,17),(-5,26),(5,26),(9,17),(17,13),(15,-3),(6,-7),(6,-18)
    ]
    rh = poly_transform(hull_pts, cx, cy, angle)
    pygame.draw.polygon(surface, DGRAY, rh)
    pygame.draw.polygon(surface, WHITE, rh, 2)

    # Cockpit
    cab = [(0,-30),(-5,-22),(5,-22)]
    rc  = poly_transform(cab, cx, cy, angle)
    pygame.draw.polygon(surface, MGRAY, rc)
    pygame.draw.polygon(surface, LGRAY, rc, 1)

    # Engine nacelles
    for eng_pts in [
        [(-5,17),(-9,17),(-9,26),(-5,26)],
        [(5,17),(9,17),(9,26),(5,26)]
    ]:
        re = poly_transform(eng_pts, cx, cy, angle)
        pygame.draw.polygon(surface, MGRAY, re)
        pygame.draw.polygon(surface, LGRAY, re, 1)

    # Nav lights (blink)
    nav_l = poly_transform([(-17, 13)], cx, cy, angle)[0]
    nav_r = poly_transform([(17, 13)],  cx, cy, angle)[0]
    if int(bt*3)%2 == 0:
        pygame.draw.circle(surface, WHITE, (int(nav_l[0]), int(nav_l[1])), 2)
        pygame.draw.circle(surface, LGRAY, (int(nav_r[0]), int(nav_r[1])), 2)

    # ── ENGINE FLAME — animated with flicker ─────────────────────────
    if thr > 0.05:
        flicker = 0.85 + 0.15*math.sin(bt*28.0 + random.uniform(-0.3, 0.3))
        base_len = thr * 28.0 * flicker
        for nozzle_off in [-7, 7]:
            base_pt = poly_transform([(nozzle_off, 26)], cx, cy, angle)[0]
            # layered flame: wide dim base → narrow bright tip
            for layer, (spread, length, brightness) in enumerate([
                (4.5, base_len * 1.0, 80),
                (2.5, base_len * 0.72, 140),
                (1.2, base_len * 0.45, 210),
            ]):
                tip_l = poly_transform([(nozzle_off - spread, 26 + length)], cx, cy, angle)[0]
                tip_r = poly_transform([(nozzle_off + spread, 26 + length)], cx, cy, angle)[0]
                tip_m = ((tip_l[0]+tip_r[0])//2, (tip_l[1]+tip_r[1])//2)
                lv     = brightness
                flame_col = (lv, lv, lv)
                pygame.draw.polygon(surface, flame_col, [
                    (int(base_pt[0]-spread*0.7*math.cos(angle+1.57)),
                     int(base_pt[1]-spread*0.7*math.sin(angle+1.57))),
                    (int(base_pt[0]+spread*0.7*math.cos(angle+1.57)),
                     int(base_pt[1]+spread*0.7*math.sin(angle+1.57))),
                    (int(tip_m[0]), int(tip_m[1])),
                ])

    # ── RCS THRUSTERS — directional, clean ───────────────────────────
    # Ship-local thruster positions: (local_x, local_y, fire_dir_x, fire_dir_y, name)
    # fire direction is the direction gas EXITS (opposite to push)
    rcs_defs = [
        # Front-left  (fires left  → pushes right, or fires fwd → turn right)
        {"pos": (-6, -7),  "exit": (-1,  0), "key": "fl"},
        # Front-right (fires right → pushes left,  or fires fwd → turn left)
        {"pos": ( 6, -7),  "exit": ( 1,  0), "key": "fr"},
        # Rear-left   (fires left  → pushes right, or fires bwd → turn left)
        {"pos": (-6,  13), "exit": (-1,  0), "key": "rl"},
        # Rear-right  (fires right → pushes left,  or fires bwd → turn right)
        {"pos": ( 6,  13), "exit": ( 1,  0), "key": "rr"},
    ]

    # Which thrusters fire for each input:
    active_rcs = set()
    if turn == -1:   # turn left  → front-right + rear-left fire
        active_rcs |= {"fr", "rl"}
    elif turn == 1:  # turn right → front-left + rear-right fire
        active_rcs |= {"fl", "rr"}
    if strafe == -1: # strafe left  → right-side thrusters push left
        active_rcs |= {"fr", "rr"}
    elif strafe == 1: # strafe right → left-side thrusters push right
        active_rcs |= {"fl", "rl"}

    rcs_visible = int(bt * 18) % 2 == 0

    for rd in rcs_defs:
        wp = poly_transform([rd["pos"]], cx, cy, angle)[0]
        gx3, gy3 = int(wp[0]), int(wp[1])
        is_on = rd["key"] in active_rcs

        # Thruster nozzle dot
        col_noz = LGRAY if is_on else DGRAY
        pygame.draw.circle(surface, col_noz, (gx3, gy3), 3)
        pygame.draw.circle(surface, WHITE if is_on else GRAY, (gx3, gy3), 3, 1)

        if is_on and rcs_visible:
            # Transform exit direction to world space
            ex_loc = rd["exit"]
            # rotate local exit direction by ship angle
            ex_wx = ex_loc[0]*math.cos(angle) - ex_loc[1]*math.sin(angle)
            ex_wy = ex_loc[0]*math.sin(angle) + ex_loc[1]*math.cos(angle)
            # Draw 3-dot plume
            for dist in [6, 10, 14]:
                px2 = gx3 + int(ex_wx * dist)
                py2 = gy3 + int(ex_wy * dist)
                alpha = 255 - dist * 14
                a_clamped = max(60, alpha)
                c_v = a_clamped
                pygame.draw.circle(surface, (c_v, c_v, c_v), (px2, py2), max(1, 3 - dist//6))
            # Solid jet line
            end_x = gx3 + int(ex_wx * 16)
            end_y = gy3 + int(ex_wy * 16)
            pygame.draw.line(surface, LGRAY, (gx3, gy3), (end_x, end_y), 2)


# =========================================================================
# 4. PARTICLES
# =========================================================================
def add_exhaust_particle(x, y, vx, vy):
    particles.append([x, y,
                       vx + random.uniform(-10, 10),
                       vy + random.uniform(-10, 10),
                       random.uniform(0.15, 0.50)])

def add_rcs_particle(x, y, vx2, vy2):
    rcs_particles.append([x, y,
                           vx2 + random.uniform(-6, 6),
                           vy2 + random.uniform(-6, 6),
                           random.uniform(0.08, 0.22)])

def update_and_draw_particles(surface, dt):
    for lst in [particles, rcs_particles]:
        for p in lst[:]:
            p[0] += p[2]*dt
            p[1] += p[3]*dt
            p[4] -= dt
            if p[4] <= 0:
                lst.remove(p)
                continue
            a = min(200, int(p[4] * 500))
            pygame.draw.circle(surface, (a, a, a),
                                (int(p[0]), int(p[1])), 2 if p[4] > 0.15 else 1)


# =========================================================================
# 5. HUD
# =========================================================================
def draw_hud_gauges(surface):
    bx, by, bw, bh = 20, 150, 22, 180
    pygame.draw.rect(surface, WHITE, (bx, by, bw, bh), 2)
    fh = int(bh * throttle)
    if fh > 0:
        pygame.draw.rect(surface, WHITE, (bx+2, by+bh-fh, bw-4, fh))
    surface.blit(FONT_SM.render("THR", True, WHITE), (bx-4, by-42))
    surface.blit(FONT_SM.render(f"{int(throttle*100)}%", True, WHITE), (bx-4, by-22))

    tx, ty = 20, 390
    pygame.draw.rect(surface, WHITE, (tx, ty, bw, bh), 2)
    th = int(bh * (engine_temp / 100.0))
    if th > 0:
        tc = LGRAY if engine_temp > 70 else GRAY
        for yl2 in range(ty+bh-th, ty+bh, 4):
            pygame.draw.line(surface, tc, (tx+2, yl2), (tx+bw-3, yl2), 1)
    surface.blit(FONT_SM.render("TEMP", True, WHITE), (tx-6, ty-42))
    if engine_cooldown:
        if int(blinking_timer*4)%2 == 0:
            surface.blit(FONT_SM.render("OVR!", True, WHITE), (tx-4, ty-22))
    else:
        surface.blit(FONT_SM.render(f"{int(engine_temp)}C", True, WHITE), (tx-4, ty-22))


MM_X, MM_Y, MM_W, MM_H = WIDTH-160, 10, 150, 130
MM_SCALE = 0.008

def draw_minimap(surface):
    mm = pygame.Surface((MM_W, MM_H), pygame.SRCALPHA)
    mm.fill((0, 0, 0, 200))
    pygame.draw.rect(mm, GRAY, (0, 0, MM_W, MM_H), 1)
    cx4, cy4 = MM_W//2, MM_H//2
    for st in stations:
        rx = cx4 + int((st["x"]-world_x) * MM_SCALE)
        ry = cy4 + int((st["y"]-world_y) * MM_SCALE)
        if 2 <= rx <= MM_W-2 and 2 <= ry <= MM_H-2:
            col4 = WHITE if cargo and cargo["target"] == st["name"] else LGRAY
            pygame.draw.circle(mm, col4, (rx, ry), 3)
            lbl = FONT_XS.render(st["name"][:5], True, col4)
            mm.blit(lbl, (rx+3, ry-5))
    # Player arrow
    pygame.draw.circle(mm, WHITE, (cx4, cy4), 3)
    a_mm = player_angle
    tip = (cx4+int(7*math.sin(a_mm)), cy4-int(7*math.cos(a_mm)))
    lft = (cx4+int(3*math.sin(a_mm+2.4)), cy4-int(3*math.cos(a_mm+2.4)))
    rgt = (cx4+int(3*math.sin(a_mm-2.4)), cy4-int(3*math.cos(a_mm-2.4)))
    pygame.draw.polygon(mm, WHITE, [tip, lft, rgt])
    surface.blit(mm, (MM_X, MM_Y))
    surface.blit(FONT_XS.render("NAV MAP", True, GRAY), (MM_X+2, MM_Y+MM_H+2))


def draw_radio_widget(surface, bt):
    """Radio comms widget — sits below minimap."""
    rx0 = MM_X
    ry0 = MM_Y + MM_H + 18
    rw  = MM_W
    rh  = 76

    bg = pygame.Surface((rw, rh), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 200))
    surface.blit(bg, (rx0, ry0))
    pygame.draw.rect(surface, GRAY, (rx0, ry0, rw, rh), 1)

    # Animated radio icon (signal rings)
    icon_x = rx0 + 14
    icon_y = ry0 + 14
    pulse = (math.sin(bt * 3.5) + 1) / 2  # 0..1
    for ring in range(3):
        r_size = 4 + ring * 5
        alpha  = int(200 * (1 - ring/3) * pulse)
        c_val  = alpha
        if alpha > 20:
            pygame.draw.circle(surface, (c_val, c_val, c_val), (icon_x, icon_y), r_size, 1)
    pygame.draw.circle(surface, WHITE, (icon_x, icon_y), 3)

    # Label
    surface.blit(FONT_XS.render("COMMS", True, LGRAY), (rx0+24, ry0+6))

    # Main radio text (word-wrapped to widget width)
    max_chars = 20
    words     = current_radio_text.split()
    lines     = []
    cur_line  = ""
    for w in words:
        if len(cur_line) + len(w) + 1 <= max_chars:
            cur_line += (" " if cur_line else "") + w
        else:
            if cur_line:
                lines.append(cur_line)
            cur_line = w
    if cur_line:
        lines.append(cur_line)

    for i, line in enumerate(lines[:2]):
        surface.blit(FONT_XS.render(line, True, WHITE), (rx0+4, ry0+22+i*14))

    # Secondary docking hint
    if radio_secondary:
        s_words = radio_secondary.split()
        s_line  = ""
        s_lines = []
        for w in s_words:
            if len(s_line) + len(w) + 1 <= max_chars:
                s_line += (" " if s_line else "") + w
            else:
                s_lines.append(s_line)
                s_line = w
        if s_line:
            s_lines.append(s_line)
        col_hint = WHITE if int(bt*3)%2 == 0 else GRAY
        for i, line in enumerate(s_lines[:2]):
            surface.blit(FONT_XS.render(line, True, col_hint), (rx0+4, ry0+52+i*12))


# =========================================================================
# 6. QUEUE HELPERS
# =========================================================================
def update_queue(st, dt):
    ships = st["queue_ships"]
    if not ships:
        return
    for i in range(len(ships)):
        ships[i] -= QUEUE_SPEED * dt
    for i in range(1, len(ships)):
        mn = ships[i-1] + QUEUE_SPACING
        if ships[i] < mn:
            ships[i] = mn
    for i in range(len(ships)):
        if ships[i] < 2:
            ships[i] = 2.0

def try_pass_gate(st):
    ships = st["queue_ships"]
    if ships and ships[0] <= 5:
        ships.pop(0)
        return True
    return False

def replenish_queue(st):
    ships = st["queue_ships"]
    if len(ships) < 6:
        last = ships[-1] if ships else 40.0
        ships.append(last + random.uniform(QUEUE_SPACING, QUEUE_SPACING + 20))


def get_random_jobs():
    s1 = random.choice(stations)["name"]
    s2 = random.choice(stations)["name"]
    while s2 == s1:
        s2 = random.choice(stations)["name"]
    return [
        {"target": s1, "reward": random.randint(180, 350)},
        {"target": s2, "reward": random.randint(220, 500)},
    ]

available_jobs = get_random_jobs()


# =========================================================================
# 7. MAIN LOOP
# =========================================================================
running = True
while running:
    dt = min(clock.tick(60) / 1000.0, 0.05)
    blinking_timer   += dt
    radio_timer      += dt
    radio_icon_phase += dt

    # ── RADIO rotation ─────────────────────────────────────────────────
    if radio_timer > 8.0:
        if game_state in ['TRAVEL', 'MAIN_MENU', 'MAP']:
            current_radio_text = random.choice(radio_messages_general)
        radio_timer = 0.0

    # ── EVENTS ─────────────────────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if game_state == 'MAIN_MENU':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    game_state = 'TRAVEL'
                elif event.key == pygame.K_ESCAPE:
                    running = False

        elif game_state == 'TRAVEL':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    game_state = 'MAP'
                elif (event.key == pygame.K_e
                      and active_station
                      and player_queue_position == 0):
                    game_state       = 'DOCKING'
                    dock_ship_x      = float(WIDTH // 2)
                    dock_ship_y      = 120.0
                    dock_vx          = 0.0
                    dock_vy          = 0.0
                    dock_landing_success = False
                    gen_dock_traffic()
                    player_queue_position = -1
                    current_radio_text = "TOWER: Gate clear. Stabilise descent."

        elif game_state == 'MAP':
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_m, pygame.K_ESCAPE):
                game_state = 'TRAVEL'

        elif game_state == 'STATION_MENU':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1 and credits_val >= 20 and fuel < max_fuel:
                    credits_val -= 20; fuel = max_fuel
                elif event.key == pygame.K_2 and credits_val >= 30 and hull < 100:
                    credits_val -= 30; hull = 100.0
                elif event.key == pygame.K_3 and not cargo:
                    cargo = available_jobs[0]
                elif event.key == pygame.K_4 and not cargo:
                    cargo = available_jobs[1]
                elif event.key == pygame.K_u:
                    game_state    = 'TRAVEL'
                    throttle      = 0.0
                    player_vx    += 200 * math.sin(player_angle)
                    player_vy    -= 200 * math.cos(player_angle)
                    available_jobs = get_random_jobs()

    keys = pygame.key.get_pressed()

    # ======================================================================
    # TRAVEL PHYSICS
    # ======================================================================
    if game_state == 'TRAVEL':
        turn_dir   = 0
        strafe_dir = 0

        # Engine temp / throttle
        if engine_cooldown:
            throttle     = max(0.0, throttle - 2.0*dt)
            engine_temp -= 25.0 * dt
            if engine_temp <= 20.0:
                engine_cooldown = False
        else:
            if keys[pygame.K_w]:
                throttle = min(1.0, throttle + 1.2*dt)
            if keys[pygame.K_s]:
                throttle = max(0.0, throttle - 1.2*dt)

        if throttle > 0.75:
            engine_temp += throttle * 30.0 * dt
            if engine_temp >= 100.0:
                engine_temp     = 100.0
                engine_cooldown = True
        else:
            engine_temp = max(0.0, engine_temp - 12.0*dt)

        # Rotation
        if keys[pygame.K_LEFT]:
            player_angle -= 3.0 * dt
            turn_dir = -1
        if keys[pygame.K_RIGHT]:
            player_angle += 3.0 * dt
            turn_dir = 1

        # Forward thrust → accumulate into velocity
        fx = math.sin(player_angle)
        fy = -math.cos(player_angle)
        thrust_force = throttle * 280.0
        player_vx += fx * thrust_force * dt
        player_vy += fy * thrust_force * dt

        # Strafe thrust
        sx2 = math.cos(player_angle)
        sy2 = math.sin(player_angle)
        if keys[pygame.K_a] and fuel > 0:
            player_vx -= sx2 * 130 * dt
            player_vy -= sy2 * 130 * dt
            fuel      -= 0.7 * dt
            strafe_dir = -1
        if keys[pygame.K_d] and fuel > 0:
            player_vx += sx2 * 130 * dt
            player_vy += sy2 * 130 * dt
            fuel      -= 0.7 * dt
            strafe_dir = 1

        # Speed cap
        spd = math.hypot(player_vx, player_vy)
        MAX_SPEED = 380.0
        if spd > MAX_SPEED:
            player_vx = player_vx / spd * MAX_SPEED
            player_vy = player_vy / spd * MAX_SPEED

        # Move world
        if fuel > 0 or spd > 0:
            world_x += player_vx * dt
            world_y += player_vy * dt
            if throttle > 0 or strafe_dir != 0:
                fuel -= (0.4 + throttle * 2.8) * dt

        # Parallax stars
        for star in stars:
            star["x"] -= player_vx * dt * star["sf"] * 0.4
            star["y"] -= player_vy * dt * star["sf"] * 0.4
            if star["x"] < 0:      star["x"] += WIDTH
            if star["x"] > WIDTH:  star["x"] -= WIDTH
            if star["y"] < 0:      star["y"] += HEIGHT
            if star["y"] > HEIGHT: star["y"] -= HEIGHT

        # Exhaust
        if throttle > 0.1 and fuel > 0:
            ex_w = WIDTH//2 - fx*28
            ey_w = HEIGHT//2 - fy*28
            if random.random() < throttle * 0.7:
                add_exhaust_particle(ex_w, ey_w, -fx*90, -fy*90)

        # RCS particles
        if (turn_dir or strafe_dir) and fuel > 0:
            if random.random() < 0.35:
                add_rcs_particle(WIDTH//2 + random.uniform(-18, 18),
                                 HEIGHT//2 + random.uniform(-18, 18),
                                 random.uniform(-20, 20),
                                 random.uniform(-20, 20))

        # Station rotation
        for st in stations:
            st["rot"] = (st["rot"] + 0.5*dt) % 360.0

        # Queue update
        queue_timer += dt
        for st in stations:
            update_queue(st, dt)
            if queue_timer > GATE_PASS_T:
                if try_pass_gate(st):
                    if player_queue_position > 0:
                        player_queue_position -= 1
            replenish_queue(st)
        if queue_timer > GATE_PASS_T:
            queue_timer = 0.0

        # Station proximity + queue + radio
        active_station  = None
        radio_secondary = ""
        for st in stations:
            dist = math.hypot(world_x - st["x"], world_y - st["y"])
            if dist < 150:
                active_station = st
            if dist < 450 and spd > 120.0:
                hull = max(0.0, hull - 25.0*dt)
                if int(blinking_timer*5)%2 == 0:
                    current_radio_text = "TOWER: SPEED LIMIT! Hull taking damage!"
                if hull <= 0:
                    hull = 100.0
                    credits_val = max(0, credits_val - 30)
                    game_state  = 'MAIN_MENU'
            if dist < 500:
                # Show docking radio hint
                q_pos = player_queue_position if player_queue_position != -1 else -1
                radio_secondary = make_dock_hint(st["name"], q_pos)
            if dist < 300 and player_queue_position == -1:
                player_queue_position = len(st["queue_ships"]) + 1
                current_radio_text = f"TOWER: {st['name'][:14]} — queue pos: {player_queue_position}."

        if active_station is None and player_queue_position != -1:
            player_queue_position = -1
            current_radio_text    = "TOWER: Sector exit. Queue position forfeited."

        # Queue position voice cue
        if player_queue_position == 0:
            radio_secondary = make_dock_hint(
                active_station["name"] if active_station else "Station", 0)

    # ======================================================================
    # DOCKING PHYSICS — improved
    # ======================================================================
    elif game_state == 'DOCKING':
        dock_vy += GRAVITY * dt

        if keys[pygame.K_w] and fuel > 0:
            dock_vy -= 220 * dt
            fuel    -= 3.5 * dt
            if random.random() < 0.55:
                add_exhaust_particle(dock_ship_x, dock_ship_y + 18, 0, 140)
        if keys[pygame.K_s] and fuel > 0:
            dock_vy += 80 * dt
        if keys[pygame.K_a] and fuel > 0:
            dock_vx -= 160 * dt
            fuel    -= 0.5 * dt
        if keys[pygame.K_d] and fuel > 0:
            dock_vx += 160 * dt
            fuel    -= 0.5 * dt

        # Damping
        dock_vx *= (1.0 - 0.55*dt)
        # Clamp vertical speed upward (no rocket above ceiling)
        dock_vy = min(dock_vy, 280)

        dock_ship_x = max(30, min(WIDTH-30, dock_ship_x + dock_vx*dt))
        dock_ship_y += dock_vy * dt

        # Ceiling collision
        if dock_ship_y < 140:
            dock_ship_y = 140.0
            dock_vy = abs(dock_vy) * 0.4   # bounce

        if dock_vy > 35 and dock_ship_y > HEIGHT - 250:
            dock_warning_flash = 0.4
        if dock_warning_flash > 0:
            dock_warning_flash -= dt

        pad_y = HEIGHT - 160
        if dock_ship_y >= pad_y - 26:
            dock_ship_y = float(pad_y - 26)
            offset2     = abs(dock_ship_x - WIDTH//2)
            if offset2 < 85 and dock_vy < 48:
                if not dock_landing_success:
                    dock_landing_success = True
                    if (cargo and active_station
                            and cargo["target"] == active_station["name"]):
                        credits_val += cargo["reward"]
                        cargo = None
                    game_state = 'STATION_MENU'
            else:
                hull         = max(0.0, hull - 30.0)
                dock_ship_x  = float(WIDTH // 2)
                dock_ship_y  = 140.0
                dock_vx      = 0.0
                dock_vy      = 0.0
                dock_warning_flash = 0.5
                current_radio_text = "TOWER: Crash on landing! Structural damage."
                if hull <= 0:
                    hull        = 100.0
                    credits_val = max(0, credits_val - 40)
                    game_state  = 'MAIN_MENU'

    # ======================================================================
    # RENDER
    # ======================================================================
    screen.fill(BLACK)

    # ── MAIN MENU ─────────────────────────────────────────────────────
    if game_state == 'MAIN_MENU':
        screen.blit(FONT_LG.render("=== SPACE TRUCKER: SIMULATOR ===", True, WHITE), (160, 200))
        screen.blit(FONT_MD.render("Press [ENTER] to launch", True, LGRAY), (320, 310))
        for i, ln in enumerate([
            "[W/S] Throttle    [LEFT/RIGHT] Rotate    [A/D] Strafe",
            "[M] Star Map      [E] Dock (when queued to position 0)",
            "Find stations, join docking queues, deliver cargo.",
        ]):
            screen.blit(FONT_SM.render(ln, True, GRAY), (180, 420 + i*28))

    # ── TRAVEL ────────────────────────────────────────────────────────
    elif game_state == 'TRAVEL':
        # Stars
        for star in stars:
            c5 = star["bright"]
            pygame.draw.circle(screen, (c5, c5, c5),
                               (int(star["x"]), int(star["y"])), star["size"])

        update_and_draw_particles(screen, dt)

        for st in stations:
            sx3 = int(WIDTH//2 + (st["x"] - world_x))
            sy3 = int(HEIGHT//2 + (st["y"] - world_y))

            # Orbit ring — only if on-screen vicinity
            if -600 <= sx3 <= WIDTH+600 and -600 <= sy3 <= HEIGHT+600:
                pygame.draw.circle(screen, DGRAY, (sx3, sy3), 450, 1)

            # Draw station only if near screen (prevents clipping artefacts)
            if -120 <= sx3 <= WIDTH+120 and -120 <= sy3 <= HEIGHT+120:
                draw_station(screen, sx3, sy3, st["variant"], st["rot"], blinking_timer)
                draw_station_gate(screen, sx3, sy3, blinking_timer)
                screen.blit(FONT_SM.render(st["name"], True, LGRAY), (sx3-55, sy3-80))

                # Queue ships
                gate_y = sy3 + 85
                for idx, dfg in enumerate(st["queue_ships"]):
                    qy = gate_y - int(dfg)
                    if gate_y - 450 < qy < gate_y:
                        qx  = sx3 - 6
                        col5 = WHITE if idx == 0 else GRAY
                        pygame.draw.rect(screen, DGRAY, (qx, qy, 12, 8))
                        pygame.draw.rect(screen, col5,  (qx, qy, 12, 8), 1)

                n5 = len(st["queue_ships"])
                if n5 > 0:
                    screen.blit(FONT_XS.render(f"queue: {n5}", True, GRAY),
                                (sx3+30, gate_y-42))

        # Player ship (always centred)
        draw_player_ship(screen, WIDTH//2, HEIGHT//2, player_angle,
                         throttle, turn_dir, strafe_dir, blinking_timer)

        draw_hud_gauges(screen)
        draw_minimap(screen)
        draw_radio_widget(screen, blinking_timer)

        # Target compass
        if cargo:
            t5 = next((s for s in stations if s["name"] == cargo["target"]), None)
            if t5:
                d5x = t5["x"] - world_x
                d5y = t5["y"] - world_y
                a5t = math.atan2(d5x, -d5y)
                ccx2, ccy2 = WIDTH-80, 180
                pygame.draw.circle(screen, WHITE, (ccx2, ccy2), 28, 1)
                pygame.draw.line(screen, WHITE, (ccx2, ccy2),
                                 (ccx2+int(20*math.sin(a5t)), ccy2-int(20*math.cos(a5t))), 2)
                screen.blit(FONT_SM.render(f"DEST: {cargo['target'][:14]}", True, WHITE),
                            (WIDTH-318, 220))

        # Dock prompt
        if active_station and player_queue_position == 0:
            pygame.draw.rect(screen, BLACK, (WIDTH//2-250, HEIGHT-178, 500, 46))
            pygame.draw.rect(screen, WHITE, (WIDTH//2-250, HEIGHT-178, 500, 46), 1)
            if int(blinking_timer*4)%2 == 0:
                screen.blit(FONT_MD.render("CLEARED TO DOCK  [E] TO ENTER", True, WHITE),
                            (WIDTH//2-210, HEIGHT-168))
        elif active_station and player_queue_position > 0:
            pygame.draw.rect(screen, BLACK, (WIDTH//2-250, HEIGHT-178, 500, 46))
            pygame.draw.rect(screen, GRAY, (WIDTH//2-250, HEIGHT-178, 500, 46), 1)
            screen.blit(FONT_MD.render(f"HOLD — QUEUE POSITION: {player_queue_position}", True, GRAY),
                        (WIDTH//2-220, HEIGHT-168))

    # ── MAP ───────────────────────────────────────────────────────────
    elif game_state == 'MAP':
        screen.blit(FONT_LG.render("STAR MAP", True, WHITE), (380, 20))
        scale6 = 0.018
        for st in stations:
            mx6 = int(WIDTH//2 + (st["x"] - world_x)*scale6)
            my6 = int(HEIGHT//2 + (st["y"] - world_y)*scale6)
            c6  = WHITE if cargo and cargo["target"] == st["name"] else LGRAY
            pygame.draw.circle(screen, c6, (mx6, my6), 6, 2)
            screen.blit(FONT_XS.render(st["name"], True, c6), (mx6+8, my6-5))
        pygame.draw.circle(screen, WHITE, (WIDTH//2, HEIGHT//2), 5)
        screen.blit(FONT_SM.render("[ M / ESC ] Back", True, GRAY), (20, HEIGHT-40))

    # ── DOCKING ───────────────────────────────────────────────────────
    elif game_state == 'DOCKING':
        # Hangar walls
        pygame.draw.line(screen, WHITE, (0, 132),           (WIDTH, 132), 2)
        pygame.draw.line(screen, WHITE, (0, HEIGHT-152),    (WIDTH, HEIGHT-152), 2)

        # Interior details
        for item in dock_interior:
            if item["type"] == "column":
                cx7 = item["x"]
                pygame.draw.line(screen, DGRAY, (cx7, 132), (cx7, HEIGHT-152), 1)
                pygame.draw.rect(screen, GRAY, (cx7-5, 128,  10, 10), 1)
                pygame.draw.rect(screen, GRAY, (cx7-5, HEIGHT-156, 10, 10), 1)
            elif item["type"] == "floor_light":
                lx7  = item["x"]
                ph7  = item["phase"]
                lc7  = LGRAY if int((blinking_timer*0.8 + ph7))%2 == 0 else DGRAY
                pygame.draw.rect(screen, lc7, (lx7-3, HEIGHT-157, 6, 5))
            elif item["type"] == "panel":
                px7, py7 = item["x"], item["y"]
                pygame.draw.rect(screen, DGRAY, (px7, py7, 42, 62), 1)
                for row7 in range(4):
                    rc7 = LGRAY if row7 % 2 == 0 else GRAY
                    pygame.draw.rect(screen, rc7, (px7+4, py7+8+row7*12, 34, 8), 1)
            elif item["type"] == "crane":
                crx = item["x"]
                pygame.draw.line(screen, GRAY, (crx, 132), (crx, 160), 2)
                pygame.draw.rect(screen, DGRAY, (crx-15, 155, 30, 12), 1)
                cable_y = int(160 + 40*abs(math.sin(blinking_timer*0.3 + crx*0.05)))
                pygame.draw.line(screen, GRAY, (crx, 167), (crx, cable_y), 1)
                pygame.draw.line(screen, GRAY, (crx, cable_y), (crx+5, cable_y+5), 1)

        screen.blit(FONT_LG.render("HANGAR — DOCKING BAY", True, WHITE), (250, 42))

        # Berths
        for obj in dock_traffic_ships:
            if obj["type"] == "BERTH":
                kx8, ky8 = obj["x"], obj["y"]
                is_top   = obj["side"] == "top"
                ky_base2 = ky8 if is_top else ky8-20
                pygame.draw.rect(screen, GRAY, (kx8-82, ky_base2, 164, 20), 1)
                lbl_y2 = ky_base2-22 if is_top else ky_base2+24
                bc8    = obj["blink"]
                sc8    = WHITE if obj["occupied"] else LGRAY
                if int((blinking_timer + bc8)*1.5)%2 == 0:
                    pygame.draw.rect(screen, sc8, (kx8+62, ky_base2+4, 10, 12))
                screen.blit(FONT_XS.render(f"BERTH {obj['label']}", True, GRAY), (kx8-30, lbl_y2))
                if obj["occupied"]:
                    pygame.draw.rect(screen, DGRAY, (kx8-18, ky_base2+3, 34, 12))
                    pygame.draw.rect(screen, LGRAY, (kx8-18, ky_base2+3, 34, 12), 1)

        update_and_draw_particles(screen, dt)

        # Player ship (docking view — side-on rectangle)
        fl10 = dock_warning_flash > 0 and int(blinking_timer*12)%2 == 0
        ship_col2 = LGRAY if fl10 else WHITE
        sx_i = int(dock_ship_x)
        sy_i = int(dock_ship_y)
        pygame.draw.rect(screen, DGRAY,  (sx_i-22, sy_i-13, 44, 26))
        pygame.draw.rect(screen, ship_col2, (sx_i-22, sy_i-13, 44, 26), 2)
        pygame.draw.rect(screen, MGRAY,  (sx_i-8,  sy_i-19, 16, 8))
        pygame.draw.rect(screen, LGRAY,  (sx_i-8,  sy_i-19, 16, 8), 1)
        pygame.draw.line(screen, WHITE,  (sx_i-18, sy_i+13), (sx_i-18, sy_i+19), 2)
        pygame.draw.line(screen, WHITE,  (sx_i+18, sy_i+13), (sx_i+18, sy_i+19), 2)
        # Engine glow during thrust
        if keys[pygame.K_w]:
            elen = int(6 + throttle * 14 + random.randint(0, 4))
            pygame.draw.line(screen, LGRAY,
                             (sx_i-7, sy_i+13), (sx_i-7, sy_i+13+elen), 2)
            pygame.draw.line(screen, LGRAY,
                             (sx_i+7, sy_i+13), (sx_i+7, sy_i+13+elen), 2)

        # Landing pad
        pad_y2 = HEIGHT - 160
        pygame.draw.rect(screen, WHITE, (WIDTH//2-87, pad_y2, 174, 20), 2)
        if int(blinking_timer*4)%2 == 0:
            pygame.draw.rect(screen, LGRAY, (WIDTH//2-87, pad_y2, 174, 6))
        screen.blit(FONT_MD.render("v  YOUR LANDING PAD  v", True, WHITE),
                    (WIDTH//2-148, pad_y2+25))

        # Descent guide
        guide_x2 = WIDTH//2
        if dock_ship_y < pad_y2 - 30:
            for sg in range(sy_i + 32, pad_y2-5, 22):
                if int(blinking_timer*6)%2 == 0:
                    pygame.draw.line(screen, DGRAY, (guide_x2, sg), (guide_x2, sg+11), 1)

        # Telemetry
        dvy2 = dock_vy
        off3 = dock_ship_x - WIDTH//2
        sc_v = LGRAY if dvy2 > 35 else (GRAY if dvy2 > 20 else WHITE)
        sc_o = LGRAY if abs(off3) > 80 else (GRAY if abs(off3) > 40 else WHITE)
        screen.blit(FONT_SM.render(f"Vert speed:  {int(dvy2):+4d} m/s", True, sc_v),  (50, 160))
        screen.blit(FONT_SM.render(f"H offset:    {int(off3):+4d} m",   True, sc_o),  (50, 186))
        screen.blit(FONT_SM.render(f"Fuel:         {int(fuel)} L",       True, WHITE), (50, 212))
        screen.blit(FONT_SM.render(f"[W] Retro    [A/D] Lateral",        True, GRAY),  (50, 238))

        if dock_warning_flash > 0 and int(blinking_timer*10)%2 == 0:
            screen.blit(FONT_MD.render("!  DESCENT RATE TOO HIGH  !", True, WHITE),
                        (WIDTH//2-172, HEIGHT//2))

    # ── STATION MENU ──────────────────────────────────────────────────
    elif game_state == 'STATION_MENU':
        nm = active_station['name'] if active_station else 'TERMINAL'
        screen.blit(FONT_LG.render(f"STATION: {nm}", True, WHITE), (100, 40))
        pygame.draw.line(screen, WHITE, (50, 90), (850, 90), 2)
        screen.blit(FONT_MD.render("SERVICES:", True, WHITE), (50, 130))
        screen.blit(FONT_SM.render("[1] Refuel tank (250L)   — 20 credits", True, WHITE), (70, 170))
        screen.blit(FONT_SM.render("[2] Repair hull          — 30 credits", True, WHITE), (70, 200))
        screen.blit(FONT_MD.render("CARGO CONTRACTS:", True, WHITE), (50, 280))
        for i2, job in enumerate(available_jobs):
            screen.blit(FONT_SM.render(
                f"[{i2+3}] Cargo → {job['target']}   Reward: {job['reward']} cr",
                True, WHITE), (70, 320 + i2*30))
        screen.blit(FONT_LG.render("[U]  Undock", True, WHITE), (330, 580))

    # ── GLOBAL HUD ────────────────────────────────────────────────────
    if game_state in ['TRAVEL', 'DOCKING', 'MAP']:
        pygame.draw.rect(screen, BLACK, (110, 10, 255, 100))
        pygame.draw.rect(screen, WHITE, (110, 10, 255, 100), 1)
        hc = LGRAY if hull < 30 else (GRAY if hull < 60 else WHITE)
        fc = LGRAY if fuel < 40 else (GRAY  if fuel < 80 else WHITE)
        screen.blit(FONT_SM.render(f"Credits: {credits_val} cr",     True, WHITE), (120, 16))
        screen.blit(FONT_SM.render(f"Fuel:    {int(fuel)}/{int(max_fuel)}L", True, fc), (120, 34))
        screen.blit(FONT_SM.render(f"Hull:    {int(hull)}%",          True, hc), (120, 52))
        screen.blit(FONT_SM.render(f"Pos:     {int(world_x)}, {int(world_y)}", True, GRAY), (120, 70))
        if cargo:
            screen.blit(FONT_SM.render(f"CARGO -> {cargo['target'][:14]}", True, WHITE), (120, 88))

        # Bottom radio bar
        pygame.draw.rect(screen, BLACK, (10, HEIGHT-50, WIDTH-20, 40))
        pygame.draw.rect(screen, WHITE, (10, HEIGHT-50, WIDTH-20, 40), 1)
        screen.blit(FONT_SM.render(current_radio_text, True, WHITE), (20, HEIGHT-40))

    pygame.display.flip()

pygame.quit()
sys.exit()