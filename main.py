import math
import random
import sys
from array import array

import pygame


pygame.init()
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
except pygame.error:
    pass

WIDTH, HEIGHT = 920, 700
flags = pygame.SCALED if hasattr(pygame, "SCALED") else 0
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT), flags)
pygame.display.set_caption("Cabo")
CLOCK = pygame.time.Clock()

BG = (24, 105, 87)
BG_DARK = (17, 79, 66)
PANEL = (16, 72, 62)
WHITE = (248, 246, 232)
GOLD = (250, 205, 86)
RED = (190, 48, 55)
BLACK = (34, 39, 43)
BLUE = (54, 114, 173)
GRAY = (190, 196, 190)

FONT = pygame.font.SysFont("arial", 22)
SMALL = pygame.font.SysFont("arial", 16)
CARD_FONT = pygame.font.SysFont("arial", 24, bold=True)
BIG = pygame.font.SysFont("arial", 34, bold=True)

CARD_W, CARD_H = 92, 128
MOVING_CARD_CACHE = {}
HUMAN_X = [135, 250, 365, 480]
CPU_X = [135, 250, 365, 480]
CARD_Y_HUMAN = 490
CARD_Y_CPU = 105
CPU_DIFFICULTY = "Balanced"


def make_tone(notes):
    if not pygame.mixer.get_init():
        return None
    sample_rate = pygame.mixer.get_init()[0]
    samples = array("h")
    for frequency, duration in notes:
        count = int(sample_rate * duration)
        for i in range(count):
            fade = min(1.0, i / 180, (count - i) / 450)
            value = int(10500 * fade * math.sin(2 * math.pi * frequency * i / sample_rate))
            samples.append(value)
    try:
        return pygame.mixer.Sound(buffer=samples.tobytes())
    except pygame.error:
        return None


def make_shuffle_sound():
    if not pygame.mixer.get_init():
        return None
    sample_rate = pygame.mixer.get_init()[0]
    duration = 1.25
    count = int(sample_rate * duration)
    samples = array("h")
    filtered_noise = 0.0
    for i in range(count):
        t = i / sample_rate
        pulse_phase = (t % 0.17) / 0.17
        pulse = max(0.0, 1.0 - pulse_phase / 0.78)
        pulse = pulse * pulse * (0.72 + random.random() * 0.28)
        fade = min(1.0, t / 0.06, (duration - t) / 0.16)
        filtered_noise = filtered_noise * 0.72 + random.uniform(-1.0, 1.0) * 0.28
        click = random.uniform(-1.0, 1.0) * max(0.0, 1.0 - pulse_phase * 18) * 0.35
        value = (filtered_noise * pulse + click) * fade * 7800
        samples.append(max(-32768, min(32767, int(value))))
    try:
        return pygame.mixer.Sound(buffer=samples.tobytes())
    except pygame.error:
        return None


def make_spread_sound():
    if not pygame.mixer.get_init():
        return None
    sample_rate = pygame.mixer.get_init()[0]
    duration = 0.95
    count = int(sample_rate * duration)
    samples = array("h")
    filtered_noise = 0.0
    starts = [0.04, 0.22, 0.40, 0.58]
    for i in range(count):
        t = i / sample_rate
        filtered_noise = filtered_noise * 0.68 + random.uniform(-1.0, 1.0) * 0.32
        value = 0.0
        for start in starts:
            progress = (t - start) / 0.19
            if 0.0 <= progress <= 1.0:
                envelope = math.sin(math.pi * progress) ** 1.4
                value += filtered_noise * envelope * 3300
                if progress < 0.025:
                    value += random.uniform(-1.0, 1.0) * (1.0 - progress / 0.025) * 1100
        samples.append(max(-32768, min(32767, int(value))))
    try:
        return pygame.mixer.Sound(buffer=samples.tobytes())
    except pygame.error:
        return None


def make_card_sound(kind):
    if not pygame.mixer.get_init():
        return None
    sample_rate = pygame.mixer.get_init()[0]
    duration, volume, decay = {
        "draw": (0.18, 6200, 0.72),
        "discard": (0.14, 7000, 0.80),
        "peek": (0.11, 4200, 0.88),
    }[kind]
    samples = array("h")
    filtered_noise = 0.0
    count = int(sample_rate * duration)
    for i in range(count):
        progress = i / count
        filtered_noise = filtered_noise * decay + random.uniform(-1.0, 1.0) * (1.0 - decay)
        envelope = (1.0 - progress) ** 2
        click = random.uniform(-1.0, 1.0) * max(0.0, 1.0 - progress * 35)
        value = (filtered_noise * 0.75 + click * 0.25) * envelope * volume
        samples.append(max(-32768, min(32767, int(value))))
    try:
        return pygame.mixer.Sound(buffer=samples.tobytes())
    except pygame.error:
        return None


SOUNDS = {
    "shuffle": make_shuffle_sound(),
    "spread": make_spread_sound(),
    "draw": make_card_sound("draw"),
    "discard": make_card_sound("discard"),
    "peek": make_card_sound("peek"),
    "swap": make_tone([(620, 0.09), (880, 0.12)]),
    "cabo": make_tone([(659, 0.13), (880, 0.16), (1175, 0.25)]),
}


def play_sound(name):
    sound = SOUNDS.get(name)
    if sound is not None:
        sound.play()


def new_deck():
    return [(rank, suit) for suit in range(4) for rank in range(1, 14)]


def card_value(card):
    return card[0]


def rank_name(rank):
    return {1: "A", 11: "J", 12: "Q", 13: "K"}.get(rank, str(rank))


def suit_symbol(suit):
    return ["â™£", "â™¦", "â™¥", "â™ "][suit]


def suit_color(suit):
    return RED if suit in (1, 2) else BLACK


def card_rect(x, y):
    return pygame.Rect(x, y, CARD_W, CARD_H)


def draw_card(surface, x, y, card=None, hidden=False, selected=False, hover=True):
    rect = card_rect(x, y)
    if hover and rect.collidepoint(pygame.mouse.get_pos()):
        y -= 6
        rect = card_rect(x, y)
        selected = True
    # Offset shadow and exposed lower edge give each card a raised, layered look.
    shadow = rect.move(4, 6)
    pygame.draw.rect(surface, (12, 43, 38), shadow, border_radius=9)
    pygame.draw.rect(surface, (205, 198, 174), rect.move(0, 3), border_radius=8)

    if hidden:
        pygame.draw.rect(surface, (26, 53, 125), rect, border_radius=8)
        pygame.draw.rect(surface, (226, 222, 196), rect, 3, border_radius=8)
        inner = rect.inflate(-12, -12)
        pygame.draw.rect(surface, (57, 99, 174), inner, 2, border_radius=5)
        pygame.draw.line(surface, (178, 203, 229), (x + 21, y + 27), (x + 70, y + 100), 2)
        pygame.draw.line(surface, (178, 203, 229), (x + 70, y + 27), (x + 21, y + 100), 2)
        pygame.draw.line(surface, (113, 155, 207), (x + 10, y + 12), (x + 10, y + CARD_H - 12), 2)
    else:
        pygame.draw.rect(surface, WHITE, rect, border_radius=8)
        pygame.draw.rect(surface, GOLD if selected else (70, 70, 70), rect, 4 if selected else 2, border_radius=8)
        pygame.draw.line(surface, (255, 255, 255), (x + 11, y + 7), (x + CARD_W - 12, y + 7), 2)
        if card:
            color = suit_color(card[1])
            rank = CARD_FONT.render(rank_name(card[0]), True, color)
            symbol = CARD_FONT.render(suit_symbol(card[1]), True, color)
            surface.blit(rank, (x + 10, y + 8))
            surface.blit(symbol, (x + 11, y + 36))
            center_rank = BIG.render(rank_name(card[0]), True, color)
            surface.blit(center_rank, center_rank.get_rect(center=(x + CARD_W // 2, y + 84)))
    return rect


def draw_moving_card(surface, x, y, card=None, hidden=False, angle=0, scale=1.0):
    key = (tuple(card) if card is not None else None, hidden)
    image = MOVING_CARD_CACHE.get(key)
    if image is None:
        image = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
        draw_card(image, 0, 0, card, hidden=hidden, hover=False)
        MOVING_CARD_CACHE[key] = image

    # The card sprite already has a layered edge and shadow; reuse it instead
    # of allocating and rotating new surfaces on every animation frame.
    surface.blit(image, (int(x), int(y)))


def draw_animation_frame(background, previous_rects, sprites):
    dirty_rects = list(previous_rects)
    for rect in previous_rects:
        SCREEN.blit(background, rect, rect)

    current_rects = []
    for x, y, card, hidden in sprites:
        rect = pygame.Rect(int(x), int(y), CARD_W, CARD_H)
        current_rects.append(rect)
        dirty_rects.append(rect)
        draw_moving_card(SCREEN, x, y, card, hidden=hidden)

    pygame.display.update(dirty_rects)
    return current_rects


def animate_card_transfer(card, start, end, hidden=False, duration=440):
    background = SCREEN.copy()
    previous_rects = []
    started = pygame.time.get_ticks()
    while True:
        progress = min(1.0, (pygame.time.get_ticks() - started) / duration)
        eased = progress * progress * (3 - 2 * progress)
        x = start[0] + (end[0] - start[0]) * eased
        y = start[1] + (end[1] - start[1]) * eased - math.sin(math.pi * progress) * 34
        previous_rects = draw_animation_frame(
            background, previous_rects, [(x, y, card, hidden)]
        )
        if progress >= 1.0:
            break
        CLOCK.tick(60)


def animate_card_exchange(first_card, first_start, first_end, second_card, second_start, second_end, duration=480):
    background = SCREEN.copy()
    previous_rects = []
    started = pygame.time.get_ticks()
    while True:
        progress = min(1.0, (pygame.time.get_ticks() - started) / duration)
        eased = progress * progress * (3 - 2 * progress)
        sprites = []
        for card, start, end, arc in (
            (first_card, first_start, first_end, -38),
            (second_card, second_start, second_end, 38),
        ):
            x = start[0] + (end[0] - start[0]) * eased
            y = start[1] + (end[1] - start[1]) * eased + math.sin(math.pi * progress) * arc
            sprites.append((x, y, None, True))
        previous_rects = draw_animation_frame(background, previous_rects, sprites)
        if progress >= 1.0:
            break
        CLOCK.tick(60)


def draw_button(surface, rect, label, enabled=True, color=BLUE):
    fill = color if enabled else (104, 111, 108)
    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, WHITE, rect, 2, border_radius=8)
    text = FONT.render(label, True, WHITE)
    surface.blit(text, text.get_rect(center=rect.center))


def text(surface, value, x, y, font=FONT, color=WHITE, center=False):
    image = font.render(value, True, color)
    rect = image.get_rect(center=(x, y)) if center else image.get_rect(topleft=(x, y))
    surface.blit(image, rect)


def animate_new_game():
    play_sound("shuffle")
    background = pygame.Surface((WIDTH, HEIGHT))
    background.fill(BG)
    pygame.draw.rect(background, BG_DARK, (0, 0, WIDTH, 110))
    text(background, "CABO", WIDTH // 2, 48, BIG, GOLD, True)
    text(background, "Shuffling and dealing...", WIDTH // 2, 185, FONT, WHITE, True)
    SCREEN.blit(background, (0, 0))
    pygame.display.flip()

    start = pygame.time.get_ticks()
    duration = 1350
    spread_sound_played = False
    previous_rects = []
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

        elapsed = pygame.time.get_ticks() - start
        progress = min(1.0, elapsed / duration)
        sprites = []
        if progress < 0.34:
            motion = math.sin(elapsed * 0.055) * 112
            for offset in range(5):
                x = WIDTH // 2 - CARD_W // 2 + motion * (1 if offset % 2 else -1)
                y = 260 + offset * 3 + math.sin(elapsed * 0.035 + offset) * 5
                sprites.append((x, y, None, True))
        else:
            if not spread_sound_played:
                play_sound("spread")
                spread_sound_played = True
            deal_progress = min(1.0, (progress - 0.34) / 0.66)
            targets = [250, 355, 460, 565]
            for index, target_x in enumerate(targets):
                card_progress = max(0.0, min(1.0, deal_progress * 4 - index))
                eased = card_progress * card_progress * (3 - 2 * card_progress)
                x = WIDTH // 2 - CARD_W // 2 + (target_x - (WIDTH // 2 - CARD_W // 2)) * eased
                y = 290 + (390 - 290) * eased - math.sin(math.pi * card_progress) * 28
                sprites.append((x, y, None, True))

        previous_rects = draw_animation_frame(background, previous_rects, sprites)
        if progress >= 1.0:
            return True
        CLOCK.tick(60)


def start_round(total_scores, round_number, mode="cpu", player_count=2):
    deck = new_deck()
    random.shuffle(deck)
    player_count = player_count if mode == "local" else 2
    players = [[deck.pop() for _ in range(4)] for _ in range(player_count)]
    discard = [deck.pop()]
    return {
        "deck": deck,
        "players": players,
        "human": players[0],
        "cpu": players[1],
        "discard": discard,
        "cpu_known": {0: card_value(players[1][0]), 2: card_value(players[1][2])},
        "human_seen": set(),
        "player_seen": [set() for _ in range(player_count)],
        "phase": "local_setup" if mode == "local" else "setup",
        "drawn": None,
        "message": "Player 1: peek at two of your cards." if mode == "local" else "Choose two of your cards to peek at.",
        "round_over": False,
        "caller": None,
        "scores": total_scores,
        "round_number": round_number,
        "setup_done": False,
        "cpu_peeked": False,
        "power_source": None,
        "mode": mode,
        "current_player": 0,
        "cpu_seen": set(),
        "player_count": player_count,
        "final_turns": None,
    }


def human_score(state):
    return sum(card_value(card) for card in state["human"])


def cpu_score(state):
    return sum(card_value(card) for card in state["cpu"])


def active_hand(state):
    return state["players"][state["current_player"]] if state["mode"] == "local" else state["human"]


def active_seen(state):
    return state["player_seen"][state["current_player"]] if state["mode"] == "local" else state["human_seen"]


def opponent_card_at(pos, state):
    if state["mode"] != "local":
        return None
    for row, player in enumerate(i for i in range(state["player_count"]) if i != state["current_player"]):
        for index in range(4):
            rect = pygame.Rect(145 + index * 55, 94 + row * 57, 43, 52)
            if rect.collidepoint(pos):
                return player, index
    return None


def draw_mini_card(surface, x, y, card=None, hidden=True):
    rect = pygame.Rect(x, y, 43, 52)
    pygame.draw.rect(surface, (12, 43, 38), rect.move(3, 4), border_radius=6)
    pygame.draw.rect(surface, (205, 198, 174), rect.move(0, 2), border_radius=5)
    fill = (26, 53, 125) if hidden else WHITE
    pygame.draw.rect(surface, fill, rect, border_radius=5)
    pygame.draw.rect(surface, (226, 222, 196), rect, 2, border_radius=5)
    pygame.draw.line(surface, (255, 255, 255), (x + 6, y + 4), (x + 36, y + 4), 1)
    if hidden:
        pygame.draw.line(surface, (178, 203, 229), (x + 9, y + 11), (x + 34, y + 41), 1)
        pygame.draw.line(surface, (178, 203, 229), (x + 34, y + 11), (x + 9, y + 41), 1)
    elif card:
        color = suit_color(card[1])
        mini_font = pygame.font.SysFont("arial", 15, bold=True)
        surface.blit(mini_font.render(rank_name(card[0]), True, color), (x + 4, y + 3))
        surface.blit(mini_font.render(suit_symbol(card[1]), True, color), (x + 4, y + 21))
    return rect


def finish_round(state):
    state["round_over"] = True
    if state["mode"] == "local":
        points = [sum(card_value(card) for card in hand) for hand in state["players"]]
        if state["caller"] is not None and points[state["caller"]] > min(points):
            points[state["caller"]] *= 2
        for i, value in enumerate(points):
            state["scores"][i] += value
        state["round_points"] = points
        winner = points.index(min(points))
        state["message"] = f"Player {winner + 1} wins the round!"
        return

    h_score = human_score(state)
    c_score = cpu_score(state)
    h_add, c_add = h_score, c_score
    if state["caller"] == "human" and h_score > c_score:
        h_add *= 2
    elif state["caller"] == "cpu" and c_score > h_score:
        c_add *= 2
    state["round_points"] = h_add
    state["cpu_round_points"] = c_add
    state["scores"][0] += h_add
    state["scores"][1] += c_add
    if h_score < c_score:
        state["message"] = f"You win the round! You: {h_score}   Computer: {c_score}"
    elif c_score < h_score:
        state["message"] = f"Computer wins the round. You: {h_score}   Computer: {c_score}"
    else:
        state["message"] = f"It's a tie! You: {h_score}   Computer: {c_score}"


def end_human_turn(state):
    state["drawn"] = None
    if state["mode"] == "local":
        if state["final_turns"] is not None:
            state["final_turns"] -= 1
            if state["final_turns"] <= 0:
                finish_round(state)
                return
        elif state["caller"] is not None:
            state["final_turns"] = state["player_count"] - 1
        state["current_player"] = (state["current_player"] + 1) % state["player_count"]
        state["phase"] = "local_handoff"
        state["message"] = f"Pass the device to Player {state['current_player'] + 1}. Click to continue."
        return

    state["phase"] = "cpu_turn"
    cpu_turn(state)
    if state["caller"] == "human":
        finish_round(state)
    else:
        state["phase"] = "human_pick"
        state["message"] = "Your turn: draw from the deck or take the discard."

def reveal_next_local_player(state):
    state["phase"] = "local_setup"
    state["message"] = f"Player {state['current_player'] + 1}: peek at two of your cards."


def begin_local_turn(state):
    state["phase"] = "human_pick"
    state["message"] = f"Player {state['current_player'] + 1}: draw from the deck or take the discard."


def cpu_turn(state):
    deck = state["deck"]
    if not deck:
        deck.extend(state["discard"][:-1])
        state["discard"] = state["discard"][-1:]
        random.shuffle(deck)
        play_sound("shuffle")
    top = state["discard"][-1]
    known_values = state["cpu_known"]
    known_worst = max(known_values, key=known_values.get) if known_values else None
    threshold = 4 if CPU_DIFFICULTY == "Casual" else 1 if CPU_DIFFICULTY == "Sharp" else 2
    if known_worst is not None and card_value(top) <= known_values[known_worst] - threshold:
        drawn = state["discard"].pop()
    else:
        drawn = deck.pop()
    play_sound("draw")

    candidates = list(known_values)
    target = max(candidates, key=lambda i: known_values[i]) if candidates else None
    if target is not None and card_value(drawn) <= known_values[target] - threshold:
        old = state["cpu"][target]
        state["cpu"][target] = drawn
        state["discard"].append(old)
        known_values[target] = card_value(drawn)
        discarded = old
    else:
        state["discard"].append(drawn)
        discarded = drawn

    play_sound("discard")
    rank = card_value(discarded)
    if rank in (7, 8):
        play_sound("peek")
        hidden = [i for i in range(4) if i not in known_values]
        if hidden:
            i = random.choice(hidden)
            known_values[i] = card_value(state["cpu"][i])
    elif rank in (9, 10):
        play_sound("peek")
        state["cpu_peeked"] = True
    elif rank in (11, 12):
        # The computer swaps only when its information suggests a clear improvement.
        if known_values:
            i = max(known_values, key=known_values.get)
            if known_values[i] >= 10:
                j = random.randrange(4)
                state["cpu"][i], state["human"][j] = state["human"][j], state["cpu"][i]
                play_sound("swap")
                known_values[i] = card_value(state["cpu"][i])
                state["human_seen"].discard(j)


def human_discard(state, card):
    state["discard"].append(card)
    play_sound("discard")
    rank = card_value(card)
    if rank in (7, 8):
        state["phase"] = "power_own"
        state["message"] = "Power: click one of your cards to peek at it."
    elif rank in (9, 10):
        state["phase"] = "power_cpu"
        target = "any opponent's" if state["mode"] == "local" else "a computer's"
        state["message"] = f"Power: click {target} card to peek at it."
    elif rank in (11, 12):
        state["phase"] = "power_swap_own"
        state["message"] = "Power: choose one of your cards to swap."
    else:
        end_human_turn(state)


def card_at(pos, xs, y):
    for i, x in enumerate(xs):
        if card_rect(x, y).collidepoint(pos):
            return i
    return None


def draw_game(state):
    SCREEN.fill(BG)
    pygame.draw.rect(SCREEN, BG_DARK, (0, 0, WIDTH, 72))
    text(SCREEN, "CABO", 28, 16, BIG, GOLD)
    text(SCREEN, f"Round {state['round_number']}", 174, 25, FONT)
    if state["mode"] == "local":
        score_text = "  ".join(f"P{i + 1}: {score}" for i, score in enumerate(state["scores"][:6]))
        text(SCREEN, f"Scores  {score_text}", 285, 28, SMALL)
    else:
        text(SCREEN, f"Score  You: {state['scores'][0]}   Computer: {state['scores'][1]}", 330, 25, FONT)
    draw_button(SCREEN, pygame.Rect(795, 13, 105, 44), "Menu", True, (74, 88, 82))

    if state["mode"] == "local":
        active_name = f"PLAYER {state['current_player'] + 1}"
        for row, player in enumerate(i for i in range(state["player_count"]) if i != state["current_player"]):
            y = 94 + row * 57
            text(SCREEN, f"P{player + 1}", 38, y + 16, SMALL, GOLD)
            for i in range(4):
                show = state["round_over"] or (
                    state["phase"] == "power_cpu_seen"
                    and state.get("peek_player") == player
                    and state.get("peek_index") == i
                )
                draw_mini_card(SCREEN, 145 + i * 55, y, state["players"][player][i] if show else None, not show)
        text(SCREEN, f"{active_name} CARDS", 40, 454, FONT, GOLD)
        for i, x in enumerate(HUMAN_X):
            show = state["round_over"] or (state["phase"] != "local_handoff" and i in active_seen(state))
            draw_card(SCREEN, x, CARD_Y_HUMAN, active_hand(state)[i] if show else None, hidden=not show)
    else:
        text(SCREEN, "COMPUTER", 40, 112, FONT, GOLD)
        for i, x in enumerate(CPU_X):
            known = state["round_over"] or (state["phase"] in ("power_cpu", "power_cpu_seen") and state.get("peek_index") == i)
            draw_card(SCREEN, x, CARD_Y_CPU, state["cpu"][i] if known else None, hidden=not known)

        text(SCREEN, "YOUR CARDS", 40, 454, FONT, GOLD)
        for i, x in enumerate(HUMAN_X):
            show = state["round_over"] or i in state["human_seen"]
            draw_card(SCREEN, x, CARD_Y_HUMAN, state["human"][i] if show else None, hidden=not show)

    text(SCREEN, "DECK", 635, 178, SMALL, WHITE, True)
    draw_card(SCREEN, 590, 195, hidden=True)
    text(SCREEN, f"{len(state['deck'])} cards", 636, 333, SMALL, WHITE, True)
    text(SCREEN, "DISCARD", 790, 178, SMALL, WHITE, True)
    draw_card(SCREEN, 745, 195, state["discard"][-1] if state["discard"] else None)

    pygame.draw.rect(SCREEN, PANEL, (25, 382, 870, 55), border_radius=8)
    text(SCREEN, state["message"], 460, 409, FONT, WHITE, True)

    if state["drawn"]:
        text(SCREEN, "DRAWN", 700, 375, SMALL, GOLD, True)
        draw_card(SCREEN, 654, 395, state["drawn"])

    if state["phase"] in ("setup", "local_setup"):
        seen_count = len(active_seen(state)) if state["mode"] == "local" else len(state["human_seen"])
        text(SCREEN, f"Peeked: {seen_count}/2", 700, 490, FONT, GOLD, True)
        if seen_count >= 2:
            label = "Continue" if state["mode"] == "local" else "Start game"
            draw_button(SCREEN, pygame.Rect(650, 535, 190, 48), label, True, (47, 133, 83))
    elif not state["round_over"]:
        if state["phase"] == "local_handoff":
            draw_button(SCREEN, pygame.Rect(650, 550, 190, 48), "Continue", True, (47, 133, 83))
        elif state["phase"] == "human_pick":
            draw_button(SCREEN, pygame.Rect(590, 375, 135, 48), "Draw deck")
            draw_button(SCREEN, pygame.Rect(740, 375, 150, 48), "Take discard")
            can_call = state["mode"] != "local" or state["caller"] is None
            draw_button(SCREEN, pygame.Rect(650, 550, 190, 48), "Call Cabo" if can_call else "Final turns", can_call, (164, 67, 54))
        elif state["phase"] == "human_drawn":
            draw_button(SCREEN, pygame.Rect(650, 550, 190, 48), "Discard drawn", True, (164, 67, 54))
            text(SCREEN, "Or click one of your cards to replace it.", 745, 620, SMALL, WHITE, True)
        elif state["phase"] == "power_cpu":
            label = "Click an opponent card" if state["mode"] == "local" else "Click a computer card"
            text(SCREEN, label, 745, 560, SMALL, GOLD, True)
        elif state["phase"] in ("power_own", "power_swap_own"):
            text(SCREEN, "Click one of your cards", 745, 560, SMALL, GOLD, True)
        elif state["phase"] == "power_swap_cpu":
            label = "Now click an opponent card" if state["mode"] == "local" else "Now click a computer card"
            text(SCREEN, label, 745, 560, SMALL, GOLD, True)
    else:
        draw_button(SCREEN, pygame.Rect(650, 550, 190, 48), "Next round", True, (47, 133, 83))
        if state["mode"] == "local":
            point_text = "Round points â€” " + "  ".join(
                f"P{i + 1}: {value}" for i, value in enumerate(state.get("round_points", []))
            )
        else:
            point_text = f"Round points â€” You: {state.get('round_points', human_score(state))}   Computer: {state.get('cpu_round_points', cpu_score(state))}"
        text(SCREEN, point_text, 460, 648, SMALL, GOLD, True)

    pygame.display.flip()


def draw_menu(settings_open, state, difficulty, player_select=False):
    SCREEN.fill(BG)
    pygame.draw.rect(SCREEN, BG_DARK, (0, 0, WIDTH, 110))
    text(SCREEN, "CABO", WIDTH // 2, 48, BIG, GOLD, True)
    if player_select:
        text(SCREEN, "OFFLINE MULTIPLAYER", WIDTH // 2, 170, BIG, WHITE, True)
        text(SCREEN, "Choose the number of players", WIDTH // 2, 235, FONT, WHITE, True)
        for count in range(2, 7):
            col = (count - 2) % 3
            row = (count - 2) // 3
            rect = pygame.Rect(235 + col * 155, 290 + row * 85, 125, 58)
            draw_button(SCREEN, rect, f"{count} Players", True, (47, 133, 83))
        draw_button(SCREEN, pygame.Rect(365, 475, 190, 50), "Back", True, (74, 88, 82))
        text(SCREEN, "Pass-and-play on this device", WIDTH // 2, 555, SMALL, WHITE, True)
    elif settings_open:
        text(SCREEN, "SETTINGS", WIDTH // 2, 170, BIG, WHITE, True)
        text(SCREEN, "Computer difficulty", WIDTH // 2, 255, FONT, WHITE, True)
        draw_button(SCREEN, pygame.Rect(325, 295, 270, 54), f"{difficulty}  (change)", True)
        draw_button(SCREEN, pygame.Rect(365, 390, 190, 50), "Back", True, (47, 133, 83))
        text(SCREEN, "Casual, Balanced, and Sharp change how the computer chooses cards.", WIDTH // 2, 480, SMALL, WHITE, True)
    else:
        text(SCREEN, "Choose how you want to play", WIDTH // 2, 165, FONT, WHITE, True)
        has_game = state is not None
        draw_button(SCREEN, pygame.Rect(300, 215, 320, 55), "Continue game", has_game, (47, 133, 83))
        draw_button(SCREEN, pygame.Rect(300, 285, 320, 55), "New game vs Computer", True)
        draw_button(SCREEN, pygame.Rect(300, 355, 320, 55), "Offline multiplayer", True, (47, 133, 83))
        draw_button(SCREEN, pygame.Rect(300, 425, 320, 55), "Settings", True)
        text(SCREEN, "Offline multiplayer supports 2â€“6 players on this device.", WIDTH // 2, 535, SMALL, WHITE, True)
    pygame.display.flip()


def main():
    global CPU_DIFFICULTY
    totals = [0, 0]
    round_number = 1
    state = None
    menu_open = True
    settings_open = False
    player_select = False
    difficulty_options = ("Casual", "Balanced", "Sharp")
    running = True
    menu_button = pygame.Rect(795, 13, 105, 44)
    setup_button = pygame.Rect(650, 535, 190, 48)
    action_button = pygame.Rect(650, 550, 190, 48)

    while running:
        if menu_open:
            draw_menu(settings_open, state, CPU_DIFFICULTY, player_select)
        else:
            draw_game(state)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not menu_open:
                menu_open = True
                settings_open = False
                player_select = False
                continue

            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue
            pos = event.pos

            if menu_open:
                if player_select:
                    if pygame.Rect(365, 475, 190, 50).collidepoint(pos):
                        player_select = False
                    else:
                        for count in range(2, 7):
                            col = (count - 2) % 3
                            row = (count - 2) // 3
                            rect = pygame.Rect(235 + col * 155, 290 + row * 85, 125, 58)
                            if rect.collidepoint(pos):
                                totals = [0] * count
                                round_number = 1
                                if not animate_new_game():
                                    running = False
                                    continue
                                state = start_round(totals, round_number, "local", count)
                                menu_open = False
                                player_select = False
                                break
                elif settings_open:
                    if pygame.Rect(325, 295, 270, 54).collidepoint(pos):
                        index = difficulty_options.index(CPU_DIFFICULTY)
                        CPU_DIFFICULTY = difficulty_options[(index + 1) % len(difficulty_options)]
                    elif pygame.Rect(365, 390, 190, 50).collidepoint(pos):
                        settings_open = False
                elif pygame.Rect(300, 215, 320, 55).collidepoint(pos):
                    if state is not None:
                        menu_open = False
                elif pygame.Rect(300, 285, 320, 55).collidepoint(pos):
                    if not animate_new_game():
                        running = False
                        continue
                    totals = [0, 0]
                    round_number = 1
                    state = start_round(totals, round_number, "cpu")
                    menu_open = False
                elif pygame.Rect(300, 355, 320, 55).collidepoint(pos):
                    player_select = True
                elif pygame.Rect(300, 425, 320, 55).collidepoint(pos):
                    settings_open = True
                continue

            if menu_button.collidepoint(pos):
                menu_open = True
                settings_open = False
                player_select = False
                continue

            if state["round_over"]:
                if action_button.collidepoint(pos):
                    round_number += 1
                    state = start_round(totals, round_number, state["mode"], state["player_count"])
                continue

            phase = state["phase"]
            if phase == "local_handoff":
                if action_button.collidepoint(pos):
                    if state.pop("handoff_setup", False):
                        reveal_next_local_player(state)
                    else:
                        begin_local_turn(state)
                continue

            if phase in ("setup", "local_setup"):
                seen = active_seen(state) if state["mode"] == "local" else state["human_seen"]
                if len(seen) >= 2 and setup_button.collidepoint(pos):
                    if state["mode"] == "local":
                        if state["current_player"] < state["player_count"] - 1:
                            state["current_player"] += 1
                            state["handoff_setup"] = True
                            state["phase"] = "local_handoff"
                            state["message"] = f"Pass the device to Player {state['current_player'] + 1}. Click Continue when ready."
                        else:
                            state["current_player"] = 0
                            state["handoff_setup"] = False
                            state["phase"] = "local_handoff"
                            state["message"] = "Setup complete. Pass the device to Player 1 and continue."
                    else:
                        state["phase"] = "human_pick"
                        state["message"] = "Your turn: draw from the deck or take the discard."
                else:
                    index = card_at(pos, HUMAN_X, CARD_Y_HUMAN)
                    if index is not None and index not in seen and len(seen) < 2:
                        seen.add(index)
                        play_sound("peek")
                        if state["mode"] == "local":
                            state["message"] = f"Player {state['current_player'] + 1}: remember those cards; peek at one more."
                        else:
                            state["message"] = "Remember those cards, then peek at one more."
                continue

            if phase == "human_pick":
                if pygame.Rect(590, 375, 135, 48).collidepoint(pos):
                    if not state["deck"]:
                        state["deck"].extend(state["discard"][:-1])
                        state["discard"] = state["discard"][-1:]
                        random.shuffle(state["deck"])
                        play_sound("shuffle")
                    drawn_card = state["deck"][-1]
                    animate_card_transfer(drawn_card, (590, 195), (654, 395), hidden=True)
                    state["drawn"] = state["deck"].pop()
                    play_sound("draw")
                    state["phase"] = "human_drawn"
                    state["message"] = "Choose a card to replace, or discard the drawn card."
                elif pygame.Rect(740, 375, 150, 48).collidepoint(pos) and state["discard"]:
                    drawn_card = state["discard"][-1]
                    animate_card_transfer(drawn_card, (745, 195), (654, 395))
                    state["drawn"] = state["discard"].pop()
                    play_sound("draw")
                    state["phase"] = "human_drawn"
                    state["message"] = "Choose one of your cards to replace with the discard."
                elif action_button.collidepoint(pos) and not (state["mode"] == "local" and state["caller"] is not None):
                    play_sound("cabo")
                    state["caller"] = state["current_player"] if state["mode"] == "local" else "human"
                    name = f"Player {state['current_player'] + 1}" if state["mode"] == "local" else "You"
                    final_message = "The other players each get one final turn." if state["mode"] == "local" else "The computer gets one final turn."
                    state["message"] = f"{name} called Cabo! {final_message}"
                    end_human_turn(state)
                continue

            if phase == "human_drawn":
                if action_button.collidepoint(pos) and state["drawn"] is not None:
                    card = state["drawn"]
                    state["drawn"] = None
                    human_discard(state, card)
                else:
                    index = card_at(pos, HUMAN_X, CARD_Y_HUMAN)
                    if index is not None:
                        hand = active_hand(state)
                        seen = active_seen(state)
                        old = hand[index]
                        hand[index] = state["drawn"]
                        seen.add(index)
                        state["drawn"] = None
                        human_discard(state, old)
                continue

            if phase == "power_own":
                index = card_at(pos, HUMAN_X, CARD_Y_HUMAN)
                if index is not None:
                    hand = active_hand(state)
                    active_seen(state).add(index)
                    play_sound("peek")
                    state["message"] = f"You saw {rank_name(card_value(hand[index]))}{suit_symbol(hand[index][1])}."
                    end_human_turn(state)
                continue

            if phase == "power_cpu":
                if state["mode"] == "local":
                    target = opponent_card_at(pos, state)
                    if target is not None:
                        player, index = target
                        state["peek_player"] = player
                        state["peek_index"] = index
                        card = state["players"][player][index]
                        play_sound("peek")
                        state["message"] = f"Player {player + 1} card: {rank_name(card_value(card))}{suit_symbol(card[1])}. Click to continue."
                        state["phase"] = "power_cpu_seen"
                else:
                    index = card_at(pos, CPU_X, CARD_Y_CPU)
                    if index is not None:
                        state["peek_index"] = index
                        card = state["cpu"][index]
                        play_sound("peek")
                        state["message"] = f"Computer card: {rank_name(card_value(card))}{suit_symbol(card[1])}. Click to continue."
                        state["phase"] = "power_cpu_seen"
                continue

            if phase == "power_cpu_seen":
                state.pop("peek_index", None)
                state.pop("peek_player", None)
                if state["mode"] == "local":
                    end_human_turn(state)
                else:
                    state["phase"] = "human_pick"
                    state["message"] = "Your turn: draw from the deck or take the discard."
                continue

            if phase == "power_swap_own":
                index = card_at(pos, HUMAN_X, CARD_Y_HUMAN)
                if index is not None:
                    state["swap_human_index"] = index
                    state["phase"] = "power_swap_cpu"
                    state["message"] = "Choose any opponent card to swap with." if state["mode"] == "local" else "Now choose a computer card to swap with."
                continue

            if phase == "power_swap_cpu":
                if state["mode"] == "local":
                    target = opponent_card_at(pos, state)
                    if target is not None:
                        player, index = target
                        own = state["swap_human_index"]
                        hand = active_hand(state)
                        opponent = state["players"][player]
                        row = list(i for i in range(state["player_count"]) if i != state["current_player"]).index(player)
                        opponent_pos = (145 + index * 55, 94 + row * 57)
                        own_pos = (HUMAN_X[own], CARD_Y_HUMAN)
                        animate_card_exchange(
                            hand[own], own_pos, opponent_pos,
                            opponent[index], opponent_pos, own_pos,
                        )
                        hand[own], opponent[index] = opponent[index], hand[own]
                        play_sound("swap")
                        active_seen(state).discard(own)
                        state["player_seen"][player].discard(index)
                        end_human_turn(state)
                else:
                    index = card_at(pos, CPU_X, CARD_Y_CPU)
                    if index is not None:
                        own = state["swap_human_index"]
                        hand = active_hand(state)
                        own_pos = (HUMAN_X[own], CARD_Y_HUMAN)
                        cpu_pos = (CPU_X[index], CARD_Y_CPU)
                        animate_card_exchange(
                            hand[own], own_pos, cpu_pos,
                            state["cpu"][index], cpu_pos, own_pos,
                        )
                        hand[own], state["cpu"][index] = state["cpu"][index], hand[own]
                        play_sound("swap")
                        active_seen(state).discard(own)
                        state["cpu_known"].pop(index, None)
                        end_human_turn(state)

        CLOCK.tick(30)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
