# Tuiko

[![CodeFactor](https://www.codefactor.io/repository/github/salsabytes/tuiko/badge)](https://www.codefactor.io/repository/github/salsabytes/tuiko/issues/main)

> **Status: work in progress — this project is NOT finished yet.**
>
> The API and behavior may change at any time without notice. Do not use it in
> production. Everything you see here is experimental.

Tuiko is a tiny TUI framework for Python — **stdlib-only**, zero third-party
dependencies. It renders with ANSI escape codes and reads input via `msvcrt`
(Windows) / `termios` (POSIX).

## What works today

- `prompt` — single-line text input
- `select` — pick one item, with digit jump (`0-9`)
- `multiselect` — pick many items at once (checkboxes)
- Realtime search (`search=True`) — type to filter the list live with the
  matching text highlighted, Inquirer-style: just type and pick;
  `fuzzy=True` matches letters in sequence (e.g. `sxk` finds "Spy x Family")
- `progress` — progress bar (percentage) + spinner
- `status` — one-line notice
- `session` — full-screen mode (alt screen + raw input)
- Inquirer-style windowed scrolling; card width and items per window adapt
  to the terminal size automatically

## What is missing

- Full API documentation
- Integration with other projects (e.g. Indonime)
- Battle-tested stability — expect rough edges

## Quick usage

```python
from tuiko import prompt, select, session

with session():
    name = prompt("What's your name?", hint="[ESC] quit")
    choice = select("Pick:", ["One", "Two"], search=True, fuzzy=True)
```

## Customization

All text, icons, and colors can be overridden via `tuiko.ui` and `tuiko.theme`:

```python
import tuiko

tuiko.ui.cursor = "▌"              # input cursor
tuiko.ui.banner = "★ Tuiko"        # wordmark
tuiko.ui.hint_select = "[↑/↓] Move · [ENTER] Select · [ESC] Cancel"
```

## Examples

- `examples/custom_ui.py` — override all text & icons
- `examples/anime_search.py` — anime search demo in the style of Indonime (mock data)

## Run the demo

```bash
python -m tuiko
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Philosophy

Instead of patching InquirerPy via monkeypatching, all widgets are fully
under our control — more stable and easier to understand.
