

import os
import select
import signal
import sys
import time
import unittest

try:
    import pty
    HAVE_PTY = True
except ImportError:
    HAVE_PTY = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@unittest.skipUnless(HAVE_PTY, "modul pty cuma ada di POSIX — Windows: smoke manual")
class TestTuiReal(unittest.TestCase):

    def _spawn(self, argv):

        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(ROOT)
            os.execv(sys.executable, [sys.executable] + argv)
        return pid, fd

    def _read_until(self, fd, patterns, timeout=8.0):

        data = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if all(p in data for p in patterns):
                return data, True
            r, _, _ = select.select([fd], [], [], 0.2)
            if not r:
                continue
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            data += chunk
        return data, all(p in data for p in patterns)

    def _send(self, fd, data):
        try:
            os.write(fd, data)
        except OSError:
            pass
        time.sleep(0.15)

    def _kill(self, pid, fd):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass


    def test_demo_full_flow(self):

        pid, fd = self._spawn(["-m", "tuiko"])
        try:
            out, ok = self._read_until(fd, [b"Cari menu"], timeout=10)
            self.assertTrue(ok, f"prompt gak muncul: {out[-400:]!r}")
            self._send(fd, b"nasi\r")
            out, ok = self._read_until(fd, [b"Pilih menu"], timeout=5)
            self.assertTrue(ok, f"daftar menu gak muncul: {out[-400:]!r}")
            self._send(fd, b"\r")
            out, ok = self._read_until(fd, [b"Pilih porsi"], timeout=5)
            self.assertTrue(ok, f"daftar porsi gak muncul: {out[-400:]!r}")
            self._send(fd, b" \x1b[B \r")
            out, ok = self._read_until(fd, [b"Semua 2 porsi beres"], timeout=15)
        finally:
            self._kill(pid, fd)
        self.assertTrue(ok, f"alur gak kelar: {out[-500:]!r}")
        self.assertIn(b"100.0%", out)
        self.assertIn(b"Porsi 1", out)
        self.assertIn(b"\x1b[?1049l", out)
        self.assertIn(b"\x1b[?25h", out)

    def test_escape_quit(self):
        pid, fd = self._spawn(["-m", "tuiko"])
        try:
            self._read_until(fd, [b"Cari menu"], timeout=10)
            self._send(fd, b"\x1b")
            out, ok = self._read_until(fd, [b"Sayonara"], timeout=5)
        finally:
            self._kill(pid, fd)
        self.assertTrue(ok, f"gak keluar: {out[-400:]!r}")
        self.assertIn(b"\x1b[?1049l", out)

    def test_ctrl_c_clean(self):

        pid, fd = self._spawn(["-m", "tuiko"])
        try:
            self._read_until(fd, [b"Cari menu"], timeout=10)
            self._send(fd, b"\x03")
            out, ok = self._read_until(fd, [b"\x1b[?25h"], timeout=5)
        finally:
            self._kill(pid, fd)
        self.assertTrue(ok, f"ctrl-c gak bersih: {out[-400:]!r}")


    def test_read_key_arrow_real(self):
        code = ("from tuiko.keys import enable_raw, read_key; import sys; "
                "enable_raw(); sys.stdout.write('KEY=' + read_key()); sys.stdout.flush()")
        pid, fd = self._spawn(["-c", code])
        try:
            time.sleep(0.6)
            self._send(fd, b"\x1b[A")
            out, ok = self._read_until(fd, [b"KEY=up"], timeout=5)
        finally:
            self._kill(pid, fd)
        self.assertTrue(ok, f"panah gak ke-baca: {out[-200:]!r}")

    def test_read_key_escape_real(self):
        code = ("from tuiko.keys import enable_raw, read_key; import sys; "
                "enable_raw(); sys.stdout.write('KEY=' + read_key()); sys.stdout.flush()")
        pid, fd = self._spawn(["-c", code])
        try:
            time.sleep(0.6)
            self._send(fd, b"\x1b")
            out, ok = self._read_until(fd, [b"KEY=escape"], timeout=5)
        finally:
            self._kill(pid, fd)
        self.assertTrue(ok, f"escape gak ke-baca: {out[-200:]!r}")


if __name__ == "__main__":
    unittest.main()
