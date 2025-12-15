import pygame
import sys
import random
import copy
import time
import traceback
import os # Diperlukan untuk cek file font
import ctypes # <--- TAMBAHKAN INI

# --- MATIKAN SCALING WINDOWS ---
try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

# ==========================================
# 1. LOGIKA SOLVER (TIDAK BERUBAH DARI KODE ASLI)
# ==========================================
# --- (Bagian ini sama persis dengan kode Anda sebelumnya) ---
ALL_CELLS = [(r, c) for r in range(9) for c in range(9)]

def peers_of(cell):
    r, c = cell
    peers = set()
    for i in range(9):
        if i != c: peers.add((r, i))
        if i != r: peers.add((i, c))
    br = (r // 3) * 3
    bc = (c // 3) * 3
    for rr in range(br, br + 3):
        for cc in range(bc, bc + 3):
            if (rr, cc) != (r, c):
                peers.add((rr, cc))
    return peers

PEERS = {cell: peers_of(cell) for cell in ALL_CELLS}

def is_consistent_assignment(grid):
    for r in range(9):
        seen = set()
        for c in range(9):
            v = grid[r][c]
            if v != 0:
                if v in seen: return False
                seen.add(v)
    for c in range(9):
        seen = set()
        for r in range(9):
            v = grid[r][c]
            if v != 0:
                if v in seen: return False
                seen.add(v)
    for br in range(0,9,3):
        for bc in range(0,9,3):
            seen = set()
            for r in range(br, br+3):
                for c in range(bc, bc+3):
                    v = grid[r][c]
                    if v != 0:
                        if v in seen: return False
                        seen.add(v)
    return True

def initial_domains(grid):
    domains = {}
    for r,c in ALL_CELLS:
        v = grid[r][c]
        if v != 0:
            domains[(r,c)] = {v}
        else:
            domains[(r,c)] = set(range(1,10))
    changed = True
    while changed:
        changed = False
        for cell in ALL_CELLS:
            if len(domains[cell]) == 1:
                val = next(iter(domains[cell]))
                for p in PEERS[cell]:
                    if val in domains[p]:
                        domains[p] = domains[p] - {val}
                        changed = True
    return domains

def forward_check(domains, cell, val):
    dom = copy.deepcopy(domains)
    dom[cell] = {val}
    stack = [cell]
    while stack:
        cur = stack.pop()
        if len(dom[cur]) == 0:
            return None
        if len(dom[cur]) == 1:
            v = next(iter(dom[cur]))
            for p in PEERS[cur]:
                if v in dom[p]:
                    dom[p] = dom[p] - {v}
                    if len(dom[p]) == 0:
                        return None
                    if len(dom[p]) == 1:
                        stack.append(p)
    return dom

def select_unassigned_var(dom):
    unassigned = [(len(dom[cell]), cell) for cell in ALL_CELLS if len(dom[cell]) > 1]
    if not unassigned:
        return None
    unassigned.sort()
    return unassigned[0][1]

def order_values(dom, var):
    vals = list(dom[var])
    def conflicts_count(v):
        cnt = 0
        for p in PEERS[var]:
            if v in dom[p]:
                cnt += 1
        return cnt
    vals.sort(key=conflicts_count)
    return vals

def domains_to_grid(dom):
    grid = [[0]*9 for _ in range(9)]
    for (r,c), d in dom.items():
        if len(d) == 1:
            grid[r][c] = next(iter(d))
    return grid

def csp_backtrack(dom, limit_nodes=None):
    nodes = {'count':0}
    def backtrack(d):
        if limit_nodes and nodes['count'] > limit_nodes:
            return None
        nodes['count'] += 1
        var = select_unassigned_var(d)
        if var is None:
            return d
        for val in order_values(d, var):
            newd = forward_check(d, var, val)
            if newd is not None:
                res = backtrack(newd)
                if res is not None:
                    return res
        return None
    return backtrack(dom)

def solve_grid(grid, limit_nodes=None):
    if not is_consistent_assignment(grid):
        return None
    dom = initial_domains(grid)
    sol_dom = csp_backtrack(dom, limit_nodes=limit_nodes)
    if sol_dom is None:
        return None
    return domains_to_grid(sol_dom)

def count_solutions(grid, max_count=2):
    if not is_consistent_assignment(grid):
        return 0
    dom = initial_domains(grid)
    count = 0
    def backtrack(d):
        nonlocal count
        if count >= max_count: return
        var = select_unassigned_var(d)
        if var is None:
            count += 1
            return
        for val in order_values(d, var):
            newd = forward_check(d, var, val)
            if newd is not None:
                backtrack(newd)
                if count >= max_count: return
    backtrack(dom)
    return count

def generate_solved_board():
    grid = [[0]*9 for _ in range(9)]
    def fill(idx=0):
        if idx == 81:
            return True
        r, c = divmod(idx, 9)
        nums = list(range(1,10))
        random.shuffle(nums)
        for n in nums:
            grid[r][c] = n
            if is_consistent_assignment(grid):
                if fill(idx+1):
                    return True
        grid[r][c] = 0
        return False
    if not fill():
        raise RuntimeError("failed to generate solved board")
    return grid

def generate_puzzle(removals=40):
    print(f"[DEBUG] Generating puzzle with {removals} removals...")
    solved = generate_solved_board()
    puzzle = copy.deepcopy(solved)
    positions = [(r,c) for r in range(9) for c in range(9)]
    random.shuffle(positions)
    removed = 0
    for (r,c) in positions:
        if removed >= removals: break
        backup = puzzle[r][c]
        puzzle[r][c] = 0
        cnt = count_solutions(puzzle, max_count=2)
        if cnt != 1:
            puzzle[r][c] = backup
        else:
            removed += 1
    print("[DEBUG] Puzzle generated successfully.")
    return puzzle, solved

# ==========================================
# 2. UI CONFIG (MODIFIED LAYOUT & FONTS)
# ==========================================
print("[DEBUG] Initializing Pygame...")
pygame.init()
FPS = 60

# --- LAYOUT BARU (LEBIH LEBAR UNTUK SIDEBAR) ---
WINDOW_W, WINDOW_H = 1050, 760  # Diperlebar agar muat 2 kolom
CELL = 64
MARGIN_TOP = 70
MARGIN_LEFT = 60 # Margin kiri untuk papan
SIDEBAR_X = MARGIN_LEFT + (CELL * 9) + 60 # Posisi mulai sidebar kanan

# --- COLOR PALETTE (SAMA SEPERTI KODE ASLI) ---
C_BG = (240, 244, 248)
C_BOARD_BG = (255, 255, 255)
C_SHADOW = (180, 190, 200)
C_GRID_THIN = (210, 220, 230)
C_GRID_THICK = (52, 73, 94)
C_CELL_SELECT = (212, 230, 241)
C_CELL_HOVER = (235, 245, 251)
C_TEXT_GIVEN = (44, 62, 80)
C_TEXT_USER = (41, 128, 185)
C_TEXT_ERROR = (231, 76, 60)
C_TEXT_SUCCESS = (39, 174, 96)
C_BTN_NORMAL = (52, 152, 219)
C_BTN_HOVER = (41, 128, 185)
C_BTN_TEXT = (255, 255, 255)
C_MENU_BTN_EASY = (46, 204, 113)
C_MENU_BTN_MED = (241, 196, 15)
C_MENU_BTN_HARD = (231, 76, 60)
C_TEXT_LIGHT = (149, 165, 166) # Warna baru untuk teks label kecil

print("[DEBUG] Setting display mode...")
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
pygame.display.set_caption("Sudoku Modern CSP")
clock = pygame.time.Clock()

# --- FONT LOADING (MODIFIED UNTUK TAMPILAN GAMBAR) ---
# Mencoba memuat font eksternal agar mirip gambar.
# PASTIKAN 'font_bold.ttf' dan 'font_reg.ttf' ada di folder yang sama.
print("[DEBUG] Loading Fonts...")
font_bold_path = "font_bold.ttf"
font_reg_path = "font_reg.ttf"

# Gunakan font Montserrat/Roboto jika ada, jika tidak kembali ke default
use_custom_font = os.path.exists(font_bold_path) and os.path.exists(font_reg_path)

if use_custom_font:
    print("[DEBUG] Custom fonts found. Using them.")
    FONT_TITLE_BIG = pygame.font.Font(font_bold_path, 72)
    FONT_TITLE = pygame.font.Font(font_bold_path, 48)
    FONT_SUBTITLE = pygame.font.Font(font_reg_path, 24)
    FONT_CELL = pygame.font.Font(font_bold_path, 42)
    FONT_BTN = pygame.font.Font(font_bold_path, 20)
    FONT_STATUS = pygame.font.Font(font_bold_path, 28)
    FONT_SCORE_LBL = pygame.font.Font(font_reg_path, 16)
    FONT_SCORE_BIG = pygame.font.Font(font_bold_path, 64)
    FONT_STATS = pygame.font.Font(font_bold_path, 20)
else:
    print("[WARNING] Custom fonts NOT found (font_bold.ttf, font_reg.ttf). Using default font (looks less modern).")
    FONT_TITLE_BIG = pygame.font.Font(None, 80)
    FONT_TITLE = pygame.font.Font(None, 60)
    FONT_SUBTITLE = pygame.font.Font(None, 28)
    FONT_CELL = pygame.font.Font(None, 50)
    FONT_BTN = pygame.font.Font(None, 24)
    FONT_STATUS = pygame.font.Font(None, 32)
    FONT_SCORE_LBL = pygame.font.Font(None, 20)
    FONT_SCORE_BIG = pygame.font.Font(None, 70)
    FONT_STATS = pygame.font.Font(None, 24)


# Global Variables
game_state = "MENU"
puzzle = []
solved_board = []
grid = []
given = []
selected = (0,0)
message = ""
solved_by_solver = None
start_time = 0

# Scoring
BASE_SCORE = 10000
score = BASE_SCORE
mistake_penalty_count = 0
hint_penalty_count = 0
current_removals = 40
difficulty_name = "Medium"

def start_game(removals, diff_name):
    global puzzle, solved_board, grid, given, selected, message, start_time, game_state
    global score, mistake_penalty_count, hint_penalty_count, current_removals, difficulty_name

    print(f"[DEBUG] Starting game: {diff_name}")
    screen.fill(C_BG)
    load_text = FONT_TITLE.render("Generating Puzzle...", True, C_GRID_THICK)
    screen.blit(load_text, ((WINDOW_W - load_text.get_width())//2, WINDOW_H//2))
    pygame.display.flip()

    current_removals = removals
    difficulty_name = diff_name
    puzzle, solved_board = generate_puzzle(removals=current_removals)
    grid = copy.deepcopy(puzzle)
    given = [[(puzzle[r][c] != 0) for c in range(9)] for r in range(9)]
    selected = (0,0)

    score = BASE_SCORE
    mistake_penalty_count = 0
    hint_penalty_count = 0

    message = "Ready"
    start_time = time.time()
    game_state = "PLAYING"
    print("[DEBUG] Game State switched to PLAYING")

def get_current_score():
    if game_state == "MENU": return BASE_SCORE
    if game_state == "FINISHED" and solved_by_solver: return 0

    elapsed = int(time.time() - start_time)
    if game_state == "FINISHED":
         # Stop clock if finished nicely
         elapsed = int(end_time - start_time)

    final_score = BASE_SCORE - (hint_penalty_count * 1000) - (mistake_penalty_count * 500) - (elapsed * 2)
    return max(0, final_score)

# --- VISUAL HELPERS ---
def draw_rounded_rect(surface, color, rect, radius=10):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_shadow_rect(surface, rect, radius=10, offset=4, color=C_SHADOW):
    shadow_rect = (rect[0]+offset, rect[1]+offset, rect[2], rect[3])
    pygame.draw.rect(surface, color, shadow_rect, border_radius=radius)

def draw_interactive_button(text, x, y, w, h, base_color, hover_color, action_name, mouse_pos, text_color=C_BTN_TEXT, shadow_offset=3):
    is_hover = (x <= mouse_pos[0] <= x+w and y <= mouse_pos[1] <= y+h)
    color = hover_color if is_hover else base_color

    draw_shadow_rect(screen, (x, y, w, h), radius=8, offset=shadow_offset)
    draw_rounded_rect(screen, color, (x, y, w, h), radius=8)

    surf = FONT_BTN.render(text, True, text_color)
    screen.blit(surf, (x + (w - surf.get_width())//2, y + (h - surf.get_height())//2))

    return action_name if is_hover else None

# --- SCREENS ---
def draw_menu():
    screen.fill(C_BG)
    mouse_pos = pygame.mouse.get_pos()

    # Title (Matches image_1.png)
    title = FONT_TITLE_BIG.render("SUDOKU", True, C_BTN_NORMAL)
    screen.blit(title, ((WINDOW_W - title.get_width())//2, 150))

    sub = FONT_SUBTITLE.render("CSP SOLVER", True, C_GRID_THICK)
    screen.blit(sub, ((WINDOW_W - sub.get_width())//2, 230))

    lbl = FONT_SCORE_LBL.render("SELECT DIFFICULTY", True, C_TEXT_LIGHT)
    screen.blit(lbl, ((WINDOW_W - lbl.get_width())//2, 300))

    # Buttons centered vertically
    btn_w, btn_h = 280, 65
    bx = (WINDOW_W - btn_w)//2
    start_y = 350
    gap = 85

    # Menggunakan style putih dengan teks berwarna seperti di gambar modern
    draw_interactive_button("EASY", bx, start_y, btn_w, btn_h, C_BOARD_BG, C_CELL_HOVER, "Easy", mouse_pos, text_color=C_MENU_BTN_EASY, shadow_offset=4)
    draw_interactive_button("MEDIUM", bx, start_y+gap, btn_w, btn_h, C_BOARD_BG, C_CELL_HOVER, "Medium", mouse_pos, text_color=C_MENU_BTN_MED, shadow_offset=4)
    draw_interactive_button("HARD", bx, start_y+gap*2, btn_w, btn_h, C_BOARD_BG, C_CELL_HOVER, "Hard", mouse_pos, text_color=C_MENU_BTN_HARD, shadow_offset=4)

def draw_board():
    screen.fill(C_BG)
    mouse_pos = pygame.mouse.get_pos()
    current_pts = get_current_score()
    elapsed = int(time.time() - start_time) if game_state == "PLAYING" else 0
    mins, secs = divmod(elapsed, 60)

    # ================= LEFT SIDE: BOARD =================
    board_rect = (MARGIN_LEFT, MARGIN_TOP, CELL*9, CELL*9)
    draw_shadow_rect(screen, board_rect, radius=8, offset=6)
    draw_rounded_rect(screen, C_BOARD_BG, board_rect, radius=8)

    # Selection & Hover
    sr, sc = selected
    pygame.draw.rect(screen, C_CELL_SELECT, (MARGIN_LEFT + sc*CELL, MARGIN_TOP + sr*CELL, CELL, CELL))

    if MARGIN_LEFT <= mouse_pos[0] < MARGIN_LEFT + 9*CELL and MARGIN_TOP <= mouse_pos[1] < MARGIN_TOP + 9*CELL:
        hc = (mouse_pos[0] - MARGIN_LEFT) // CELL
        hr = (mouse_pos[1] - MARGIN_TOP) // CELL
        if (hr,hc) != selected:
             pygame.draw.rect(screen, C_CELL_HOVER, (MARGIN_LEFT + hc*CELL, MARGIN_TOP + hr*CELL, CELL, CELL))

    # Numbers
    for r in range(9):
        for c in range(9):
            x = MARGIN_LEFT + c*CELL; y = MARGIN_TOP + r*CELL
            v = grid[r][c]
            if v != 0:
                color = C_TEXT_GIVEN if given[r][c] else C_TEXT_USER
                surf = FONT_CELL.render(str(v), True, color)
                # Center vertically and horizontally slightly better
                text_rect = surf.get_rect(center=(x + CELL//2, y + CELL//2 + 3))
                screen.blit(surf, text_rect)

    # Grid Lines (Updated positions)
    for i in range(10):
        pos = MARGIN_LEFT + i*CELL
        pygame.draw.line(screen, C_GRID_THIN, (pos, MARGIN_TOP), (pos, MARGIN_TOP + 9*CELL), 1)
        pos_y = MARGIN_TOP + i*CELL
        pygame.draw.line(screen, C_GRID_THIN, (MARGIN_LEFT, pos_y), (MARGIN_LEFT + 9*CELL, pos_y), 1)
    for i in range(0, 10, 3):
        pos = MARGIN_LEFT + i*CELL
        pygame.draw.line(screen, C_GRID_THICK, (pos, MARGIN_TOP), (pos, MARGIN_TOP + 9*CELL), 3)
        pos_y = MARGIN_TOP + i*CELL
        pygame.draw.line(screen, C_GRID_THICK, (MARGIN_LEFT, pos_y), (MARGIN_LEFT + 9*CELL, pos_y), 3)
    pygame.draw.rect(screen, C_GRID_THICK, board_rect, 3, border_radius=8)

    # ================= RIGHT SIDE: SIDEBAR (Matches image_0.png) =================
    sidebar_y = MARGIN_TOP - 20
    
    # Title & Info
    title_surf = FONT_TITLE.render("Sudoku", True, C_GRID_THICK)
    screen.blit(title_surf, (SIDEBAR_X, sidebar_y))

    info_surf = FONT_SUBTITLE.render(f"{difficulty_name.upper()}  CSP Solver", True, C_TEXT_LIGHT)
    screen.blit(info_surf, (SIDEBAR_X, sidebar_y + 50))

    # --- SCORE CARD ---
    card_y = sidebar_y + 100
    card_w, card_h = 300, 150
    draw_shadow_rect(screen, (SIDEBAR_X, card_y, card_w, card_h), radius=12, offset=4, color=(220,230,240))
    draw_rounded_rect(screen, C_BOARD_BG, (SIDEBAR_X, card_y, card_w, card_h), radius=12)

    score_lbl = FONT_SCORE_LBL.render("CURRENT SCORE", True, C_TEXT_LIGHT)
    screen.blit(score_lbl, (SIDEBAR_X + (card_w-score_lbl.get_width())//2, card_y + 25))

    score_val_surf = FONT_SCORE_BIG.render(str(current_pts), True, C_BTN_NORMAL)
    screen.blit(score_val_surf, (SIDEBAR_X + (card_w-score_val_surf.get_width())//2, card_y + 55))

    # --- STATS ---
    stats_y = card_y + card_h + 30
    
    # Time
    time_lbl = FONT_STATS.render("Time", True, C_TEXT_LIGHT)
    time_val = FONT_STATS.render(f"{mins:02d}:{secs:02d}", True, C_GRID_THICK)
    screen.blit(time_lbl, (SIDEBAR_X, stats_y))
    screen.blit(time_val, (SIDEBAR_X + card_w - time_val.get_width(), stats_y))

    # Mistakes
    mis_y = stats_y + 35
    mis_lbl = FONT_STATS.render("Mistakes (-500)", True, C_TEXT_LIGHT)
    mis_val = FONT_STATS.render(str(mistake_penalty_count), True, C_TEXT_ERROR)
    screen.blit(mis_lbl, (SIDEBAR_X, mis_y))
    screen.blit(mis_val, (SIDEBAR_X + card_w - mis_val.get_width(), mis_y))

    # Hints
    hint_y = mis_y + 35
    hint_lbl = FONT_STATS.render("Hints (-1000)", True, C_TEXT_LIGHT)
    hint_val = FONT_STATS.render(str(hint_penalty_count), True, (241, 196, 15)) # Orange-ish
    screen.blit(hint_lbl, (SIDEBAR_X, hint_y))
    screen.blit(hint_val, (SIDEBAR_X + card_w - hint_val.get_width(), hint_y))


    # --- ACTION BUTTONS (GRID 2x2) ---
    btn_start_y = hint_y + 50
    btn_w_small, btn_h_small = 140, 50
    btn_gap = 20
    
    # Row 1
    draw_interactive_button("Solve", SIDEBAR_X, btn_start_y, btn_w_small, btn_h_small, C_BOARD_BG, C_CELL_HOVER, "Solve", mouse_pos, text_color=C_BTN_NORMAL)
    draw_interactive_button("Hint", SIDEBAR_X + btn_w_small + btn_gap, btn_start_y, btn_w_small, btn_h_small, C_BOARD_BG, C_CELL_HOVER, "Hint", mouse_pos, text_color=(243, 156, 18))
    
    # Row 2
    btn_row2_y = btn_start_y + btn_h_small + btn_gap
    draw_interactive_button("Check", SIDEBAR_X, btn_row2_y, btn_w_small, btn_h_small, C_BOARD_BG, C_CELL_HOVER, "Validate", mouse_pos, text_color=C_TEXT_SUCCESS)
    draw_interactive_button("Clear", SIDEBAR_X + btn_w_small + btn_gap, btn_row2_y, btn_w_small, btn_h_small, C_BOARD_BG, C_CELL_HOVER, "Clear", mouse_pos, text_color=C_TEXT_ERROR)

    # --- BACK BUTTON (WIDE) ---
    back_y = btn_row2_y + btn_h_small + 30
    back_w = btn_w_small * 2 + btn_gap
    draw_interactive_button("Back to Menu", SIDEBAR_X, back_y, back_w, 55, (220, 225, 230), (200, 205, 210), "Back", mouse_pos, text_color=C_GRID_THICK, shadow_offset=2)

    # Status Message (Bottom left)
    if message:
        msg_color = C_TEXT_ERROR if "Wrong" in message or "Invalid" in message or "Board full" in message else C_GRID_THICK
        msg_surf = FONT_STATUS.render(message, True, msg_color)
        screen.blit(msg_surf, (MARGIN_LEFT, MARGIN_TOP + 9*CELL + 25))

# --- CLICK HANDLING UPDATED FOR NEW LAYOUT ---
def click_button_check_game(pos):
    mx, my = pos
    # Sidebar area bounds
    if mx < SIDEBAR_X: return None
    
    btn_w_small, btn_h_small = 140, 50
    btn_gap = 20
    
    # Calculate Y positions based on draw_board logic
    sidebar_y = MARGIN_TOP - 20
    card_y = sidebar_y + 100
    card_h = 150
    stats_y = card_y + card_h + 30
    hint_y = stats_y + 35 + 35
    btn_start_y = hint_y + 50
    btn_row2_y = btn_start_y + btn_h_small + btn_gap
    back_y = btn_row2_y + btn_h_small + 30
    back_w = btn_w_small * 2 + btn_gap

    # Check 2x2 Grid
    # Top Left (Solve)
    if SIDEBAR_X <= mx <= SIDEBAR_X + btn_w_small and btn_start_y <= my <= btn_start_y + btn_h_small: return "Solve"
    # Top Right (Hint)
    if SIDEBAR_X + btn_w_small + btn_gap <= mx <= SIDEBAR_X + btn_w_small*2 + btn_gap and btn_start_y <= my <= btn_start_y + btn_h_small: return "Hint"
    # Bottom Left (Check)
    if SIDEBAR_X <= mx <= SIDEBAR_X + btn_w_small and btn_row2_y <= my <= btn_row2_y + btn_h_small: return "Validate"
    # Bottom Right (Clear)
    if SIDEBAR_X + btn_w_small + btn_gap <= mx <= SIDEBAR_X + btn_w_small*2 + btn_gap and btn_row2_y <= my <= btn_row2_y + btn_h_small: return "Clear"
    
    # Check Back Button
    if SIDEBAR_X <= mx <= SIDEBAR_X + back_w and back_y <= my <= back_y + 55: return "Back"

    return None

def check_menu_click(pos):
    btn_w, btn_h = 280, 65
    bx = (WINDOW_W - btn_w)//2
    start_y = 350
    gap = 85
    mx, my = pos
    
    if bx <= mx <= bx + btn_w:
        if start_y <= my <= start_y + btn_h: return (30, "Easy")
        if start_y+gap <= my <= start_y+gap+btn_h: return (45, "Medium")
        if start_y+gap*2 <= my <= start_y+gap*2+btn_h: return (55, "Hard")
    return None

def flash_wrong_cell(r, c):
    # Updated coordinates for flash
    x = MARGIN_LEFT + c*CELL; y = MARGIN_TOP + r*CELL
    rect = (x,y,CELL,CELL)
    for _ in range(2):
        pygame.draw.rect(screen, C_TEXT_ERROR, rect)
        pygame.display.update(rect)
        pygame.time.delay(100)
        draw_board() # Redraw board to clear flash
        pygame.display.update(rect)
        pygame.time.delay(50)

# --- ACTIONS ---
def provide_hint():
    global message, hint_penalty_count
    if game_state != "PLAYING": return
    sol = solved_board if solved_board else solve_grid(grid)
    if sol is None:
        message = "No solution available."
        return
    
    # Try to fill randomly instead of top-left first
    empty_cells = [(r,c) for r in range(9) for c in range(9) if not given[r][c] and grid[r][c] == 0]
    if not empty_cells:
        message = "Board full."
        return

    r, c = random.choice(empty_cells)
    grid[r][c] = sol[r][c]
    hint_penalty_count += 1
    message = "Hint used."

def validate_action():
    global message
    if game_state != "PLAYING": return
    if not is_consistent_assignment(grid):
        message = "Invalid: conflicts found."
    elif all(grid[r][c] != 0 for r in range(9) for c in range(9)):
        message = "Correct! Board Complete."
    else:
        message = "Looks good so far (incomplete)."

def clear_action():
    global grid, message
    if game_state != "PLAYING": return
    for r in range(9):
        for c in range(9):
            if not given[r][c]:
                grid[r][c] = 0
    message = "Board cleared (givens remain)."

def back_action():
    global game_state
    game_state = "MENU"

def solve_action():
    global grid, message, solved_by_solver, score, game_state, end_time
    if game_state != "PLAYING": return
    message = "Solving..."
    draw_board()
    pygame.display.flip()
    sol = solve_grid(grid)
    if sol is None:
        message = "Unsolvable configuration."
    else:
        grid = sol
        solved_by_solver = True
        score = 0
        message = "Auto-Solved (0 pts)."
        game_state = "FINISHED"
        end_time = time.time()

def handle_keydown(event):
    global selected, mistake_penalty_count, message, game_state, end_time
    if game_state != "PLAYING": return

    sr, sc = selected
    if event.key == pygame.K_LEFT: selected = (sr, max(sc-1, 0))
    elif event.key == pygame.K_RIGHT: selected = (sr, min(sc+1, 8))
    elif event.key == pygame.K_UP: selected = (max(sr-1,0), sc)
    elif event.key == pygame.K_DOWN: selected = (min(sr+1,8), sc)
    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9):
        if given[sr][sc]: return
        try: num = int(event.unicode)
        except: return 
        temp = grid[sr][sc]
        grid[sr][sc] = num
        if is_consistent_assignment(grid):
            message = ""
            if all(grid[r][c] != 0 for r in range(9) for c in range(9)):
                game_state = "FINISHED"
                end_time = time.time()
        else:
            grid[sr][sc] = temp
            mistake_penalty_count += 1
            message = "Wrong move!"
            flash_wrong_cell(sr, sc)
    elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
        if not given[sr][sc]: grid[sr][sc] = 0

# ==========================================
# 3. MAIN LOOP
# ==========================================
def main():
    global selected, end_time
    print("[DEBUG] Entering Main Loop...")
    running = True
    end_time = 0
    try:
        while running:
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if game_state == "MENU":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        result = check_menu_click(event.pos)
                        if result:
                            removals, name = result
                            start_game(removals, name)
                
                elif game_state in ["PLAYING", "FINISHED"]:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mx, my = event.pos
                        # Check board click first
                        if MARGIN_LEFT <= mx < MARGIN_LEFT + 9*CELL and MARGIN_TOP <= my < MARGIN_TOP + 9*CELL:
                             if game_state == "PLAYING":
                                c = (mx - MARGIN_LEFT) // CELL
                                r = (my - MARGIN_TOP) // CELL
                                selected = (r,c)
                        else:
                            # Check sidebar buttons
                            action = click_button_check_game(event.pos)
                            if action == "Solve": solve_action()
                            elif action == "Hint": provide_hint()
                            elif action == "Validate": validate_action()
                            elif action == "Clear": clear_action()
                            elif action == "Back": back_action()
                    
                    elif event.type == pygame.KEYDOWN:
                        handle_keydown(event)
            
            # DRAWING
            if game_state == "MENU":
                draw_menu()
            else:
                draw_board()
                # Overlay sederhana jika selesai
                if game_state == "FINISHED" and not solved_by_solver:
                     surf = FONT_STATUS.render("PUZZLE COMPLETED!", True, C_TEXT_SUCCESS)
                     draw_rounded_rect(screen, C_BOARD_BG, (MARGIN_LEFT + 9*CELL//2 - surf.get_width()//2 - 20, MARGIN_TOP + 9*CELL//2 - 30, surf.get_width()+40, 60))
                     screen.blit(surf, (MARGIN_LEFT + 9*CELL//2 - surf.get_width()//2, MARGIN_TOP + 9*CELL//2 - 10))


            pygame.display.flip()
            
    except Exception as e:
        print("\n[CRITICAL ERROR] Program Crashed!")
        traceback.print_exc()
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()