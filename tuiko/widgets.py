

import re
import sys
import threading
import time
import types
from contextlib import contextmanager

from .core import bg, disp_width, grad, render_frame, strip_ansi, style, term_height, term_width, theme, truncate, ui
from .keys import disable_raw, enable_raw, read_key


@contextmanager
def session(out=None):


  out = out or sys.stdout
  from .core import ALT_IN, ALT_OUT, HIDE_CURSOR, SHOW_CURSOR, enable_ansi
  enable_ansi()
  out.write(ALT_IN + HIDE_CURSOR)
  out.flush()
  enable_raw()
  try:
    yield
  finally:
    disable_raw()
    out.write(SHOW_CURSOR + ALT_OUT)
    out.flush()


def _keycap(key):

  return bg(theme.key_bg, style(f" {key} ", 1, theme.key_fg))

def _hint(text):


  parts = []
  pos = 0
  for m in re.finditer(r"\[([^\]]+)\]", text):
    if pos < m.start():
      parts.append(style(text[pos:m.start()], theme.muted))
    parts.append(_keycap(m.group(1)))
    pos = m.end()
  if pos < len(text):
    parts.append(style(text[pos:], theme.muted))
  return "".join(parts)


def _card_w():

  return max(term_width() - 4, 26)

def _side(content, w):

  inner = w - 2
  n = disp_width(strip_ansi(content))
  if n > inner:
    content = truncate(strip_ansi(content), inner)
    n = disp_width(content)
    content += " " * max(inner - n, 0)
  else:
    content += " " * (inner - n)
  return ui.box_border[3] + content + ui.box_border[3]

def _top(w):

  tl, top, tr, _, _, _, _ = ui.box_border
  return style(tl + top * (w - 2) + tr, theme.border)

def _bottom(w):

  _, _, _, _, bl, bottom, br = ui.box_border
  return style(bl + bottom * (w - 2) + br, theme.border)

def _banner_row(w, line):

  inner = w - 2
  t = truncate(strip_ansi(line).strip(), inner - 4)
  tw = disp_width(t)
  left = (inner - tw) // 2
  return _side(" " * left + grad(t, theme.grad) + " " * (inner - left - tw), w)

def _pill(text):

  return bg(theme.dim_bg, style(f" {text} ", 1, theme.accent_bright))

def _title(w, message, pill=""):

  inner = w - 2
  head = " " + style(f"{ui.prompt_mark} ", 1, theme.accent_bright) + style(message, 1, theme.accent)
  if pill:
    head += " " * max(inner - disp_width(strip_ansi(head)) - disp_width(strip_ansi(pill)) - 1, 2) + pill
  return _side(head, w)

def _match_ranges(q, text, fuzzy):

  low = text.lower()
  if fuzzy:
    ranges = []
    pos = 0
    for ch in q:
      i = low.find(ch, pos)
      if i < 0:
        return None
      ranges.append((i, i + 1))
      pos = i + 1
    return ranges
  ranges = []
  pos = 0
  while True:
    i = low.find(q, pos)
    if i < 0:
      break
    ranges.append((i, i + len(q)))
    pos = i + len(q)
  return ranges or None

def _hl_text(text, ranges, base, hl):

  if not ranges:
    return style(text, *base)
  out = []
  pos = 0
  for a, b in ranges:
    if a > pos:
      out.append(style(text[pos:a], *base))
    out.append(style(text[a:b], 1, hl))
    pos = b
  if pos < len(text):
    out.append(style(text[pos:], *base))
  return "".join(out)

def _item_row(w, text, *, selected, checked=None, ranges=None):


  inner = w - 2
  mark = ""
  if checked is not None:
    mark = (style(ui.checked, theme.success) if checked else style(ui.unchecked, theme.muted)) + " "
  if selected:
    bar = style(ui.pointer, 1, theme.accent_bright)
    content = bar + " " + mark + _hl_text(text, ranges, (1, theme.select_fg), theme.highlight)
    pad = max(inner - disp_width(strip_ansi(content)), 0)
    return _side(bg(theme.select_bg, content + " " * pad), w)
  return _side("  " + mark + _hl_text(text, ranges, (theme.text,), theme.highlight), w)

def _footer(w, hint):

  inner = w - 2
  line = _hint(hint)
  if disp_width(strip_ansi(line)) > inner - 2:
    line = truncate(strip_ansi(line), max(inner - 4, 8))
  return _side(" " + line, w)

def _rule(w):

  return _side(style(ui.rule * (w - 2), theme.faint), w)

def _search_row(w, query):

  inner = w - 2
  shown = query[-max(inner - 10, 4):]
  mark = style(ui.search_mark, theme.muted)
  body = style(shown, theme.text) if query else style(ui.search_ph, theme.faint)
  txt = mark + " " + body + style(ui.cursor, theme.accent_bright)
  pad = max(inner - disp_width(strip_ansi(txt)) - 2, 1)
  return _side(" " + txt + " " * pad, w)

def _header_rows(w, header):

  rows = []
  if header:
    rows.append(_banner_row(w, header[0]))
    for h in header[1:]:
      rows.append(_side(h, w))
  return rows

def _auto_page_size(header, search=False):


  fixed = 8 + len(header) + (1 if search else 0)
  return max(term_height() - fixed, 3)


def _key_iter():
  # Polling key + deteksi resize terminal: ukuran berubah tanpa key → yield None
  # (loop yang pakai iterator ini mengartikan None sebagai "render ulang").
  last = (term_width(), term_height())
  while True:
    k = read_key(timeout=0.15)
    if k is None:
      size = (term_width(), term_height())
      if size != last:
        last = size
        yield None
      continue
    yield k

def prompt(message, *, default="", hint="", key_source=None, out=None, header=()):


  keys = key_source if key_source is not None else _key_iter()
  out = out or sys.stdout
  value = default
  while True:
    w = _card_w()
    inner = w - 2
    rows = [_top(w)]
    rows += _header_rows(w, header)
    rows.append(_title(w, message))

    shown = value[-max(inner - 8, 4):]
    txt = style(shown, theme.text) + style(ui.cursor, theme.accent_bright)
    field_w = max(inner - 2, 8)
    pad = max(field_w - disp_width(strip_ansi(txt)) - 1, 1)
    field = bg(theme.field_bg, " " + txt + " " * pad)
    rows.append(_side(" " + field, w))
    if hint:
      rows.append(_rule(w))
      rows.append(_footer(w, hint))
    rows.append(_bottom(w))
    render_frame(rows, out)
    k = next(keys)
    if k is None:  # resize terminal → re-render dengan ukuran baru
      continue
    if k == "enter":
      return value
    if k == "escape":
      return None
    if k == "ctrl-c":
      raise KeyboardInterrupt
    if k == "backspace":
      value = value[:-1]
    elif k == "space":
      value += " "
    elif len(k) == 1:
      value += k


def _list_state(page_size, auto, multi, search, fuzzy, items, hint):
  # All mutable loop state in one namespace → loop body stays flat.
  return types.SimpleNamespace(
    page_size=page_size, auto=auto, multi=multi, search=search, fuzzy=fuzzy,
    items=items,
    hint=hint, total=len(items), query="", visible=list(range(len(items))),
    match_map={}, max_start=max(0, len(items) - page_size), start=0, sel=0,
    checked=set(), digit_buf="", last_digit=0.0,
    pages=max(1, (len(items) + page_size - 1) // page_size),
  )


def _fit_scroll(st):
  # clamp start so the selected row stays inside the window
  if st.sel < st.start:
    st.start = st.sel
  elif st.sel > st.start + st.page_size - 1:
    st.start = st.sel - st.page_size + 1
  st.start = max(0, min(st.start, st.max_start))


def _apply_filter(st):
  # Filter+rank items into st.visible; reset scroll to the top.
  q = st.query.strip().lower()
  if not q:
    st.visible = list(range(st.total))
    st.match_map = {}
  else:
    scored = []
    st.match_map = {}
    for i, it in enumerate(st.items):
      ranges = _match_ranges(q, it, st.fuzzy)
      if ranges:
        # (span, start): tight/complete matches rank first (contiguous
        # "punch" beats a scattered one); on ties, earlier start wins
        # (first word beats second word).
        score = (ranges[-1][1] - ranges[0][0], ranges[0][0]) if st.fuzzy else 0
        scored.append((score, i))
        st.match_map[i] = ranges
    scored.sort(key=lambda t: (t[0], t[1]))
    st.visible = [i for _, i in scored]
  st.max_start = max(0, len(st.visible) - st.page_size)
  st.pages = max(1, (len(st.visible) + st.page_size - 1) // st.page_size)
  st.start = st.sel = 0


def _render_list(st, message, header, out):
  # Draw one frame from st; recompute page size on resize (auto).
  n = len(st.visible)
  if st.auto:
    st.page_size = _auto_page_size(header, st.search)
    st.max_start = max(0, n - st.page_size)
    st.pages = max(1, (n + st.page_size - 1) // st.page_size)
    _fit_scroll(st)
  end = min(st.start + st.page_size, n)
  w = _card_w()
  rows = [_top(w)]
  rows += _header_rows(w, header)
  if st.search and st.query:
    pill = _pill(f"{n} {ui.search_n}")
  else:
    pill = _pill(f"{st.start // st.page_size + 1}/{st.pages}")
  if st.multi:
    pill += " " + _pill(f"{len(st.checked)} {ui.selected_n}")
  rows.append(_title(w, message, pill))
  if st.search:
    rows.append(_search_row(w, st.query))
  rows.append(_rule(w))
  for i in range(st.start, end):
    idx = st.visible[i]
    rows.append(_item_row(w, st.items[idx], selected=(i == st.sel),
                          checked=(idx in st.checked) if st.multi else None,
                          ranges=st.match_map.get(idx) if st.search else None))
  if end - st.start < st.page_size:
    rows.append(_side("", w))
  rows.append(_rule(w))
  hint_line = st.hint
  if st.digit_buf:
    hint_line += f"  {ui.jump_to} [{st.digit_buf}]"
  rows.append(_footer(w, hint_line))
  rows.append(_bottom(w))
  render_frame(rows, out)


def _search_key(st, key):
  # Edit the search query. Returns True if the key was consumed.
  if key == "backspace":
    if st.query:
      st.query = st.query[:-1]
      _apply_filter(st)
    return True
  if key == "space":
    if st.multi:
      if len(st.visible):
        idx = st.visible[st.sel]
        st.checked.discard(idx) if idx in st.checked else st.checked.add(idx)
    else:
      st.query += " "
      _apply_filter(st)
    return True
  if len(key) == 1 and key.isprintable():
    st.query += key
    _apply_filter(st)
    return True
  if key == "escape" and st.query:
    st.query = ""
    _apply_filter(st)
    return True
  return False


def _jump_digit(st, key, now):
  # 0-9 digit jump (non-search only). Returns True if the key was consumed.
  if not key.isdigit() or st.search:
    return False
  if now - st.last_digit > 1.5:
    st.digit_buf = ""
  st.digit_buf += key
  st.last_digit = now
  target = int(st.digit_buf) - 1
  if 0 <= target < st.total:
    st.sel = target
    _fit_scroll(st)
  return True


def _nav_key(st, key, multi, search):
  """Navigation. Returns (action, payload); action: continue/return/quit/raise."""
  limit = len(st.visible) if search else st.total
  if key == "up":
    if st.sel > 0:
      st.sel -= 1
      _fit_scroll(st)
  elif key == "down":
    if st.sel < limit - 1:
      st.sel += 1
      _fit_scroll(st)
  elif key == "pgup":
    st.sel = max(st.sel - st.page_size, 0)
    _fit_scroll(st)
  elif key == "pgdn":
    st.sel = min(st.sel + st.page_size, limit - 1)
    _fit_scroll(st)
  elif key == "space" and multi and not search:
    st.checked.discard(st.sel) if st.sel in st.checked else st.checked.add(st.sel)
  elif key == "enter":
    if search:
      if len(st.visible):
        return ("return", (st.visible[st.sel], st.checked))
    else:
      return ("return", (st.sel, st.checked))
  elif key == "escape":
    return ("quit", None)
  elif key == "ctrl-c":
    return ("raise", KeyboardInterrupt())
  return ("continue", None)


def _list_loop(message, items, *, page_size, multi, search, fuzzy, keys, out, header=(), shortcuts=None):

  auto = page_size is None
  if page_size is None:
    page_size = _auto_page_size(header, search)
  hint = ui.hint_multiselect if multi else ui.hint_select
  if shortcuts:
    hint += "  ·  " + "  ·  ".join(f"[{k}] {v}" for k, v in shortcuts.items())
  st = _list_state(page_size, auto, multi, search, fuzzy, items, hint)

  while True:
    _render_list(st, message, header, out)
    key = next(keys)
    if key is None:  # resize terminal
      continue
    now = time.time()
    if shortcuts and key in shortcuts:
      return ("shortcut", shortcuts[key])
    if st.search and _search_key(st, key):
      continue
    if _jump_digit(st, key, now):
      continue
    st.digit_buf = ""
    action, payload = _nav_key(st, key, st.multi, st.search)
    if action == "continue":
      continue
    if action == "raise":
      raise payload
    if action == "quit":
      return None
    return payload

def _pick(message, items, multi, *, page_size=None, search=False, fuzzy=False, shortcuts=None, key_source=None, out=None, header=()):

  if not items:
    return None
  keys = key_source if key_source is not None else _key_iter()
  return _list_loop(message, items, page_size=page_size, multi=multi, search=search or fuzzy, fuzzy=fuzzy,
                    keys=keys, out=out or sys.stdout, header=header, shortcuts=shortcuts)

def select(message, items, *, page_size=None, search=False, fuzzy=False, shortcuts=None, key_source=None, out=None, header=()):

  res = _pick(message, items, False, page_size=page_size, search=search, fuzzy=fuzzy, shortcuts=shortcuts,
              key_source=key_source, out=out, header=header)
  return None if res is None else (res[1] if res[0] == "shortcut" else res[0])

def multiselect(message, items, *, page_size=None, search=False, fuzzy=False, shortcuts=None, key_source=None, out=None, header=()):

  res = _pick(message, items, True, page_size=page_size, search=search, fuzzy=fuzzy, shortcuts=shortcuts,
              key_source=key_source, out=out, header=header)
  return None if res is None else res[1]


@contextmanager
def progress(desc, total=None, *, out=None):


  out = out or sys.stdout
  i = 0
  width = max(term_width() - 4, 20)
  bar_w = max(width - disp_width(desc) - 16, 8)

  def draw(frac, spin):
    if frac is None:
      ch = ui.spinner[spin % len(ui.spinner)]
      line = f"  {style(ch, theme.accent_bright)} {style(desc, 1, theme.accent)}"
    else:
      filled = int(bar_w * max(0.0, min(frac, 1.0)))
      if frac >= 1.0:
        bar = style(ui.bar_fill * filled, theme.success) + style(ui.bar_empty * (bar_w - filled), theme.faint)
        pct = style(f" {ui.tick} {frac * 100:5.1f}{ui.pct}", 1, theme.success)
      else:
        bar = grad(ui.bar_fill * filled, theme.grad) + style(ui.bar_empty * (bar_w - filled), theme.faint)
        pct = style(f"{frac * 100:5.1f}{ui.pct}", 1, theme.accent_bright)
      line = f"  {style(desc, 1, theme.accent)}  {bar}  {pct}"
    out.write("\r\x1b[2K" + line)
    out.flush()

  def update(completed):
    nonlocal i
    if total is None:
      i += 1
      draw(None, i)
    else:
      draw(completed / total if total else 0, i)

  # Indeterminate spinner: repaint from a daemon thread so blocking callers
  # (network fetches that never call update) still get a live animation.
  stop = threading.Event()
  spin_thread = None
  if total is None:
    def _autospin():
      n = 0
      while not stop.wait(0.1):
        n += 1
        draw(None, n)
    spin_thread = threading.Thread(target=_autospin, daemon=True)
    spin_thread.start()
  draw(None, 0)
  try:
    yield update
  finally:
    if spin_thread is not None:
      stop.set()
      spin_thread.join(timeout=0.5)
    out.write("\n")
    out.flush()

def status(msg, *, out=None):

  out = out or sys.stdout
  out.write("  " + style(f"{ui.star} ", 1, theme.accent_bright) + style(msg, theme.text) + "\n")
  out.flush()
