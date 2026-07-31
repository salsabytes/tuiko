

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

def _normalize_char(ch):

  return _CHAR_MAP.get(ch, ch)

_WIN_ARROWS = {
  "H": "up", "P": "down", "K": "left", "M": "right",
  "I": "pgup", "Q": "pgdn", "G": "home", "O": "end",
}

def _parse_win(ch, ch2):

  if ch in ("\xe0", "\x00"):
    return _WIN_ARROWS.get(ch2, ch2)
  return ch

_POSIX_SEQ = {
  b"\x1b": "escape",
  b"\x1b[A": "up", b"\x1b[B": "down", b"\x1b[C": "right", b"\x1b[D": "left",
  b"\x1b[H": "home", b"\x1b[F": "end",
  b"\x1b[5~": "pgup", b"\x1b[6~": "pgdn", b"\x1b[3~": "delete",
}

def _parse_posix(seq):

  return _POSIX_SEQ.get(seq, seq.decode(errors="replace"))


def read_key():

  if os.name == "nt":
    import msvcrt
    ch = msvcrt.getwch()
    if ch in ("\xe0", "\x00"):
      return _parse_win(ch, msvcrt.getwch())
    return _normalize_char(ch)
  return _read_posix()

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
