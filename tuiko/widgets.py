

import re
import sys
import time
from contextlib import contextmanager

from .core import bg, grad, render_frame, strip_ansi, style, term_height, term_width, theme, truncate, ui
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


def box(title, lines, *, width=None):

  w = width or max(term_width() - 2, 20)
  inner = max(w - 4, 10)
  t = truncate(title, inner)
  dash = max(inner - len(t) - 1, 1)
  tl, top, tr, side, bl, bottom, br = ui.box_border
  rows = [style(tl + top + " ", theme.accent) + style(t, 1, theme.accent_bright) + style(f" {top * dash}{tr}", theme.accent)]
  for ln in lines:
    rows.append(f"{side} {truncate(ln, inner).ljust(inner)} {side}")
  rows.append(style(bl + bottom * (inner + 2) + br, theme.accent))
  return rows


def _keycap(key):

  return bg(theme.key_bg, style(f" {key} ", 1, theme.key_fg))

def _hint(text):


  lines = []
  for line in text.split("\n"):
    parts = []
    pos = 0
    for m in re.finditer(r"\[([^\]]+)\]", line):
      if pos < m.start():
        parts.append(style(line[pos:m.start()], theme.muted))
      parts.append(_keycap(m.group(1)))
      pos = m.end()
    if pos < len(line):
      parts.append(style(line[pos:], theme.muted))
    lines.append("".join(parts))
  return lines


def _card_w():

  return max(term_width() - 4, 26)

def _side(content, w):

  inner = w - 2
  n = len(strip_ansi(content))
  if n > inner:
    content = truncate(strip_ansi(content), inner)
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
  left = (inner - len(t)) // 2
  return _side(" " * left + grad(t, theme.grad) + " " * (inner - left - len(t)), w)

def _pill(text):

  return bg(theme.dim_bg, style(f" {text} ", 1, theme.accent_bright))

def _title(w, message, pill=""):

  inner = w - 2
  head = " " + style(f"{ui.prompt_mark} ", 1, theme.accent_bright) + style(message, 1, theme.accent)
  if pill:
    head += " " * max(inner - len(strip_ansi(head)) - len(strip_ansi(pill)) - 1, 2) + pill
  return _side(head, w)

def _item_row(w, text, *, selected, checked=None):


  inner = w - 2
  mark = ""
  if checked is not None:
    mark = (style(ui.checked, theme.success) if checked else style(ui.unchecked, theme.muted)) + " "
  if selected:
    bar = style(ui.pointer, 1, theme.accent_bright)
    content = bar + " " + mark + style(text, 1, theme.select_fg)
    pad = max(inner - len(strip_ansi(content)), 0)
    return _side(bg(theme.select_bg, content + " " * pad), w)
  return _side("  " + mark + style(text, theme.text), w)

def _footer(w, hint):

  inner = w - 2
  line = _hint(hint)[0]
  if len(strip_ansi(line)) > inner - 2:
    line = strip_ansi(line)[: max(inner - 4, 8)].rstrip() + " …"
  return _side(" " + line, w)

def _rule(w):

  return _side(style(ui.rule * (w - 2), theme.faint), w)

def _auto_page_size(header):


  fixed = 8 + len(header)
  return max(term_height() - fixed, 3)


def _key_iter():
  while True:
    yield read_key()

def prompt(message, *, default="", hint="", key_source=None, out=None, header=()):


  keys = key_source if key_source is not None else _key_iter()
  out = out or sys.stdout
  value = default
  while True:
    w = _card_w()
    inner = w - 2
    rows = [_top(w)]
    if header:
      rows.append(_banner_row(w, header[0]))
      for h in header[1:]:
        rows.append(_side(h, w))
    rows.append(_title(w, message))

    shown = value[-max(inner - 8, 4):]
    txt = style(shown, theme.text) + style(ui.cursor, theme.accent_bright)
    field_w = max(inner - 2, 8)
    pad = max(field_w - len(strip_ansi(txt)) - 1, 1)
    field = bg(theme.field_bg, " " + txt + " " * pad)
    rows.append(_side(" " + field, w))
    if hint:
      rows.append(_rule(w))
      rows.append(_footer(w, hint))
    rows.append(_bottom(w))
    render_frame(rows, out)
    k = next(keys)
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


def _list_loop(message, items, *, page_size, multi, keys, out, header=()):


  if page_size is None:
    page_size = _auto_page_size(header)
  total = len(items)
  max_start = max(0, total - page_size)
  start, sel = 0, 0
  checked = set()
  digit_buf, last_digit = "", 0.0
  hint = ui.hint_multiselect if multi else ui.hint_select
  pages = max(1, (total + page_size - 1) // page_size)

  def _fit():

    nonlocal start
    if sel < start:
      start = sel
    elif sel > start + page_size - 1:
      start = sel - page_size + 1
    start = max(0, min(start, max_start))

  while True:
    end = min(start + page_size, total)
    w = _card_w()
    rows = [_top(w)]
    if header:
      rows.append(_banner_row(w, header[0]))
      for h in header[1:]:
        rows.append(_side(h, w))
    pill = _pill(f"{start // page_size + 1}/{pages}")
    if multi:
      pill += " " + _pill(f"{len(checked)} {ui.selected_n}")
    rows.append(_title(w, message, pill))
    rows.append(_rule(w))
    for i in range(start, end):
      rows.append(_item_row(w, items[i], selected=(i == sel),
                            checked=(i in checked) if multi else None))
    if end - start < page_size:
      rows.append(_side("", w))
    rows.append(_rule(w))
    hint_line = hint + (f"  {ui.jump_to} [{digit_buf}]" if digit_buf else "")
    rows.append(_footer(w, hint_line))
    rows.append(_bottom(w))
    render_frame(rows, out)

    k = next(keys)
    now = time.time()
    if k.isdigit():
      if now - last_digit > 1.5:
        digit_buf = ""
      digit_buf += k
      last_digit = now
      target = int(digit_buf) - 1
      if 0 <= target < total:
        sel = target
        _fit()
      continue
    digit_buf = ""
    if k == "up":
      if sel > 0:
        sel -= 1
        _fit()
    elif k == "down":
      if sel < total - 1:
        sel += 1
        _fit()
    elif k == "pgup":
      sel = max(sel - page_size, 0)
      _fit()
    elif k == "pgdn":
      sel = min(sel + page_size, total - 1)
      _fit()
    elif k == "space" and multi:
      checked.discard(sel) if sel in checked else checked.add(sel)
    elif k == "enter":
      return sel, checked
    elif k == "escape":
      return None
    elif k == "ctrl-c":
      raise KeyboardInterrupt

def select(message, items, *, page_size=None, key_source=None, out=None, header=()):


  if not items:
    return None
  keys = key_source if key_source is not None else _key_iter()
  res = _list_loop(message, items, page_size=page_size, multi=False,
                   keys=keys, out=out or sys.stdout, header=header)
  return None if res is None else res[0]

def multiselect(message, items, *, page_size=None, key_source=None, out=None, header=()):


  if not items:
    return None
  keys = key_source if key_source is not None else _key_iter()
  res = _list_loop(message, items, page_size=page_size, multi=True,
                   keys=keys, out=out or sys.stdout, header=header)
  return None if res is None else res[1]


@contextmanager
def progress(desc, total=None, *, out=None):


  out = out or sys.stdout
  i = 0
  width = max(term_width() - 4, 20)
  bar_w = max(width - len(desc) - 16, 8)

  def draw(frac, spin):
    if frac is None:
      ch = ui.spinner[spin % len(ui.spinner)]
      line = f"  {style(ch, theme.accent_bright)} {style(desc, 1, theme.accent)}  {style(ui.working, theme.muted)}"
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

  draw(None, 0)
  try:
    yield update
  finally:
    out.write("\n")
    out.flush()

def status(msg, *, prefix=None, out=None):


  out = out or sys.stdout
  if prefix is None:
    prefix = ui.star
  prefix = prefix.strip()
  if prefix:
    p = bg(theme.dim_bg, style(f" {prefix} ", 1, theme.accent_bright))
    out.write("  " + p + " " + style(msg, theme.text) + "\n")
  else:
    out.write("  " + style(msg, theme.text) + "\n")
  out.flush()
