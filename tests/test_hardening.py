"""Tests for the hardened-build patches (see HARDENING.md).

If a future upstream change breaks one of these, the corresponding patch
needs to be re-applied or reworked during the hardened sync.
"""
import hashlib
import io
import json
import os
import signal
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import ou_dedetai.constants as constants
import ou_dedetai.network as network
import ou_dedetai.system as system
import ou_dedetai.utils as utils


class _Exit(Exception):
    pass


def _app():
    app = Mock()
    app.exit = Mock(side_effect=_Exit)
    return app


class TestH1SelfUpdateDisabled(unittest.TestCase):
    def test_update_lli_binary_does_nothing(self):
        app = _app()
        with patch.object(network, "logos_reuse_download") as dl, \
             patch.object(utils, "restart_lli") as restart:
            network.update_lli_binary(app)
        dl.assert_not_called()
        restart.assert_not_called()
        self.assertIn("disabled", app.status.call_args[0][0])


class TestH2PinnedHashes(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name)
        self.file = self.dir / "payload.bin"
        self.file.write_bytes(b"hello hardened world")
        self.sha = hashlib.sha256(b"hello hardened world").hexdigest()
        self.pins = self.dir / "pins.json"
        self._orig = network.PINS_FILE
        network.PINS_FILE = self.pins
        os.environ.pop(network.ALLOW_UNPINNED_ENV, None)

    def tearDown(self):
        network.PINS_FILE = self._orig
        os.environ.pop(network.ALLOW_UNPINNED_ENV, None)
        self.td.cleanup()

    def _pin(self, url, sha):
        self.pins.write_text(json.dumps({"pins": {url: {"sha256": sha}}}))

    def test_match_passes(self):
        self._pin("https://x/y", self.sha)
        app = _app()
        network._enforce_pinned_hash("https://x/y", self.file, app)
        app.exit.assert_not_called()

    def test_mismatch_exits_and_keeps_file(self):
        self._pin("https://x/y", "0" * 64)
        with self.assertRaises(_Exit):
            network._enforce_pinned_hash("https://x/y", self.file, _app())
        self.assertTrue(self.file.exists())

    def test_unpinned_exits(self):
        self._pin("https://other", self.sha)
        app = _app()
        with self.assertRaises(_Exit):
            network._enforce_pinned_hash("https://x/y", self.file, app)
        self.assertIn(self.sha, app.exit.call_args[0][0])

    def test_unpinned_override(self):
        self._pin("https://other", self.sha)
        os.environ[network.ALLOW_UNPINNED_ENV] = "1"
        app = _app()
        network._enforce_pinned_hash("https://x/y", self.file, app)
        app.exit.assert_not_called()

    def test_bundled_pin_file_is_valid(self):
        data = json.loads(self._orig.read_text())
        for url, entry in data["pins"].items():
            self.assertTrue(url.startswith("https://"), url)
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")

    def test_reuse_download_enforces_pin(self):
        app = _app()
        app.conf.user_download_dir = None
        app.conf.download_dir = str(self.dir)
        self._pin("https://x/y", "0" * 64)
        with patch.object(network, "_verify_downloaded_file", return_value=True):
            with self.assertRaises(_Exit):
                network.logos_reuse_download("https://x/y", self.file.name, str(self.dir), app=app)


class TestH3SafeTar(unittest.TestCase):
    def test_path_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            archive = td / "evil.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo("../escaped.txt")
                info.size = 3
                tar.addfile(info, io.BytesIO(b"bad"))
            out = td / "out"
            utils.untar_file(archive, out)
            self.assertFalse((td / "escaped.txt").exists())


class TestH4RootScript(unittest.TestCase):
    def test_arguments_are_quoted(self):
        script = system._build_root_script(["apt", "install", "-y", "x; rm -rf ~"], "sudo")
        self.assertEqual(script, "apt install -y 'x; rm -rf ~'")

    def test_segments_and_superuser_prefix_dropped(self):
        script = system._build_root_script(
            ["pkexec", "a", "b c", "&&", "pkexec", "d", "&&", "e"], "pkexec"
        )
        self.assertEqual(script, "a 'b c' && d && e")

    def test_runs_as_argv_without_shell(self):
        out = subprocess.run(
            ["sh", "-c", system._build_root_script(["echo", "$(id)", "&&", "echo", "ok"], "sudo")],
            capture_output=True, text=True, check=True,
        ).stdout
        self.assertEqual(out, "$(id)\nok\n")


class TestH5PidFile(unittest.TestCase):
    def test_pid_file_not_in_tmp(self):
        self.assertFalse(constants.PID_FILE.startswith("/tmp/"))

    def test_foreign_process_not_offered_for_kill(self):
        with tempfile.TemporaryDirectory() as td:
            pidfile = Path(td) / "x.pid"
            orig = constants.PID_FILE
            constants.PID_FILE = str(pidfile)
            # A live process we own that is NOT this app.
            proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
            try:
                pidfile.write_text(str(proc.pid))
                app = _app()
                app.approve = Mock(return_value=True)
                utils.die_if_running(app)
                app.approve.assert_not_called()
                self.assertIsNone(proc.poll())
            finally:
                proc.send_signal(signal.SIGTERM)
                proc.wait()
                constants.PID_FILE = orig


class TestH6NoOsSystem(unittest.TestCase):
    def test_clean_all_handles_odd_cwd(self):
        with tempfile.TemporaryDirectory() as td:
            weird = Path(td) / "a dir; touch PWNED"
            weird.mkdir()
            (weird / "wget-log.1").write_text("x")
            cwd = os.getcwd()
            os.chdir(weird)
            try:
                utils.clean_all()
            finally:
                os.chdir(cwd)
            self.assertFalse((weird / "wget-log.1").exists())
            self.assertFalse((Path(td) / "a dir").exists())
            self.assertFalse(Path(cwd, "PWNED").exists())


class TestH7UrlHandler(unittest.TestCase):
    def test_malicious_url_is_passed_verbatim(self):
        import ou_dedetai.installer as installer
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            received = td / "args.txt"
            fake_exe = td / "fake exe"  # space in path on purpose
            fake_exe.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{received}"\n')
            fake_exe.chmod(0o755)
            app = Mock()
            app.conf.logos_exe_windows_path = "C:\\users\\po\\AppData\\Local\\Logos\\Logos.exe"
            script = installer._write_url_handler_script(app, td, str(fake_exe))
            evil = f"logos4:x;touch${{IFS}}{td}/PWNED$(touch {td}/PWNED2)`touch {td}/PWNED3`'\""
            subprocess.run([str(script), evil], check=True, timeout=10)
            self.assertEqual(
                received.read_text().splitlines(),
                ["--wine", app.conf.logos_exe_windows_path, evil],
            )
            for marker in ("PWNED", "PWNED2", "PWNED3"):
                self.assertFalse((td / marker).exists(), marker)

    def test_desktop_exec_quote(self):
        import ou_dedetai.installer as installer
        self.assertEqual(installer._desktop_exec_quote('/a b/$x"`\\'), '"/a b/\\$x\\"\\`\\\\"')


if __name__ == "__main__":
    unittest.main()
