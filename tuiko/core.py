
import os
import re
import shutil
import sys
import unicodedata

__version__ = "0.1.3"

RESET = "\x1b[0m"


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
  rule = "─"
  box_border = "╭─╮│╰─╯"
  spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
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
  return f"{''.join(parts)}{text}{RESET}"

def bg(code, text):

  return f"\x1b[48;5;{code}m{text}{RESET}"

def grad(text, colors):


  if not text:
    return ""
  n = len(colors)
  if n == 1:
    return style(text, 1, colors[0])
  parts = []
  span = max(len(text) - 1, 1)
  for i, ch in enumerate(text):
    idx = (i * (n - 1)) // span
    parts.append(f"\x1b[38;5;{colors[idx]}m{ch}")
  return "\x1b[1m" + "".join(parts) + RESET

def sep(width, *, color=None):

  return style("─" * max(width, 1), color or theme.faint)

_ANSI_RE = re.compile(r"\x1b(?:\[[0-9;?]*[A-Za-z]|\][^\x07]*(\x07|\x1b\\)|[()][A-Z0-9])")

def strip_ansi(text):

  return _ANSI_RE.sub("", text)

def term_width():

  return shutil.get_terminal_size((80, 24)).columns

def term_height():

  return shutil.get_terminal_size((80, 24)).lines

# Display columns of text — ANSI-safe; wide (CJK/emoji) chars count 2.
def disp_width(text):

  text = _ANSI_RE.sub("", text)
  w = 0
  for ch in text:
    if unicodedata.combining(ch):
      continue
    w += 2 if unicodedata.east_asian_width(ch) in "WF" else 1
  return w

# Truncate to fit `width` display columns (wide-aware), end with ….
def truncate(text, width):

  if disp_width(text) <= width:
    return text
  out = []
  used = 0
  for ch in text:
    cw = disp_width(ch)
    if used + cw > max(width - 1, 0):
      break
    out.append(ch)
    used += cw
  return "".join(out) + "…"


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
    pass  # nosec B110: best-effort VT enable; ignore if not a Windows console
