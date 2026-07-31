

import time

import tuiko
from tuiko import (
  grad,
  multiselect,
  progress,
  prompt,
  select,
  session,
  status,
  theme,
  ui,
)


ui.banner = "★ Tuiko"
ui.cursor = "▌"
ui.star = "★"
ui.checked = "[X]"
ui.unchecked = "[ ]"
ui.spinner = "◐◓◑◒"
ui.working = "Mikir..."
ui.hint_select = "[↑/↓] Gerak · [ENTER] Pilih · [ESC] Batal"
ui.hint_multiselect = "[↑/↓] Gerak · [SPACE] Tandai · [ENTER] Lanjut · [ESC] Batal"
ui.box_border = "+-+|+++"


theme.accent = 208
theme.accent_bright = 214
theme.select_fg = 214
theme.grad = (94, 136, 172, 208, 214, 220)


def banner():
  return [grad(f"  {ui.banner}  ", theme.grad)]


def main():
  with session():
    nama = prompt("Siapa namamu?", hint="[ESC] keluar", header=banner())
    if nama is None:
      status("Dibatalkan.")
      return

    hobi = select("Hobi favoritmu:", ["Koding", "Main game", "Baca manga"],
                  header=banner())
    if hobi is None:
      status("Dibatalkan.")
      return

    lain = multiselect("Yang ini juga suka:", ["Nonton film", "Dengerin musik", "Jalan-jalan"],
                       header=banner())
    if lain is None:
      status("Dibatalkan.")
      return

    with progress("Nyiapin...", total=100) as up:
      for p in range(0, 101, 25):
        up(p)
        time.sleep(0.2)
    status(f"Sampai ketemu, {nama}!")

if __name__ == "__main__":
  main()
