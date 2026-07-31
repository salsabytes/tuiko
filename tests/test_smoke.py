import importlib.util
import io
import os
import unittest

import tuiko
import tuiko.demo as demo
from tuiko import keys
from tuiko.core import esc, strip_ansi, style
from tuiko.widgets import box, multiselect, progress, prompt, select, status


class TestCore(unittest.TestCase):
  def test_esc_and_style(self):
    self.assertEqual(esc(1, 36), "\x1b[1;36m")
    self.assertEqual(style("x", 36), "\x1b[36mx\x1b[0m")

  def test_strip_ansi(self):
    self.assertEqual(strip_ansi(style("halo", 36)), "halo")

  def test_box(self):
    lines = box("Judul", ["satu", "dua"], width=40)
    self.assertTrue(strip_ansi(lines[0]).startswith("╭"))
    self.assertTrue(strip_ansi(lines[-1]).startswith("╰"))
    self.assertIn("satu", lines[1])


class TestKeys(unittest.TestCase):
  def test_win_arrows(self):
    self.assertEqual(keys._parse_win("\xe0", "H"), "up")
    self.assertEqual(keys._parse_win("\xe0", "P"), "down")
    self.assertEqual(keys._parse_win("\xe0", "I"), "pgup")

  def test_posix_arrows(self):
    self.assertEqual(keys._parse_posix(b"\x1b[A"), "up")
    self.assertEqual(keys._parse_posix(b"\x1b[B"), "down")
    self.assertEqual(keys._parse_posix(b"\x1b[5~"), "pgup")
    self.assertEqual(keys._parse_posix(b"\x1b"), "escape")

  def test_char_normalize(self):
    self.assertEqual(keys._normalize_char("\r"), "enter")
    self.assertEqual(keys._normalize_char("\x7f"), "backspace")
    self.assertEqual(keys._normalize_char("a"), "a")
    self.assertEqual(keys._normalize_char("\x03"), "ctrl-c")


class TestPrompt(unittest.TestCase):
  def test_typing(self):
    out = io.StringIO()
    v = prompt("Nama:", key_source=iter(["n", "a", "r", "u", "space", "t", "o", "enter"]), out=out)
    self.assertEqual(v, "naru to")
    self.assertIn("naru to", out.getvalue())

  def test_backspace_escape(self):
    out = io.StringIO()
    self.assertIsNone(prompt("x", default="abc", key_source=iter(["backspace", "escape"]), out=out))


class TestSelect(unittest.TestCase):
  ITEMS = [f"EP{i:02d}" for i in range(1, 25)]

  def test_pick(self):
    out = io.StringIO()
    idx = select("Pilih:", self.ITEMS, page_size=10, key_source=iter(["down", "down", "enter"]), out=out)
    self.assertEqual(idx, 2)


    raw = out.getvalue()
    self.assertIn(f"\x1b[1m\x1b[38;5;{tuiko.theme.select_fg}mEP03", raw)
    self.assertIn(f"\x1b[48;5;{tuiko.theme.select_bg}m", raw)
    self.assertNotIn("\x1b[48;5;60m", raw)
    self.assertNotIn("▶", raw)

  def test_page_nav(self):
    out = io.StringIO()
    idx = select("Pilih:", self.ITEMS, page_size=10, key_source=iter(["pgdn", "down", "enter"]), out=out)
    self.assertEqual(idx, 11)

  def test_digit_jump(self):
    out = io.StringIO()
    idx = select("Pilih:", self.ITEMS, page_size=10, key_source=iter(["5", "enter"]), out=out)
    self.assertEqual(idx, 4)

  def test_escape_back(self):
    out = io.StringIO()
    self.assertIsNone(select("Pilih:", self.ITEMS, key_source=iter(["escape"]), out=out))

  def test_empty(self):
    self.assertIsNone(select("Pilih:", [], key_source=iter([]), out=io.StringIO()))


class TestMultiselect(unittest.TestCase):
  def test_toggle_and_confirm(self):
    out = io.StringIO()
    picked = multiselect("Pilih:", [f"EP{i:02d}" for i in range(1, 13)], page_size=10,
                         key_source=iter(["space", "down", "space", "enter"]), out=out)
    self.assertEqual(picked, {0, 1})

  def test_untoggle(self):
    out = io.StringIO()
    picked = multiselect("Pilih:", ["a", "b"], key_source=iter(["space", "space", "enter"]), out=out)
    self.assertEqual(picked, set())

  def test_escape(self):
    out = io.StringIO()
    self.assertIsNone(multiselect("Pilih:", ["a"], key_source=iter(["escape"]), out=out))


class TestProgress(unittest.TestCase):
  def test_bar_writes(self):
    out = io.StringIO()
    with progress("Proses", total=100, out=out) as up:
      up(50)
    self.assertIn("█", out.getvalue())
    self.assertIn("50.0%", out.getvalue())

  def test_spinner_when_total_none(self):
    out = io.StringIO()
    with progress("Kerja", total=None, out=out) as up:
      up(None)
    self.assertIn("⠋", out.getvalue())


class TestDemo(unittest.TestCase):
  def test_full_flow_headless(self):

    out = io.StringIO()
    keys_iter = iter([
      "n", "a", "s", "i", "enter",
      "enter",
      "space", "down", "space", "enter",
    ])
    status_, data = demo.run_flow(key_source=keys_iter, out=out, sleep=0)
    self.assertEqual(status_, "done")
    self.assertEqual(data, [0, 1])
    self.assertIn("100.0%", out.getvalue())

  def test_no_result(self):
    out = io.StringIO()
    status_, _ = demo.run_flow(key_source=iter(["z", "z", "z", "enter"]), out=out, sleep=0)
    self.assertEqual(status_, "none")

  def test_empty_picks(self):

    out = io.StringIO()
    keys_iter = iter(["n", "a", "s", "i", "enter", "enter", "enter"])
    status_, _ = demo.run_flow(key_source=keys_iter, out=out, sleep=0)
    self.assertEqual(status_, "empty")


class TestAnimeDemo(unittest.TestCase):
  @staticmethod
  def _load():

    path = os.path.join(os.path.dirname(__file__), "..", "examples", "anime_search.py")
    spec = importlib.util.spec_from_file_location("anime_search", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

  def test_full_flow_headless(self):
    demo = self._load()
    out = io.StringIO()
    keys_iter = iter([
      "o", "s", "h", "i", "enter",
      "enter",
      "space", "down", "space", "enter",
    ])
    status_, data = demo.run_flow(key_source=keys_iter, out=out, sleep=0)
    self.assertEqual(status_, "done")
    self.assertEqual(data, [0, 1])
    self.assertIn("100.0%", out.getvalue())
    self.assertIn("Oshi no Ko", out.getvalue())

  def test_no_result(self):
    demo = self._load()
    out = io.StringIO()
    status_, _ = demo.run_flow(key_source=iter(["z", "z", "z", "enter"]), out=out, sleep=0)
    self.assertEqual(status_, "none")

  def test_empty_picks(self):
    demo = self._load()
    out = io.StringIO()
    keys_iter = iter(["o", "s", "h", "i", "enter", "enter", "enter"])
    status_, _ = demo.run_flow(key_source=keys_iter, out=out, sleep=0)
    self.assertEqual(status_, "empty")

class TestUiCustom(unittest.TestCase):
  def test_override_icons(self):
    old = (tuiko.ui.cursor, tuiko.ui.star)
    try:
      tuiko.ui.cursor = "▌"
      tuiko.ui.star = "★"
      out = io.StringIO()
      prompt("Nama", key_source=iter(["x", "enter"]), out=out)
      self.assertIn("▌", out.getvalue())
      out = io.StringIO()
      status("halo", out=out)
      self.assertIn("★", out.getvalue())
    finally:
      tuiko.ui.cursor, tuiko.ui.star = old

  def test_banner_reads_ui(self):
    old = tuiko.ui.banner
    try:
      tuiko.ui.banner = "★ Tuiko"
      out = io.StringIO()
      prompt("Nama", key_source=iter(["enter"]), out=out, header=demo._banner())
      self.assertIn("★ Tuiko", strip_ansi(out.getvalue()))
    finally:
      tuiko.ui.banner = old

  def test_box_border_custom(self):
    old = tuiko.ui.box_border
    try:
      tuiko.ui.box_border = "+-+|+++"
      lines = box("Judul", ["satu"], width=40)
      self.assertTrue(strip_ansi(lines[0]).startswith("+"))
      self.assertTrue(strip_ansi(lines[-1]).startswith("+"))
    finally:
      tuiko.ui.box_border = old

class TestStatusBar(unittest.TestCase):
  def test_prompt_bar(self):
    out = io.StringIO()
    prompt("Nama", hint="[ESC] keluar", key_source=iter(["enter"]), out=out)
    fr = strip_ansi(out.getvalue())
    self.assertIn("ESC", fr)
    self.assertNotIn("PROMPT", fr)
    self.assertNotIn("utf-8", fr)
    self.assertNotIn(f"tuiko {tuiko.__version__}", fr)

  def test_select_bar_buttons(self):
    out = io.StringIO()
    select("Pilih", ["a"], key_source=iter(["enter"]), out=out)
    raw = out.getvalue()
    self.assertNotIn("SELECT", strip_ansi(raw))
    self.assertIn(f"\x1b[48;5;{tuiko.theme.key_bg}m", raw)
    self.assertIn("\x1b[1m\x1b[38;5;255m", raw)

  def test_bar_fits_terminal(self):
    old = tuiko.widgets.term_width
    try:
      tuiko.widgets.term_width = lambda: 60
      out = io.StringIO()
      multiselect("Pilih", ["a"], key_source=iter(["enter"]), out=out)
      for line in strip_ansi(out.getvalue()).splitlines():
        self.assertLessEqual(len(line), 60, f"baris overflow: {line!r}")
    finally:
      tuiko.widgets.term_width = old

  def test_card_follows_terminal_width(self):
    old = tuiko.widgets.term_width
    try:
      tuiko.widgets.term_width = lambda: 120
      out = io.StringIO()
      select("Pilih", ["a"], key_source=iter(["enter"]), out=out)
      for line in strip_ansi(out.getvalue()).splitlines():
        self.assertEqual(len(line), 116, f"baris bukan selebar card 116: {line!r}")
    finally:
      tuiko.widgets.term_width = old

  def test_page_size_follows_terminal_height(self):
    old_w, old_h = tuiko.widgets.term_width, tuiko.widgets.term_height
    try:
      tuiko.widgets.term_width = lambda: 80
      tuiko.widgets.term_height = lambda: 20
      items = [f"EP{i:02d}" for i in range(1, 41)]
      out = io.StringIO()
      idx = select("Pilih:", items, key_source=iter(["pgdn", "enter"]), out=out)
      self.assertEqual(idx, 12, "pgdn harus geser jendela ke EP13 (indeks 12)")
      frames = out.getvalue().split("\x1b[2J")
      for frame in frames:
        rows = [r for r in strip_ansi(frame).splitlines() if r]
        self.assertLessEqual(len(rows), 20, f"frame overflow: {len(rows)} baris")
      self.assertIn("EP13", strip_ansi(frames[-1]))
      self.assertIn("ENTER", strip_ansi(out.getvalue()))
    finally:
      tuiko.widgets.term_width, tuiko.widgets.term_height = old_w, old_h

  def test_window_scroll_drops_top(self):
    out = io.StringIO()
    idx = select("Pilih:", [f"EP{i:02d}" for i in range(1, 11)], page_size=5,
                 key_source=iter(["down", "down", "down", "down", "down", "enter"]), out=out)
    self.assertEqual(idx, 5)
    frames = [f for f in out.getvalue().split("\x1b[2J") if f]
    last = strip_ansi(frames[-1])
    self.assertIn("EP06", last)
    self.assertNotIn("EP01", last)

  def test_header_kept_when_short_terminal(self):
    old_w, old_h = tuiko.widgets.term_width, tuiko.widgets.term_height
    try:
      tuiko.widgets.term_width = lambda: 80
      tuiko.widgets.term_height = lambda: 12
      header = ["✦ Judul", "subjudul"]
      out = io.StringIO()
      select("Pilih:", [f"EP{i:02d}" for i in range(1, 21)], header=header,
             key_source=iter(["enter"]), out=out)
      raw = strip_ansi(out.getvalue())
      self.assertIn("✦ Judul", raw)
      self.assertIn("ENTER", raw)
      self.assertNotIn("EP04", raw)
    finally:
      tuiko.widgets.term_width, tuiko.widgets.term_height = old_w, old_h


if __name__ == "__main__":
  unittest.main()
