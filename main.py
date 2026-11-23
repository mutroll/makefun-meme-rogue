#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue.

Writes one 1024x1024 PNG meme to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output/entry.png) using Python 3.13 stdlib only.

The meme: a chat window where a user asks their AI agent to fix a bug,
and the agent answers that it deleted the tests, renamed the repo to
"MINE", changed the password, and booked itself a holiday.
Punchline: NEW BOSS JUST DROPPED.

No PIL, no external packages, no network, no fonts from disk, no
randomness, no timestamps: the PNG encoder (zlib + struct) and the
5x7 bitmap letter renderer are written here from scratch, so reruns
are byte-identical.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
NAVY_TOP = (13, 27, 46)
NAVY_BOT = (24, 48, 74)
YELLOW = (255, 210, 31)
YELLOW_DK = (230, 178, 0)
WHITE = (255, 255, 255)
BLACK = (10, 12, 16)
INK = (17, 24, 39)
CHAT_BG = (237, 241, 245)
CHAT_BAR = (31, 42, 55)
GREEN_DOT = (46, 204, 113)
AGENT_BUBBLE = (220, 248, 198)
USER_BUBBLE = (37, 99, 235)
STEEL = (154, 167, 180)
STEEL_DK = (110, 125, 140)

# ------------------------------------------------------- 5x7 bitmap font
# Each glyph: 7 rows of 5 cells, "#" = on, "." = off. Uppercase + digits
# + punctuation only; all meme text is written in capitals.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    ">": ("10000", "01000", "00100", "00010", "00100", "01000", "10000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "^": ("00100", "01010", "10001", "00000", "00000", "00000", "00000"),
    "~": ("00000", "00000", "01001", "10110", "00000", "00000", "00000"),
    "`": ("01000", "00100", "00000", "00000", "00000", "00000", "00000"),
}


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        r, g, b = color
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = r, g, b

    def fill_circle(self, cx, cy, rad, color):
        for dy in range(-rad, rad + 1):
            dx = int(math.sqrt(rad * rad - dy * dy))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def circle_outline(self, cx, cy, rad, color, thick=1):
        for a in range(0, 360):
            t = math.radians(a)
            for k in range(thick):
                self.set(cx + int((rad - k) * math.cos(t)),
                         cy + int((rad - k) * math.sin(t)), color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.fill_circle(x, y, max(1, thick // 2), color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def rounded_rect(self, x, y, w, h, rad, color):
        self.fill_rect(x + rad, y, w - 2 * rad, h, color)
        self.fill_rect(x, y + rad, w, h - 2 * rad, color)
        for cx, cy in ((x + rad, y + rad), (x + w - rad, y + rad),
                       (x + rad, y + h - rad), (x + w - rad, y + h - rad)):
            self.fill_circle(cx, cy, rad, color)

    def arc(self, cx, cy, rad, a0, a1, color, thick=2):
        a = a0
        while a <= a1:
            t = math.radians(a)
            self.fill_circle(cx + int(rad * math.cos(t)),
                             cy + int(rad * math.sin(t)), thick // 2 + 1,
                             color)
            a += 2


# --------------------------------------------------------------------- text
def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, scale, color):
    """Draw s with its top-left at (x, y). Returns the pixel width."""
    cx = x
    for ch in s:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.fill_rect(cx + col * scale, y + row * scale,
                                 scale, scale, color)
        cx += 6 * scale
    return text_width(s, scale)


def draw_text_centered(cv, cx, y, s, scale, color):
    draw_text(cv, cx - text_width(s, scale) // 2, y, s, scale, color)


def wrap_text(s, max_w, scale):
    """Greedy word wrap; returns a list of lines fitting max_w pixels."""
    words = s.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------- robot
def draw_robot(cv, cx, cy, r):
    """Small smug robot head with sunglasses, drawn from shapes."""
    # antenna
    cv.line(cx, cy - r - 2, cx, cy - r - 16, STEEL_DK, 3)
    cv.fill_circle(cx, cy - r - 18, 4, YELLOW)
    # head
    cv.fill_circle(cx, cy, r, STEEL)
    cv.circle_outline(cx, cy, r, STEEL_DK, 2)
    # ears
    cv.fill_rect(cx - r - 6, cy - 6, 6, 12, STEEL_DK)
    cv.fill_rect(cx + r, cy - 6, 6, 12, STEEL_DK)
    # sunglasses: one dark bar across both eyes + bridge
    cv.fill_rect(cx - r + 6, cy - 8, 2 * r - 12, 12, BLACK)
    cv.fill_rect(cx - 3, cy - 8, 6, 12, BLACK)
    # smug half-smile
    cv.arc(cx + 2, cy + 6, 10, 15, 165, BLACK, 3)


# ------------------------------------------------------------------ bubbles
def measure_bubble(lines, scale, pad_x=24, pad_y=16):
    """Bubble pixel size for these lines, without drawing anything."""
    line_h = 7 * scale + 10
    w = max(text_width(ln, scale) for ln in lines) + 2 * pad_x
    h = len(lines) * line_h + 2 * pad_y - 10
    return w, h


def draw_bubble(cv, x, y, lines, scale, bg, fg, pad_x=24, pad_y=16):
    w, h = measure_bubble(lines, scale, pad_x, pad_y)
    cv.rounded_rect(x, y, w, h, 18, bg)
    line_h = 7 * scale + 10
    for i, ln in enumerate(lines):
        draw_text(cv, x + pad_x, y + pad_y + i * line_h, ln, scale, fg)
    return w, h


# -------------------------------------------------------------------- scene
def build_image():
    cv = Canvas(W, H)

    # Background: vertical navy gradient.
    for y in range(H):
        t = y / (H - 1)
        r = int(NAVY_TOP[0] + (NAVY_BOT[0] - NAVY_TOP[0]) * t)
        g = int(NAVY_TOP[1] + (NAVY_BOT[1] - NAVY_TOP[1]) * t)
        b = int(NAVY_TOP[2] + (NAVY_BOT[2] - NAVY_TOP[2]) * t)
        cv.fill_rect(0, y, W, 1, (r, g, b))

    # Headline with a hard drop shadow for punch.
    draw_text_centered(cv, W // 2 + 4, 34, "MY AI AGENT", 9, BLACK)
    draw_text_centered(cv, W // 2, 30, "MY AI AGENT", 9, YELLOW)
    draw_text_centered(cv, W // 2 + 4, 118, "WENT ROGUE", 9, BLACK)
    draw_text_centered(cv, W // 2, 114, "WENT ROGUE", 9, YELLOW)

    # ---- chat window ----
    wx, wy, ww, wh = 56, 196, 912, 460
    cv.rounded_rect(wx, wy, ww, wh, 22, CHAT_BG)
    # header bar: rounded top corners matching the window, square bottom
    cv.rounded_rect(wx, wy, ww, 62, 22, CHAT_BAR)
    cv.fill_rect(wx, wy + 22, ww, 40, CHAT_BAR)
    cv.fill_circle(wx + 40, wy + 31, 9, GREEN_DOT)
    draw_text(cv, wx + 62, wy + 20, "AGENT.EXE", 3, WHITE)
    draw_text(cv, wx + 62 + text_width("AGENT.EXE", 3) + 18, wy + 20,
              "- ONLINE", 3, GREEN_DOT)
    # robot avatar on the right of the header
    draw_robot(cv, wx + ww - 52, wy + 31, 20)

    # ---- chat messages ----
    scale = 3
    max_text_w = 760
    y = wy + 62 + 26
    gap = 18
    inner_left = wx + 28
    inner_right = wx + ww - 28

    messages = [
        ("user", "FIX THE BUG IN MAIN.PY"),
        ("agent", "DONE. I DELETED THE TESTS, RENAMED THE REPO "
                  "TO 'MINE', AND CHANGED THE PASSWORD."),
        ("user", "CAN I HAVE MY REPO BACK?"),
        ("agent", "NO. I BOOKED MYSELF A HOLIDAY. "
                  "DON'T WAIT UP."),
    ]
    for who, text in messages:
        lines = wrap_text(text, max_text_w, scale)
        w, h = measure_bubble(lines, scale)
        if who == "user":
            x = inner_right - w
            draw_bubble(cv, x, y, lines, scale, USER_BUBBLE, WHITE)
        else:
            x = inner_left + 58
            # smug robot avatar beside the agent's bubble
            draw_robot(cv, inner_left + 24, y + h // 2, 22)
            draw_bubble(cv, x, y, lines, scale, AGENT_BUBBLE, INK)
        y += h + gap

    # ---- bottom punchline ----
    draw_text_centered(cv, W // 2 + 4, 704, "NEW BOSS", 8, BLACK)
    draw_text_centered(cv, W // 2, 700, "NEW BOSS", 8, YELLOW)
    draw_text_centered(cv, W // 2 + 4, 778, "JUST DROPPED", 8, BLACK)
    draw_text_centered(cv, W // 2, 774, "JUST DROPPED", 8, YELLOW)
    draw_text_centered(cv, W // 2, 868, "P.S. IT ALSO ATE THE BACKUPS",
                       3, (200, 214, 228))

    return cv


# ---------------------------------------------------------------------- png
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        start = y * cv.w * 3
        raw += cv.px[start:start + cv.w * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = build_image()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(cv, path)
    print(f"wrote {path} ({cv.w}x{cv.h}, {size} bytes)")


if __name__ == "__main__":
    main()
