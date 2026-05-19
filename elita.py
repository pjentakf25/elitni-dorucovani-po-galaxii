import pygame
import sys
import random
import math

# =========================================================================
# 1. INICIALIZACE A HLAVNÍ NASTAVENÍ
# =========================================================================
pygame.init()
WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Trucker: Heavy Simulation Pro Edition")
clock = pygame.time.Clock()

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

FONT_SM = pygame.font.SysFont("Courier", 18)
FONT_MD = pygame.font.SysFont("Courier", 24)
FONT_LG = pygame.font.SysFont("Courier", 32)

game_state = 'MAIN_MENU'

# --- STATISTIKY HRÁČE & SIMULACE ---
credits = 100
max_fuel = 250.0
fuel = 250.0
hull = 100.0  
cargo = None
throttle = 0.0

# Systém přehřívání
engine_temp = 0.0       
engine_cooldown = False 

world_x, world_y = 0.0, 0.0
player_angle = 0.0
current_speed = 0.0

# Správa fronty (kolony) u aktivní stanice
player_queue_position = -1  # -1 znamená, že hráč ještě není ve frontě
queue_timer = 0.0

# Hvězdy na pozadí a částice
stars = [{"x": random.uniform(0, WIDTH), "y": random.uniform(0, HEIGHT), "speed_factor": random.uniform(0.2, 1.0), "size": random.choice([1, 2])} for _ in range(100)]
particles = []

# Stanice a inicializace jejich vlastních dynamických kolon
stations = [
    {"name": "Alfa Centauri Prime", "x": 3500, "y": -4000, "pad_id": "DOCK-01"},
    {"name": "Sol Station Echo", "x": -5000, "y": 3000, "pad_id": "DOCK-02"},
    {"name": "Zeta Reticuli Outpost", "x": 6000, "y": 5500, "pad_id": "DOCK-03"},
    {"name": "Orion Mining Hub", "x": -2500, "y": -7500, "pad_id": "DOCK-04"},
    {"name": "Sirius Junction", "x": 7500, "y": -3000, "pad_id": "DOCK-05"},
    {"name": "Kepler Depot", "x": -6000, "y": -4500, "pad_id": "DOCK-06"}
]

# Vygenerujeme počáteční pozice lodí v kolonách pro každou stanici
for st in stations:
    # Každá stanice má seznam vzdáleností lodí od brány (v pixelech/jednotkách fronty)
    # Lodě stojí v řadě za sebou: např. 40px, 90px, 140px, 190px od brány
    st["queue_ships"] = [40.0, 90.0, 140.0, 190.0]

active_station = None

# ČASTĚJŠÍ GLOBÁLNÍ PROVOZ
global_traffic = []
def spawn_global_traffic():
    global global_traffic
    global_traffic = []
    for _ in range(20):  
        global_traffic.append({
            "world_x": random.uniform(-9000, 9000),
            "world_y": random.uniform(-9000, 9000),
            "vx": random.uniform(-80, 80),
            "vy": random.uniform(-80, 80),
            "size_w": random.randint(25, 40),
            "size_h": random.randint(10, 15)
        })
spawn_global_traffic()

def get_random_jobs():
    st1 = random.choice(stations)["name"]
    st2 = random.choice(stations)["name"]
    while st2 == st1: st2 = random.choice(stations)["name"]
    return [{"target": st1, "reward": random.randint(180, 350)}, {"target": st2, "reward": random.randint(220, 500)}]

available_jobs = get_random_jobs()

# --- RÁDIOVÝ SYSTÉM ---
radio_messages = [
    "Radio: Pozor na gravitační prstence stanic! Vstupujte pouze pod 120 m/s.",
    "Radio: Sledujte ukazatel teploty [TEMP]. Přehřátí poškodí jádro motoru.",
    "Věž: Provoz houstne. Zařaďte se poslušně na konec příletové kolony.",
    "Radio: RCS trysky vykazují nominální tlak ve všech osách."
]
current_radio_text = "Radio: Core Operating Temperature: NOMINAL."
radio_timer = 0
blinking_timer = 0.0

# --- DOCKING PROMĚNNÉ ---
dock_ship_x = WIDTH // 2
dock_ship_y = 100
dock_vx, dock_vy = 0.0, 0.0
GRAVITY = 75.0
dock_traffic_ships = []

def generate_dock_traffic():
    global dock_traffic_ships
    dock_traffic_ships = []
    koje_positions = [
        {"x": WIDTH // 4, "y": 120, "label": "01", "type": "KOJE"},
        {"x": (3 * WIDTH) // 4, "y": 120, "label": "02", "type": "KOJE"},
        {"x": WIDTH // 4, "y": HEIGHT - 150, "label": "03", "type": "KOJE"},
        {"x": (3 * WIDTH) // 4, "y": HEIGHT - 150, "label": "04", "type": "KOJE"}
    ]
    for koje in koje_positions:
        koje["occupied"] = random.random() > 0.4
        dock_traffic_ships.append(koje)

    for _ in range(2):
        dock_traffic_ships.append({
            "x": random.choice([-20, WIDTH + 20]),
            "y": random.randint(250, HEIGHT - 300),
            "vx": random.uniform(60, 110) * (1 if random.random() > 0.5 else -1),
            "type": "FLYING"
        })

# =========================================================================
# 2. GEOMETRIE, ČÁSTICE A UKAZATELE GUI
# =========================================================================
def draw_heavy_trucker_ship(surface, cx, cy, angle):
    points = [
        (0, -28), (-5, -16), (-5, -6), (-14, -2), (-16, 12), (-8, 16),
        (-4, 24), (4, 24), (8, 16), (16, 12), (14, -2), (5, -6), (5, -16)
    ]
    rotated = []
    for px, py in points:
        rx = cx + (px * math.cos(angle) - py * math.sin(angle))
        ry = cy + (px * math.sin(angle) + py * math.cos(angle))
        rotated.append((rx, ry))
    pygame.draw.polygon(surface, WHITE, rotated, 2)

def draw_npc_cargo_ship(surface, x, y, width, height, vertical=False):
    """Vykreslí obdélníkovou nákladní loď (horizontálně nebo vertikálně)."""
    if not vertical:
        pygame.draw.rect(surface, WHITE, (x, y, width, height), 2)
        pygame.draw.rect(surface, WHITE, (x + width, y + 2, 6, height - 4), 1) # Kabina
        pygame.draw.line(surface, WHITE, (x, y + 3), (x - 4, y + 3), 2) # Motor
    else:
        # Vertikální kreslení (pro kolonu směřující dolů do brány)
        pygame.draw.rect(surface, WHITE, (x, y, height, width), 2)
        pygame.draw.rect(surface, WHITE, (x + 2, y + width, height - 4, 6), 1) # Kabina dole
        pygame.draw.line(surface, WHITE, (x + 3, y), (x + 3, y - 4), 2) # Motor nahoře

def add_exhaust_particle(x, y, vx, vy):
    particles.append([x, y, vx + random.uniform(-10, 10), vy + random.uniform(-10, 10), random.uniform(0.15, 0.5)])

def update_and_draw_particles(surface, dt):
    for p in particles[:]:
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[4] -= dt
        if p[4] <= 0: particles.remove(p)
        else:
            if p[4] > 0.25: pygame.draw.circle(surface, WHITE, (int(p[0]), int(p[1])), 2)
            else: surface.set_at((int(p[0]), int(p[1])), WHITE)

def draw_hud_gauges(surface):
    bx, by, bw, bh = 20, 150, 25, 180
    pygame.draw.rect(surface, WHITE, (bx, by, bw, bh), 2)
    fill_h = int(bh * throttle)
    if fill_h > 0: pygame.draw.rect(surface, WHITE, (bx + 3, by + bh - fill_h, bw - 5, fill_h))
    surface.blit(FONT_SM.render("THR", True, WHITE), (bx - 5, by - 45))
    surface.blit(FONT_SM.render(f"{int(throttle*100)}%", True, WHITE), (bx - 5, by - 25))

    tx, ty = 20, 390
    pygame.draw.rect(surface, WHITE, (tx, ty, bw, bh), 2)
    temp_h = int(bh * (engine_temp / 100.0))
    if temp_h > 0:
        for y_l in range(ty + bh - temp_h, ty + bh, 4): pygame.draw.line(surface, WHITE, (tx + 2, y_l), (tx + bw - 3, y_l), 1)
    surface.blit(FONT_SM.render("TEMP", True, WHITE), (tx - 8, ty - 45))
    if engine_cooldown:
        if int(blinking_timer * 4) % 2 == 0: surface.blit(FONT_SM.render("OVR!", True, WHITE), (tx - 5, ty - 25))
    else: surface.blit(FONT_SM.render(f"{int(engine_temp)}C", True, WHITE), (tx - 5, ty - 25))

# =========================================================================
# 3. HLAVNÍ HERNÍ SMYČKA A REŽIMY
# =========================================================================
running = True
while running:
    dt = clock.tick(60) / 1000.0
    blinking_timer += dt

    radio_timer += dt
    if radio_timer > 7.0:
        if game_state in ['TRAVEL', 'MAIN_MENU', 'MAP']:
            current_radio_text = random.choice(radio_messages)
        radio_timer = 0

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        
        if game_state == 'MAIN_MENU':
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN: game_state = 'TRAVEL'
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False

        elif game_state == 'TRAVEL':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m: game_state = 'MAP'
                elif event.key == pygame.K_e and active_station and player_queue_position == 0:
                    # Dokování je povoleno POUZE pokud je hráč na řadě (pozice 0)
                    game_state = 'DOCKING'
                    dock_ship_x, dock_ship_y = WIDTH // 2, 140
                    dock_vx, dock_vy = 0.0, 0.0
                    generate_dock_traffic()
                    player_queue_position = -1 # Reset fronty po úspěšném vjezdu
                    current_radio_text = f"Věž: Průlet bránou úspěšný. Stabilizujte výšku nad plošinou."

        elif game_state == 'MAP':
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_m or event.key == pygame.K_ESCAPE): game_state = 'TRAVEL'

        elif game_state == 'STATION_MENU':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1 and credits >= 20 and fuel < max_fuel:
                    credits -= 20; fuel = max_fuel
                elif event.key == pygame.K_2 and credits >= 30 and hull < 100:
                    credits -= 30; hull = 100.0
                elif event.key == pygame.K_3 and not cargo: cargo = available_jobs[0]
                elif event.key == pygame.K_4 and not cargo: cargo = available_jobs[1]
                elif event.key == pygame.K_u:
                    game_state = 'TRAVEL'
                    throttle, current_speed = 0.0, 0.0
                    world_x += 200 * math.sin(player_angle)
                    world_y -= 200 * math.cos(player_angle)
                    available_jobs = get_random_jobs()

    keys = pygame.key.get_pressed()
    
    if game_state == 'TRAVEL':
        # --- FYZIKA A PŘEHŘÍVÁNÍ ---
        if engine_cooldown:
            throttle = max(0.0, throttle - 2.0 * dt)
            engine_temp -= 25.0 * dt
            if engine_temp <= 20.0: engine_cooldown = False
        else:
            if keys[pygame.K_w]: throttle = min(1.0, throttle + 1.2 * dt)
            if keys[pygame.K_s]: throttle = max(0.0, throttle - 1.2 * dt)

        if throttle > 0.75:
            engine_temp += (throttle * 30.0) * dt
            if engine_temp >= 100.0: engine_temp = 100.0; engine_cooldown = True
        else: engine_temp = max(0.0, engine_temp - 12.0 * dt)

        if keys[pygame.K_LEFT]:  player_angle -= 3.0 * dt
        if keys[pygame.K_RIGHT]: player_angle += 3.0 * dt
        
        strafe_vx, strafe_vy = 0.0, 0.0
        strafe_x, strafe_y = math.cos(player_angle), math.sin(player_angle)
        forward_x, forward_y = math.sin(player_angle), -math.cos(player_angle)

        if keys[pygame.K_a] and fuel > 0:
            strafe_vx -= strafe_x * 130; strafe_vy -= strafe_y * 130; fuel -= 0.7 * dt
        if keys[pygame.K_d] and fuel > 0:
            strafe_vx += strafe_x * 130; strafe_vy += strafe_y * 130; fuel -= 0.7 * dt

        target_speed = throttle * 320.0
        current_speed += (target_speed - current_speed) * 1.8 * dt
        move_vx = (forward_x * current_speed) + strafe_vx
        move_vy = (forward_y * current_speed) + strafe_vy
        
        if fuel > 0 and (abs(move_vx) > 0 or abs(move_vy) > 0):
            world_x += move_vx * dt
            world_y += move_vy * dt
            fuel -= (0.4 + throttle * 2.8) * dt
            for star in stars:
                star["x"] -= move_vx * dt * star["speed_factor"] * 0.4
                if star["x"] < 0: star["x"] += WIDTH
                if star["x"] > WIDTH: star["x"] -= WIDTH
                star["y"] -= move_vy * dt * star["speed_factor"] * 0.4
                if star["y"] < 0: star["y"] += HEIGHT
                if star["y"] > HEIGHT: star["y"] -= HEIGHT

        # --- AKTUALIZACE GLOBÁLNÍHO A STANICOVÉHO PROVOZU (KOLONY) ---
        for npc in global_traffic:
            npc["world_x"] += npc["vx"] * dt
            npc["world_y"] += npc["vy"] * dt
            if npc["world_x"] < -9000: npc["world_x"] = 9000

        # Posun a logika front u všech stanic
        queue_timer += dt
        for st in stations:
            ships = st["queue_ships"]
            
            # První loď v koloně se pomalu posouvá k bráně (vzdálenost 0)
            if len(ships) > 0:
                if ships[0] > 10:
                    for i in range(len(ships)): ships[i] -= 15.0 * dt  # Celá fronta se sune kupředu
                else:
                    # Loď dorazila do brány a vjíždí dovnitř -> opouští venkovní frontu
                    if queue_timer > 4.0:  # Každých pár sekund projede jedna loď bránou
                        ships.pop(0)
                        queue_timer = 0.0
                        if player_queue_position > 0:
                            player_queue_position -= 1 # Hráč se posouvá v řadě dopředu!
                            current_radio_text = f"Věž: Kolona se pohnula. Jste {player_queue_position}. v pořadí."
                        elif player_queue_position == 0:
                            current_radio_text = "VĚŽ: JSTE NA ŘADĚ! Brána je volná, stiskněte [E] pro vjezd!"

            # Doplňování fronty zezadu novými NPC loděmi, aby fronta nikdy nezmizela
            if len(ships) < 4:
                last_pos = ships[-1] if len(ships) > 0 else 40
                ships.append(last_pos + random.uniform(45, 60))

        # --- DETEKCE AKTIVNÍ STANICE A ZAŘAZENÍ DO FRONTY ---
        active_station = None
        for st in stations:
            dist = math.hypot(world_x - st["x"], world_y - st["y"])
            if dist < 450: 
                if dist < 150: active_station = st
                
                # Poškození při rychlém průletu prstencem
                if current_speed > 120.0:
                    hull = max(0.0, hull - (25.0 * dt))
                    if int(blinking_timer * 5) % 2 == 0: current_radio_text = "VĚŽ: RYCHLOSTNÍ KONTROLA! Tření poškozuje trup!"
                    if hull <= 0: hull, credits = 100.0, max(0, credits - 30); game_state = 'MAIN_MENU'

                # Pokud je hráč blízko brány a ještě není ve frontě, automaticky ho věž zařadí na konec!
                if dist < 300 and player_queue_position == -1:
                    player_queue_position = len(st["queue_ships"]) + 1
                    current_radio_text = f"Věž: Registrujeme vás. Zařazen na konec kolony. Pořadí: {player_queue_position}."

        # Pokud hráč odletí daleko od stanice, vypadne z fronty
        if not active_station and player_queue_position != -1:
            player_queue_position = -1
            current_radio_text = "Věž: Opustil jste přibližovací sektor. Vaše místo v koloně propadlo."

    elif game_state == 'DOCKING':
        dock_vy += GRAVITY * dt
        if keys[pygame.K_w] and fuel > 0:
            dock_vy -= 185 * dt; fuel -= 3.5 * dt
            if random.random() < 0.5: add_exhaust_particle(dock_ship_x, dock_ship_y + 14, 0, 150)
        if keys[pygame.K_s] and fuel > 0: dock_vy += 90 * dt
        if keys[pygame.K_a] and fuel > 0: dock_vx -= 130 * dt
        if keys[pygame.K_d] and fuel > 0: dock_vx += 130 * dt
            
        dock_ship_x += dock_vx * dt
        dock_ship_y += dock_vy * dt
        
        for ship in dock_traffic_ships:
            if ship["type"] == "FLYING":
                ship["x"] += ship["vx"] * dt
                if ship["x"] < -40: ship["x"] = WIDTH + 30
                if ship["x"] > WIDTH + 40: ship["x"] = -30

        target_y = HEIGHT - 150
        if dock_ship_y >= target_y - 20:
            dock_ship_y = target_y - 20
            if abs(dock_ship_x - WIDTH // 2) < 80 and dock_vy < 45:
                game_state = 'STATION_MENU'
                if cargo and cargo["target"] == active_station["name"]: credits += cargo["reward"]; cargo = None
            else:
                hull = max(0.0, hull - 30.0)
                dock_ship_x, dock_ship_y = WIDTH // 2, 140
                dock_vx, dock_vy = 0.0, 0.0
                current_radio_text = "Věž: Havárie při přistání! Strukturální poškození."
                if hull <= 0: hull, credits = 100.0, max(0, credits - 40); game_state = 'MAIN_MENU'

    # =========================================================================
    # 4. RENDEROVÁNÍ GRAFIKY (ČISTÝ STYLIZOVANÝ 1-BIT)
    # =========================================================================
    screen.fill(BLACK)

    if game_state == 'MAIN_MENU':
        screen.blit(FONT_LG.render("=== SPACE TRUCKER: SIMULATOR ===", True, WHITE), (170, 200))
        screen.blit(FONT_MD.render("Stiskni [ENTER] pro start", True, WHITE), (320, 320))
        screen.blit(FONT_SM.render("NOVINKA: Pohyblivé kolony a čekání na povolení od věže!", True, WHITE), (150, 470))

    elif game_state == 'TRAVEL':
        for star in stars: pygame.draw.circle(screen, WHITE, (int(star["x"]), int(star["y"])), star["size"])
        update_and_draw_particles(screen, dt)
        
        for st in stations:
            screen_st_x = int(WIDTH // 2 + (st["x"] - world_x))
            screen_st_y = int(HEIGHT // 2 + (st["y"] - world_y))
            
            # Orbitální brzdný kruh
            pygame.draw.circle(screen, WHITE, (screen_st_x, screen_st_y), 450, 1)
            
            if -600 <= screen_st_x <= WIDTH + 600 and -600 <= screen_st_y <= HEIGHT + 600:
                # Hlavní tělo stanice
                pygame.draw.circle(screen, WHITE, (screen_st_x, screen_st_y), 35, 2)
                screen.blit(FONT_SM.render(st["name"], True, WHITE), (screen_st_x - 60, screen_st_y - 60))
                
                # VNĚJŠÍ BRÁNA (Geometricky naprosto stejná jako v docking módu – vertikální průchod v ose)
                gate_w, gate_h = 160, 20
                gate_x = screen_st_x - (gate_w // 2)
                gate_y = screen_st_y + 80  # Vjezd umístěn pod stanici
                pygame.draw.rect(screen, WHITE, (gate_x, gate_y, gate_w, gate_h), 2)
                screen.blit(FONT_SM.render("BRÁNA (VJEZD)", True, WHITE), (gate_x + 20, gate_y + 25))
                
                # VYRESLENÍ POHYBLIVÉ KOLONY: Lodě stojí v řadě vertikálně nad bránou a sunou se dolů
                for dist_from_gate in st["queue_ships"]:
                    ship_y = gate_y - int(dist_from_gate)
                    # Vykreslíme je pouze pokud jsou nad bránou
                    if ship_y < gate_y:
                        draw_npc_cargo_ship(screen, screen_st_x - 6, ship_y, 25, 12, vertical=True)
                
                # Textový popisek kolony
                if len(st["queue_ships"]) > 0:
                    screen.blit(FONT_SM.render("kolona (čekající tahače)", True, WHITE), (screen_st_x + 30, gate_y - 60))

        # Vykreslení lodí ve volném vesmíru
        for npc in global_traffic:
            n_x = int(WIDTH // 2 + (npc["world_x"] - world_x))
            n_y = int(HEIGHT // 2 + (npc["world_y"] - world_y))
            if 0 <= n_x <= WIDTH and 0 <= n_y <= HEIGHT:
                draw_npc_cargo_ship(screen, n_x, n_y, npc["size_w"], npc["size_h"])

        draw_heavy_trucker_ship(screen, WIDTH // 2, HEIGHT // 2, player_angle)
        draw_hud_gauges(screen)

        # Kompas a směrování k cíli zakázky
        if cargo:
            target_st = next((s for s in stations if s["name"] == cargo["target"]), None)
            if target_st:
                dx, dy = target_st["x"] - world_x, target_st["y"] - world_y
                angle_to_target = math.atan2(dx, -dy)
                cx, cy = WIDTH - 80, 100
                pygame.draw.circle(screen, WHITE, (cx, cy), 30, 1)
                pygame.draw.line(screen, WHITE, (cx, cy), (cx + int(22 * math.sin(angle_to_target)), cy - int(22 * math.cos(angle_to_target))), 2)
                screen.blit(FONT_SM.render(f"Cíl: {cargo['target']}", True, WHITE), (WIDTH - 320, 150))

        # Spodní informační banner pro řazení v koloně
        if active_station and player_queue_position != -1:
            pygame.draw.rect(screen, BLACK, (WIDTH // 2 - 250, HEIGHT - 180, 500, 45))
            if player_queue_position > 0:
                text = f"ČEKEJTE V KOLONĚ! JSTE {player_queue_position}. V POŘADÍ"
                screen.blit(FONT_MD.render(text, True, WHITE), (WIDTH // 2 - 210, HEIGHT - 170))
            else:
                if int(blinking_timer * 4) % 2 == 0:
                    screen.blit(FONT_MD.render("VAŠE ŘADA! STISKNI [E] PRO VJEZD DO DOKU", True, WHITE), (WIDTH // 2 - 240, HEIGHT - 170))

    elif game_state == 'DOCKING':
        screen.blit(FONT_LG.render("Docking Matrix (Vnitřní Hangár)", True, WHITE), (230, 30))
        
        pad_y = HEIGHT - 150
        # Vnitřní stěny hangáru
        pygame.draw.line(screen, WHITE, (0, 120), (WIDTH, 120), 2) 
        pygame.draw.line(screen, WHITE, (0, pad_y), (WIDTH, pad_y), 2) 

        # VÁŠ PAD - Úplně stejná velikost i design jako vjezdová brána (160 px široký)
        pygame.draw.rect(screen, WHITE, (WIDTH // 2 - 80, pad_y, 160, 20), 2)
        if int(blinking_timer * 4) % 2 == 0:
            pygame.draw.rect(screen, WHITE, (WIDTH // 2 - 80, pad_y, 160, 6))
        screen.blit(FONT_MD.render("VÁŠ PAD (DOCK)", True, WHITE), (WIDTH // 2 - 70, pad_y + 25))

        # Ostatní kóje 01-04 uvnitř stanice
        for obj in dock_traffic_ships:
            if obj["type"] == "KOJE":
                kx, ky = obj["x"], obj["y"]
                if ky == 120:
                    pygame.draw.rect(screen, WHITE, (kx - 80, ky - 20, 160, 20), 1)
                    screen.blit(FONT_SM.render(f"Kóje {obj['label']}", True, WHITE), (kx - 30, ky - 40))
                    if obj["occupied"]: draw_npc_cargo_ship(screen, kx - 20, ky - 16, 35, 12)
                else:
                    pygame.draw.rect(screen, WHITE, (kx - 80, ky, 160, 20), 1)
                    screen.blit(FONT_SM.render(f"Kóje {obj['label']}", True, WHITE), (kx - 30, ky + 25))
                    if obj["occupied"]: draw_npc_cargo_ship(screen, kx - 20, ky + 4, 35, 12)
                        
            elif obj["type"] == "FLYING":
                draw_npc_cargo_ship(screen, int(obj["x"]), int(obj["y"]), 40, 14)

        update_and_draw_particles(screen, dt)
        
        # Loď hráče při přistávání
        pygame.draw.rect(screen, WHITE, (dock_ship_x - 18, dock_ship_y - 10, 36, 20), 2)
        pygame.draw.rect(screen, WHITE, (dock_ship_x - 6, dock_ship_y - 16, 12, 6), 1)
        pygame.draw.line(screen, WHITE, (dock_ship_x - 14, dock_ship_y + 10), (dock_ship_x - 14, dock_ship_y + 14), 2)
        pygame.draw.line(screen, WHITE, (dock_ship_x + 14, dock_ship_y + 10), (dock_ship_x + 14, dock_ship_y + 14), 2)
        
        screen.blit(FONT_SM.render(f"Rychlost klesání:  {int(dock_vy)} m/s", True, WHITE), (50, 150))
        screen.blit(FONT_SM.render(f"Odchylka osy:     {int(dock_ship_x - WIDTH//2)} m", True, WHITE), (50, 180))

    elif game_state == 'STATION_MENU':
        screen.blit(FONT_LG.render(f"STANICE: {active_station['name'] if active_station else 'TERMINAL'}", True, WHITE), (150, 40))
        pygame.draw.line(screen, WHITE, (50, 90), (850, 90), 2)
        screen.blit(FONT_MD.render("MARKET & REPASE TRUPU LODE:", True, WHITE), (50, 130))
        screen.blit(FONT_SM.render("[1] Kompletní dotankování nádrže (Max 250l)  - 20g", True, WHITE), (70, 170))
        screen.blit(FONT_SM.render("[2] Celková oprava pancéřování trupu         - 30g", True, WHITE), (70, 200))
        screen.blit(FONT_MD.render("LOGISTICKÉ CENTRUM - KURÝRNÍ NABÍDKY:", True, WHITE), (50, 280))
        for i, job in enumerate(available_jobs):
            screen.blit(FONT_SM.render(f"[{i+3}] Kontejner do sektoru: {job['target']} | Odměna: {job['reward']}g", True, WHITE), (70, 320 + i * 30))
        screen.blit(FONT_LG.render("Pro ODLET zpět do vesmíru stiskni [U]", True, WHITE), (230, 580))

    # --- GLOBÁLNÍ HUD PANEL ---
    if game_state in ['TRAVEL', 'DOCKING', 'MAP']:
        pygame.draw.rect(screen, WHITE, (110, 10, 250, 95), 1)
        screen.blit(FONT_SM.render(f"Kredity: {credits}g", True, WHITE), (120, 16))
        screen.blit(FONT_SM.render(f"Palivo:  {int(fuel)} / {int(max_fuel)}l", True, WHITE), (120, 34))
        screen.blit(FONT_SM.render(f"Trup:    {int(hull)}%", True, WHITE), (120, 52))
        screen.blit(FONT_SM.render(f"Sektor:  {int(world_x)}, {int(world_y)}", True, WHITE), (120, 70))

        pygame.draw.rect(screen, WHITE, (10, HEIGHT - 50, WIDTH - 20, 40), 1)
        screen.blit(FONT_SM.render(current_radio_text, True, WHITE), (20, HEIGHT - 40))

    pygame.display.flip()

pygame.quit()
sys.exit()