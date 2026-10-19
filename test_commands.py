"""اختبارات الأوامر: تستدعي main.py فعلياً داخل مجلد مؤقت."""

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout

import main

REPO_DIR = os.path.dirname(os.path.abspath(__file__))


class CommandTestCase(unittest.TestCase):
    """كل اختبار يعمل في مجلد مؤقت حتى لا يلمس بيانات الجلسات الحقيقية."""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp()
        os.chdir(self._tmp)
        main.FileManager.ensure_directories()
        with open(os.path.join(REPO_DIR, "commands.json"), encoding="utf-8") as f:
            commands = json.load(f)
        self.session = main.Session()
        self.cm = main.CommandManager(self.session, {}, commands)

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self._tmp, ignore_errors=True)

    def run_cmd(self, name):
        with redirect_stdout(io.StringIO()):
            return self.cm.execute(name)


class TestCommands(CommandTestCase):

    def test_commands_file_has_nine_commands(self):
        self.assertEqual(len(self.cm.commands["commands"]), 9)

    def test_unknown_command_fails(self):
        result = self.run_cmd("طيران")
        self.assertFalse(result["success"])

    def test_start_activates_and_saves_session(self):
        self.run_cmd("ابدأ")
        self.assertEqual(self.session.data["status"], "active")
        with open(main.SESSION_FILE, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["status"], "active")

    def test_pause_then_resume(self):
        self.run_cmd("ابدأ")
        self.run_cmd("بريك")
        self.assertEqual(self.session.data["status"], "paused")
        self.run_cmd("اكمل")
        self.assertEqual(self.session.data["status"], "active")

    def test_exit_archives_session(self):
        self.run_cmd("ابدأ")
        result = self.run_cmd("خروج")
        self.assertEqual(self.session.data["status"], "closed")
        self.assertTrue(os.path.exists(result["archive_file"]))

    def test_history_records_commands(self):
        self.run_cmd("ابدأ")
        self.run_cmd("بريك")
        self.assertTrue(self.session.history[-1].endswith("PAUSE_TIMER"))


if __name__ == "__main__":
    unittest.main()
