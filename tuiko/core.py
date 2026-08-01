
import os
import re
import shutil
import sys

__version__ = "0.1.1"


def esc(*codes):

  return f"\x1b[{';'.join(map(str, codes))}m"

RESET = "\x1b[0m"
BOLD, DIM = 1, 2


class palette:


  black, red, green, yellow, blue, magenta, cyan, white = range(30, 38)
  gray, bright_cyan, bright_green, bright_yellow = 90, 96, 92, 93

  dark_cyan, mint, gold, sky = 24, 114, 220, 117


class theme:

  accent = 141
  accent_bright = 213
  text = 255
  muted = 245
  faint = 239
  success = 114
  highlight = 226
  select_fg = 213
  key_bg = 237
  key_fg = 255
  grad = (57, 63, 99, 135, 141, 177, 213, 219)

  border = 141
  select_bg = 54
  dim_bg = 236
  field_bg = 235


class ui:
  banner = "✦ Tuiko"
  star = "✦"
  prompt_mark = "›"
  cursor = "█"
  pointer = "▐"
  checked = "[✓]"
  unchecked = "[ ]"
  bar_fill = "█"
  bar_empty = "░"
  tick = "✓"
  hint_mark = "·"
  rule = "─"
  box_border = "╭─╮│╰─╯"
  spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
  working = "Bekerja..."
  selected_n = "dipilih"
  jump_to = "→ Lompat ke:"
  pct = "%"
  hint_select = "[↑/↓] Gerak · [ENTER] Pilih · [ESC] Batal"
  hint_multiselect = "[↑/↓] Gerak · [SPACE] Tandai · [ENTER] Lanjut · [ESC] Batal"
  search_mark = "⌕"
  search_ph = "Ketik untuk cari…"
  search_n = "cocok"


def style(text, *codes):


  parts = []
  for c in codes:
    if isinstance(c, int):
      parts.append(f"\x1b[38;5;{c}m" if c >= 100 else f"\x1b[{c}m")
    else:
      parts.append(c)
  return f"{''.join(parts)}{text}{RESET}"

def bg(code, text):

  return f"\x1b[48;5;{code}m{text}{RESET}"

def grad(text, colors, *, bold=True):


  if not text:
    return ""
  n = len(colors)
  if n == 1:
    return style(text, 1 if bold else 0, colors[0])
  parts = []
  span = max(len(text) - 1, 1)
  for i, ch in enumerate(text):
    idx = (i * (n - 1)) // span
    parts.append(f"\x1b[38;5;{colors[idx]}m{ch}")
  return ("\x1b[1m" if bold else "") + "".join(parts) + RESET

def sep(width, *, color=None):

  return style("─" * max(width, 1), color or theme.faint)

_ANSI_RE = re.compile(r"\x1b(?:\[[0-9;?]*[A-Za-z]|\][^\x07]*(\x07|\x1b\\)|[()][A-Z0-9])")

def strip_ansi(text):

  return _ANSI_RE.sub("", text)

def term_width():

  return shutil.get_terminal_size((80, 24)).columns

def term_height():

  return shutil.get_terminal_size((80, 24)).lines

def truncate(text, width):

  if len(text) <= width:
    return text
  return text[: max(0, width - 1)] + "…"


CLEAR = "\x1b[2J"
HOME = "\x1b[H"
HIDE_CURSOR, SHOW_CURSOR = "\x1b[?25l", "\x1b[?25h"
ALT_IN, ALT_OUT = "\x1b[?1049h", "\x1b[?1049l"

def render_frame(lines, out=None):


  out = out or sys.stdout
  out.write(CLEAR + HOME + "\n".join(lines) + "\n")
  out.flush()

def enable_ansi():

  if os.name != "nt":
    return
  try:
    import ctypes
    k32 = ctypes.windll.kernel32
    h = k32.GetStdHandle(-11)
    mode = ctypes.c_uint32()
    if k32.GetConsoleMode(h, ctypes.byref(mode)):
      k32.SetConsoleMode(h, mode.value | 0x0004)
  except Exception:
    pass
