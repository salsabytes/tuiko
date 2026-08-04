import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time

import tuiko
from tuiko import (
  grad,
  multiselect,
  progress,
  select,
  session,
  status,
  style,
  theme,
  ui,
)

SLEEP = 0.05

def _apply_theme():
  ui.banner = "✦ Indonime"
  ui.star = "✦"
  ui.selected_n = "episode dipilih"
  ui.jump_to = "→ Lompat ke:"

def _banner():
  return [
    grad(f"  {ui.banner}  ", theme.grad),
    style("  cari anime — pilih judul, tandai episode, tonton", theme.muted),
  ]

_CATALOG = [
  ("Oshi no Ko", 11),
  ("Frieren: Beyond Journey's End", 28),
  ("Jujutsu Kaisen", 24),
  ("One Piece", 12),
  ("Chainsaw Man", 12),
  ("Spy x Family", 25),
  ("Attack on Titan", 16),
  ("Kimetsu no Yaiba", 26),
  ("Bocchi the Rock!", 12),
  ("Mushoku Tensei", 23),
  ("Steins;Gate", 24),
  ("Violet Evergarden", 13),
  ("Horimiya", 13),
  ("Bakemonogatari", 15),
]

def _search(q):
  
  q = q.strip().lower()
  if not q:
    return []
  return [t for t, _ in _CATALOG if q in t.lower()]

def _episodes(title):
  n = next(n for t, n in _CATALOG if t == title)
  return [f"EP{i:02d} — {title}" for i in range(1, n + 1)]

def run_flow(key_source=None, out=None, sleep=SLEEP):
  titles = [t for t, _ in _CATALOG]
  t = select("Cari anime:", titles, search=True, fuzzy=True, key_source=key_source, out=out, header=_banner())
  if t is None:
    return "quit", None
  title = titles[t]
  picks = multiselect(f"Tandai episode ({title}):", _episodes(title), search=True,
                      key_source=key_source, out=out, header=_banner())
  if picks is None:
    return "quit", None
  if not picks:
    return "empty", None
  for i in sorted(picks):
    ep = _episodes(title)[i]
    with progress(f"Resolve stream {ep}", total=100, out=out) as up:
      for p in range(0, 101, 10):
        up(p)
        time.sleep(sleep)
    status(f"✓ {ep} siap → tonton", out=out)
  return "done", sorted(picks)

def main():
  _apply_theme()
  try:
    with session():
      result, data = run_flow()
      if result == "quit":
        status("Sayonara ~ ✦")
      elif result == "empty":
        status("Gak ada episode yang dipilih.")
      else:
        status(f"Semua {len(data)} episode beres — selamat nonton!")
      time.sleep(1.2)
  except KeyboardInterrupt:
    pass
  finally:
    print()

if __name__ == "__main__":
  main()
