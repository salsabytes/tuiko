# keydebug — inspect the raw keys your terminal sends.
#
# Usage:
#   python keydebug.py          # raw mode: raw bytes from msvcrt/termios
#   python keydebug.py --tuiko  # tuiko mode: read_key() output like indonime uses
#
# Press the key you want to inspect (alt+p, alt+q, ctrl+p, ctrl+q, arrow, escape).
# Press 'q' (no modifier) to quit.
import os
import sys


def _ord(c):
  return hex(ord(c))


def raw_loop_win():
  import msvcrt
  import time
  print("RAW MODE (Windows msvcrt) — tekan tombol, 'q' untuk keluar")
  print("fokus: alt+p · alt+q · ctrl+p · ctrl+q · arrow · escape")
  while True:
    ch = msvcrt.getwch()
    if ch in ("\xe0", "\x00"):
      ch2 = msvcrt.getwch()
      print(f"special: {ch!r}({_ord(ch)}) + {ch2!r}({_ord(ch2)})")
      continue
    if ch == "\x1b":
      time.sleep(0.02)
      if msvcrt.kbhit():
        seq = [ch]
        while msvcrt.kbhit():
          c = msvcrt.getwch()
          seq.append(c)
          if c.isalpha() or c == "~":
            break
        print("esc-seq:", [(c, _ord(c)) for c in seq])
      else:
        print("escape (sendiri)")
      continue
    print(f"char: {ch!r} ({_ord(ch)})")
    if ch == "q":
      break


def raw_loop_posix():
  import select
  import termios
  import tty
  fd = sys.stdin.fileno()
  old = termios.tcgetattr(fd)
  try:
    tty.setcbreak(fd)
    print("RAW MODE (POSIX termios) — tekan tombol, 'q' untuk keluar")
    while True:
      b = os.read(fd, 1)
      if b == b"\x1b":
        r, _, _ = select.select([fd], [], [], 0.05)
        seq = b
        if r:
          seq += os.read(fd, 1)
          if seq == b"\x1b[":
            seq += os.read(fd, 1)
            if seq in (b"\x1b[5", b"\x1b[6", b"\x1b[3"):
              seq += os.read(fd, 1)
        print("seq:", [hex(x) for x in seq], "=", seq)
      else:
        print("byte:", [hex(x) for x in b], "=", b)
        if b == b"q":
          break
  finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old)


def tuiko_loop():
  sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  from tuiko import session
  from tuiko.keys import read_key
  print("TUIKO MODE — pakai read_key() persis kayak indonime, 'q' untuk keluar")
  with session():
    while True:
      k = read_key()
      print(f"tuiko key: {k!r}")
      if k == "q":
        break


if __name__ == "__main__":
  if "--tuiko" in sys.argv:
    tuiko_loop()
  elif os.name == "nt":
    raw_loop_win()
  else:
    raw_loop_posix()
