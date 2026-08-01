

import os
import sys

_OLD_ATTRS = None


def enable_raw():


  global _OLD_ATTRS
  if os.name == "nt":
    return
  import termios
  import tty
  fd = sys.stdin.fileno()
  _OLD_ATTRS = termios.tcgetattr(fd)
  tty.setcbreak(fd)

def disable_raw():

  global _OLD_ATTRS
  if os.name == "nt" or _OLD_ATTRS is None:
    return
  import termios
  termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _OLD_ATTRS)
  _OLD_ATTRS = None


_CHAR_MAP = {
  "\r": "enter", "\n": "enter",
  "\b": "backspace", "\x7f": "backspace",
  "\t": "tab", " ": "space", "\x03": "ctrl-c",
}

# ctrl-a .. ctrl-z (ASCII control chars 0x01-0x1a)
for _i in range(1, 27):
  _CHAR_MAP.setdefault(chr(_i), f"ctrl-{chr(96 + _i)}")

def _normalize_char(ch):

  return _CHAR_MAP.get(ch, ch)

_WIN_ARROWS = {
  "H": "up", "P": "down", "K": "left", "M": "right",
  "I": "pgup", "Q": "pgdn", "G": "home", "O": "end",
}

def _parse_win(ch, ch2):

  if ch == "\xe0":
    # extended keys (arrows, page keys) — modern consoles send these with \xe0
    return _WIN_ARROWS.get(ch2, ch2)
  if ch == "\x00":
    # Alt+letter arrives as \x00 + letter; legacy arrows also used \x00 but
    # modern consoles use \xe0, so prefer Alt for letters here
    if ch2.isalpha():
      return f"alt-{ch2.lower()}"
    return _WIN_ARROWS.get(ch2, ch2)
  return ch

_POSIX_SEQ = {
  b"\x1b": "escape",
  b"\x1b[A": "up", b"\x1b[B": "down", b"\x1b[C": "right", b"\x1b[D": "left",
  b"\x1b[H": "home", b"\x1b[F": "end",
  b"\x1b[5~": "pgup", b"\x1b[6~": "pgdn", b"\x1b[3~": "delete",
}

def _parse_posix(seq):

  if len(seq) == 2 and seq.startswith(b"\x1b"):
    ch = seq[1:2].decode(errors="replace")
    if ch.isalnum():
      return f"alt-{ch.lower()}"
  return _POSIX_SEQ.get(seq, seq.decode(errors="replace"))


def read_key():

  if os.name == "nt":
    import msvcrt
    ch = msvcrt.getwch()
    if ch in ("\xe0", "\x00"):
      return _parse_win(ch, msvcrt.getwch())
    if ch == "\x1b":
      return _read_win_esc()
    return _normalize_char(ch)
  return _read_posix()

def _read_win_esc():

  """Parse ESC-prefixed sequences on Windows (VT mode / modern terminals)."""
  import msvcrt
  import time
  time.sleep(0.02)  # let the rest of the sequence arrive
  if not msvcrt.kbhit():
    return "escape"
  b = b"\x1b" + msvcrt.getwch().encode("latin-1", "replace")
  if b == b"\x1b[":
    while msvcrt.kbhit():
      c = msvcrt.getwch()
      b += c.encode("latin-1", "replace")
      if c.isalpha() or c == "~":
        break
  return _parse_posix(b)

def _read_posix():


  import select
  fd = sys.stdin.fileno()
  b = os.read(fd, 1)
  if b == b"\x1b":
    r, _, _ = select.select([fd], [], [], 0.05)
    if not r:
      return "escape"
    b += os.read(fd, 1)
    if b == b"\x1b[":
      b += os.read(fd, 1)
      if b in (b"\x1b[5", b"\x1b[6", b"\x1b[3"):
        b += os.read(fd, 1)
    return _parse_posix(b)
  return _normalize_char(b.decode(errors="replace"))
