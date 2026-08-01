

import time

from .core import grad, style, theme, ui
from .widgets import multiselect, progress, select, session, status

SLEEP = 0.05

def _banner():

  return [
    grad(f"  {ui.banner}  ", theme.grad),
    style("  pesan makanan — cari, pilih, tandai porsi", theme.muted),
  ]

_CATALOG = [
  ("Nasi Goreng Spesial", 4), ("Mie Ayam Bakso", 3), ("Sate Ayam", 5),
  ("Soto Betawi", 3), ("Gado-Gado", 2), ("Rendang Sapi", 4),
  ("Bakso Urat", 3), ("Pempek Palembang", 2),
]

def _portions(title):

  n = next(n for t, n in _CATALOG if t == title)
  return [f"Porsi {i} — {title}" for i in range(1, n + 1)]

def run_flow(key_source=None, out=None, sleep=SLEEP):

  titles = [t for t, _ in _CATALOG]
  t = select("Cari menu:", titles, search=True, key_source=key_source, out=out, header=_banner())
  if t is None:
    return "quit", None
  title = titles[t]
  picks = multiselect(f"Pilih porsi ({title}):", _portions(title), search=True,
                      key_source=key_source, out=out, header=_banner())
  if picks is None:
    return "quit", None
  if not picks:
    return "empty", None
  for i in sorted(picks):
    with progress(f"Masak {_portions(title)[i]}", total=100, out=out) as up:
      for p in range(0, 101, 10):
        up(p)
        time.sleep(sleep)
    status(f"✓ {_portions(title)[i]} siap → meja", out=out)
  return "done", sorted(picks)

def main():

  try:
    with session():
      result, data = run_flow()
      if result == "quit":
        status("Sayonara ~ ✦")
      elif result == "empty":
        status("Gak ada porsi yang dipilih.")
      else:
        status(f"Semua {len(data)} porsi beres!")
      time.sleep(1.2)
  except KeyboardInterrupt:
    pass
  finally:
    print()
