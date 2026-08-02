import importlib.util
import io
import os
import unittest

import tuiko
import tuiko.demo as demo
from tuiko import keys
from tuiko.core import disp_width, esc, pad_right, strip_ansi, style, truncate
from tuiko.widgets import box, multiselect, progress, prompt, select, status


class TestCore(unittest.TestCase):
  def test_esc_and_style(self):
    self.assertEqual(esc(1, 36), "\x1b[1;36m")
    self.assertEqual(style("x", 36), "\x1b[36mx\x1b[0m")

  def test_strip_ansi(self):
    self.assertEqual(strip_ansi(style("halo", 36)), "halo")

  def test_disp_width_wide_chars(self):
    # emoji + CJK count 2 columns, ASCII counts 1
    self.assertEqual(disp_width("abc"), 3)
    self.assertEqual(disp_width("📺  Cari anime:"), 15)
    self.assertEqual(disp_width("日本語"), 6)

  def test_disp_width_strips_ansi(self):
    self.assertEqual(disp_width(style("📺 x", 36)), 4)

  def test_pad_right_wide(self):
    self.assertEqual(pad_right("📺", 5), "📺   ")
    self.assertEqual(disp_width(pad_right("📺", 5)), 5)

  def test_truncate_wide(self):
    # truncate must fit within `width` display columns, not char count
    t = truncate("日本語のアニメタイトル", 6)
    self.assertLessEqual(disp_width(t), 6)
    self.assertTrue(t.endswith("…"))

  def test_truncate_ascii_unchanged(self):
    self.assertEqual(truncate("halo", 10), "halo")

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

  def test_ctrl_letters(self):
    self.assertEqual(keys._normalize_char("\x10"), "ctrl-p")
    self.assertEqual(keys._normalize_char("\x11"), "ctrl-q")
    self.assertEqual(keys._normalize_char("\x01"), "ctrl-a")

  def test_alt_keys(self):
    # Windows Alt+letter arrives as \x00 + letter (uppercase or lowercase) → alt-<key>,
    # and must NOT collide with arrow keys (\xe0 + letter)
    self.assertEqual(keys._parse_win("\x00", "p"), "alt-p")
    self.assertEqual(keys._parse_win("\x00", "P"), "alt-p")
    self.assertEqual(keys._parse_win("\x00", "q"), "alt-q")
    self.assertEqual(keys._parse_win("\x00", "Q"), "alt-q")
    self.assertEqual(keys._parse_win("\xe0", "P"), "down")
    self.assertEqual(keys._parse_win("\xe0", "Q"), "pgdn")
    # VT/terminal mode: ESC + letter → alt-<key>
    self.assertEqual(keys._parse_posix(b"\x1bp"), "alt-p")
    self.assertEqual(keys._parse_posix(b"\x1bq"), "alt-q")


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


class TestShortcuts(unittest.TestCase):
  def test_select_returns_shortcut_action(self):
    out = io.StringIO()
    res = select("Pilih:", ["Apple", "Banana"], shortcuts={"ctrl-q": "quit"},
                 key_source=iter(["ctrl-q"]), out=out)
    self.assertEqual(res, "quit")

  def test_select_shortcut_hint_shown(self):
    old = tuiko.widgets.term_width
    try:
      tuiko.widgets.term_width = lambda: 120  # enough room for base hint + shortcuts
      out = io.StringIO()
      select("Pilih:", ["Apple"], shortcuts={"alt-p": "provider", "ctrl-q": "quit"},
             key_source=iter(["enter"]), out=out)
      raw = strip_ansi(out.getvalue())
      self.assertIn("alt-p", raw)
      self.assertIn("provider", raw)
      self.assertIn("ctrl-q", raw)
      self.assertIn("quit", raw)
    finally:
      tuiko.widgets.term_width = old

  def test_normal_pick_still_works_with_shortcuts(self):
    out = io.StringIO()
    idx = select("Pilih:", ["Apple", "Banana", "Cherry"], shortcuts={"ctrl-q": "quit"},
                 key_source=iter(["down", "enter"]), out=out)
    self.assertEqual(idx, 1)

  def test_multiselect_shortcut(self):
    out = io.StringIO()
    res = multiselect("Pilih:", ["Apple", "Banana"], shortcuts={"ctrl-q": "quit"},
                      key_source=iter(["ctrl-q"]), out=out)
    self.assertEqual(res, "quit")


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
      "space", "down", "space", "enter",
    ])
    status_, data = demo.run_flow(key_source=keys_iter, out=out, sleep=0)
    self.assertEqual(status_, "done")
    self.assertEqual(data, [0, 1])
    self.assertIn("100.0%", out.getvalue())

  def test_cancel_on_escape(self):
    out = io.StringIO()
    status_, _ = demo.run_flow(key_source=iter(["z", "z", "z", "escape", "escape"]), out=out, sleep=0)
    self.assertEqual(status_, "quit")

  def test_empty_picks(self):

    out = io.StringIO()
    keys_iter = iter(["n", "a", "s", "i", "enter", "enter"])
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
      "space", "down", "space", "enter",
    ])
    status_, data = demo.run_flow(key_source=keys_iter, out=out, sleep=0)
    self.assertEqual(status_, "done")
    self.assertEqual(data, [0, 1])
    self.assertIn("100.0%", out.getvalue())
    self.assertIn("Oshi no Ko", out.getvalue())

  def test_cancel_on_escape(self):
    demo = self._load()
    out = io.StringIO()
    status_, _ = demo.run_flow(key_source=iter(["z", "z", "z", "escape", "escape"]), out=out, sleep=0)
    self.assertEqual(status_, "quit")

  def test_empty_picks(self):
    demo = self._load()
    out = io.StringIO()
    keys_iter = iter(["o", "s", "h", "i", "enter", "enter"])
    status_, _ = demo.run_flow(key_source=keys_iter, out=out, sleep=0)
    self.assertEqual(status_, "empty")

class TestSearch(unittest.TestCase):
  def test_type_filters_live(self):
    out = io.StringIO()
    idx = select("Pilih:", ["Apple", "Banana", "Cherry", "Grape"], search=True,
                 key_source=iter(["g", "r", "a", "enter"]), out=out)
    self.assertEqual(idx, 3)
    frames = [f for f in out.getvalue().split("\x1b[2J") if f]
    last = strip_ansi(frames[-1])
    self.assertIn("Grape", last)
    self.assertNotIn("Apple", last)

  def test_backspace_edits_query(self):
    out = io.StringIO()
    idx = select("Pilih:", ["Apple", "Banana", "Cherry"], search=True,
                 key_source=iter(["b", "a", "n", "backspace", "n", "a", "enter"]), out=out)
    self.assertEqual(idx, 1)

  def test_escape_clears_then_cancels(self):
    out = io.StringIO()
    res = select("Pilih:", ["Apple", "Banana"], search=True,
                 key_source=iter(["a", "escape", "escape"]), out=out)
    self.assertIsNone(res)

  def test_enter_on_no_match_noop(self):
    out = io.StringIO()
    res = select("Pilih:", ["Apple", "Banana"], search=True,
                 key_source=iter(["z", "z", "enter", "escape", "escape"]), out=out)
    self.assertIsNone(res)

  def test_multiselect_search_toggle(self):
    out = io.StringIO()
    picked = multiselect("Pilih:", ["Apple", "Banana", "Grape", "Kiwi"], search=True,
                         key_source=iter(["a", "space", "enter"]), out=out)
    self.assertEqual(picked, {0})

  def test_search_row_rendered(self):
    out = io.StringIO()
    select("Pilih:", ["Apple", "Banana"], search=True,
           key_source=iter(["a", "enter"]), out=out)
    raw = strip_ansi(out.getvalue())
    self.assertIn("Ketik untuk cari", raw)
    self.assertIn("⌕", raw)

  def test_match_highlighted_in_item(self):
    out = io.StringIO()
    select("Pilih:", ["Papaya", "Apple", "Banana"], search=True,
           key_source=iter(["p", "a", "enter"]), out=out)
    raw = out.getvalue()
    self.assertIn(f"\x1b[1m\x1b[38;5;{tuiko.theme.highlight}mPa", raw)
    self.assertIn(f"\x1b[1m\x1b[38;5;{tuiko.theme.highlight}mpa", raw)

  def test_fuzzy_subsequence_match(self):
    out = io.StringIO()
    idx = select("Pilih:", ["Spy x Family", "Spy Kids", "One Piece"], search=True, fuzzy=True,
                 key_source=iter(["s", "x", "f", "enter"]), out=out)
    self.assertEqual(idx, 0)

  def test_fuzzy_prefix_ranked_first(self):
    # typing "kyou": "Kyoukai no Kanata" (first word matches) must top the list
    # even though "Ansatsu Kyoushitsu" (second word) appears earlier in source order
    titles = ["Ansatsu Kyoushitsu", "Kyoukai no Kanata", "Denpa Kyoushi", "Gal to Kyouryuu"]
    out = io.StringIO()
    idx = select("Pilih:", titles, search=True, fuzzy=True,
                 key_source=iter(["k", "y", "o", "u", "enter"]), out=out)
    self.assertEqual(idx, 1)  # original index of "Kyoukai no Kanata"
    frames = [f for f in out.getvalue().split("\x1b[2J") if f]
    last = strip_ansi(frames[-1])
    self.assertLess(last.index("Kyoukai no Kanata"), last.index("Ansatsu Kyoushitsu"),
                    "first-word match harus lebih atas dari second-word match")

  def test_fuzzy_off_uses_substring(self):
    out = io.StringIO()
    res = select("Pilih:", ["Spy x Family", "Spy Kids", "One Piece"], search=True, fuzzy=False,
                 key_source=iter(["s", "x", "f", "enter", "escape", "escape"]), out=out)
    self.assertIsNone(res)

  def test_fuzzy_highlights_scattered_chars(self):
    out = io.StringIO()
    select("Pilih:", ["Spy x Family", "Spy Kids"], search=True, fuzzy=True,
           key_source=iter(["s", "x", "f", "enter"]), out=out)
    raw = out.getvalue()
    self.assertIn(f"\x1b[1m\x1b[38;5;{tuiko.theme.highlight}mS", raw)
    self.assertIn(f"\x1b[1m\x1b[38;5;{tuiko.theme.highlight}mx", raw)
    self.assertIn(f"\x1b[1m\x1b[38;5;{tuiko.theme.highlight}mF", raw)

  def test_search_fits_terminal_height(self):
    old_w, old_h = tuiko.widgets.term_width, tuiko.widgets.term_height
    try:
      tuiko.widgets.term_width = lambda: 80
      tuiko.widgets.term_height = lambda: 14
      items = [f"EP{i:02d}" for i in range(1, 41)]
      out = io.StringIO()
      select("Pilih:", items, search=True,
             key_source=iter(["1", "enter"]), out=out)
      frames = [f for f in out.getvalue().split("\x1b[2J") if f]
      for frame in frames:
        rows = [r for r in strip_ansi(frame).splitlines() if r]
        self.assertLessEqual(len(rows), 14, f"frame overflow: {len(rows)} baris")
    finally:
      tuiko.widgets.term_width, tuiko.widgets.term_height = old_w, old_h


class TestWideAlign(unittest.TestCase):
  def _frame_widths(self, out):
    rows = []
    for l in strip_ansi(out.getvalue().split("\x1b[2J")[-1]).splitlines():
      if l.strip():
        rows.append(disp_width(l))
    return rows

  def test_emoji_title_row_aligned(self):
    # regression: 📺 in the title made the pill row 1 col wider than the box
    old_w, old_h = tuiko.widgets.term_width, tuiko.widgets.term_height
    try:
      tuiko.widgets.term_width = lambda: 80
      tuiko.widgets.term_height = lambda: 24
      out = io.StringIO()
      select("📺  Cari anime:", [f"Anime {i}" for i in range(67)], page_size=1,
             key_source=iter(["enter"]), out=out)
      widths = set(self._frame_widths(out))
      self.assertEqual(len(widths), 1, f"rows misaligned: {sorted(widths)}")
      self.assertEqual(widths.pop(), 76)
    finally:
      tuiko.widgets.term_width, tuiko.widgets.term_height = old_w, old_h

  def test_cjk_items_aligned(self):
    old_w, old_h = tuiko.widgets.term_width, tuiko.widgets.term_height
    try:
      tuiko.widgets.term_width = lambda: 80
      tuiko.widgets.term_height = lambda: 24
      out = io.StringIO()
      select("Pilih:", ["葬送のフリーレン", "Spy x Family"], key_source=iter(["enter"]), out=out)
      widths = set(self._frame_widths(out))
      self.assertEqual(len(widths), 1, f"rows misaligned: {sorted(widths)}")
    finally:
      tuiko.widgets.term_width, tuiko.widgets.term_height = old_w, old_h

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
