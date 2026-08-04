# Custom UI — ubah semua teks & icon lewat tuiko.ui, lalu jalanin demo flow-nya.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tuiko

tuiko.ui.banner = "★ Tuiko"
tuiko.ui.star = "★"
tuiko.ui.prompt_mark = "❯"
tuiko.ui.cursor = "▌"
tuiko.ui.checked = "[X]"
tuiko.ui.unchecked = "[ ]"
tuiko.ui.bar_fill = "█"
tuiko.ui.bar_empty = "·"
tuiko.ui.tick = "✔"
tuiko.ui.rule = "-"
tuiko.ui.box_border = "+-+|+++"
tuiko.ui.spinner = "◐◓◑◒"
tuiko.ui.selected_n = "dipilih"
tuiko.ui.jump_to = "→ Loncat ke:"
tuiko.ui.pct = "%"
tuiko.ui.hint_select = "[↑/↓] Gerak · [ENTER] Pilih · [ESC] Batal"
tuiko.ui.hint_multiselect = "[↑/↓] Gerak · [SPACE] Tandai · [ENTER] Lanjut · [ESC] Batal"

if __name__ == "__main__":
    from tuiko import demo

    demo.main()  # flow yang sama, tapi dengan gaya custom di atas
