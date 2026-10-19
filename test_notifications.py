"""اختبارات إشعار المؤقت: ساعة وهمية بدل الانتظار الحقيقي."""

import io
import os
import shutil
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import main
from test_commands import CommandTestCase, REPO_DIR


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make_notifier():
    """notifier بساعة وهمية؛ الفترة طويلة جداً فلا يرسم الـ thread شيئاً بنفسه."""
    clock = FakeClock()
    out = io.StringIO()
    return main.TimerNotifier(interval=3600, out=out, clock=clock), clock, out


class TestRenderLine(unittest.TestCase):

    def test_full_time_shows_empty_bar(self):
        line = main.render_line(1500, 1500)
        self.assertTrue(line.startswith("\r\033[K"))  # يُرسم فوق السطر نفسه
        self.assertIn("[" + "░" * 30 + "] 25:00 متبقي", line)

    def test_half_time_fills_half_the_bar(self):
        self.assertIn("█" * 15 + "░" * 15, main.render_line(750, 1500))

    def test_partial_second_rounds_up(self):
        self.assertIn("24:41", main.render_line(1480.4, 1500))


class TestTimerNotifier(unittest.TestCase):

    def setUp(self):
        self.notifier, self.clock, self.out = make_notifier()

    def tearDown(self):
        self.notifier.stop()

    def test_start_shows_line_immediately(self):
        self.notifier.start(1500)
        self.assertIn("25:00 متبقي", self.out.getvalue())

    def test_tick_after_20_seconds(self):
        self.notifier.start(1500)
        self.clock.now = 20
        self.notifier.tick()
        self.assertIn("24:40 متبقي", self.out.getvalue())

    def test_ticks_refresh_one_line_instead_of_adding_lines(self):
        self.notifier.start(1500)
        for second in (20, 40, 60):
            self.clock.now = second
            self.notifier.tick()
        output = self.out.getvalue()
        self.assertEqual(output.count("\n"), 1)        # سطر البداية فقط
        self.assertEqual(output.count("\r\033[K"), 4)  # كل تحديث يمسح السطر

    def test_pause_keeps_remaining_and_stops_drawing(self):
        self.notifier.start(1500)
        self.clock.now = 100
        self.notifier.pause()
        self.assertEqual(self.notifier.remaining, 1400)
        before = self.out.getvalue()
        self.clock.now = 600
        self.notifier.tick()
        self.assertEqual(self.out.getvalue(), before)
        self.assertEqual(self.notifier.remaining_seconds(), 1400)

    def test_resume_continues_from_remaining_not_from_start(self):
        self.notifier.start(1500)
        self.clock.now = 100
        self.notifier.pause()
        self.clock.now = 600
        self.notifier.resume()
        self.clock.now = 620
        self.notifier.tick()
        self.assertIn("23:00 متبقي", self.out.getvalue())
        self.assertNotIn("25:00 متبقي", self.out.getvalue().split("\n", 1)[1])

    def test_alarm_when_time_is_up(self):
        self.notifier.start(60)
        self.clock.now = 60
        self.notifier.tick()
        self.assertIn("\a⏰ انتهى وقت المؤقت", self.out.getvalue())
        self.assertFalse(self.notifier.running)

    def test_stop_prevents_resume(self):
        self.notifier.start(1500)
        self.notifier.stop()
        self.notifier.resume()
        self.assertFalse(self.notifier.running)


class TestNotifierThread(unittest.TestCase):

    def test_thread_redraws_on_interval_and_stops_on_pause(self):
        out = io.StringIO()
        notifier = main.TimerNotifier(interval=0.05, out=out)
        notifier.start(60)
        time.sleep(0.3)
        notifier.pause()
        drawn = out.getvalue().count("⏱️")
        self.assertGreaterEqual(drawn, 3)
        time.sleep(0.2)
        self.assertEqual(out.getvalue().count("⏱️"), drawn)  # لا رسم بعد الإيقاف
        self.assertFalse(notifier._thread)

    def test_alarm_rings_on_time_even_with_long_interval(self):
        out = io.StringIO()
        notifier = main.TimerNotifier(interval=20, out=out)
        notifier.start(0.2)
        time.sleep(0.6)
        self.assertIn("انتهى وقت المؤقت", out.getvalue())
        notifier.stop()


class TestCommandsDriveTimer(CommandTestCase):
    """الأوامر تتحكم بالمؤقت: يعمل بعد ابدأ/اكمل فقط."""

    def setUp(self):
        super().setUp()
        self.cm.notifier, self.clock, self.out = make_notifier()

    def test_start_runs_timer_from_config(self):
        self.cm.config = {"timer": {"default_interval": 10}}
        self.run_cmd("ابدأ")
        self.assertTrue(self.cm.notifier.running)
        self.assertIn("10:00 متبقي", self.out.getvalue())

    def test_break_pauses_and_continue_resumes(self):
        self.run_cmd("ابدأ")
        self.clock.now = 300
        result = self.run_cmd("بريك")
        self.assertFalse(self.cm.notifier.running)
        self.assertIn("20:00", result["message"])
        self.run_cmd("اكمل")
        self.assertTrue(self.cm.notifier.running)
        self.assertEqual(self.cm.notifier.remaining_seconds(), 1200)

    def test_stop_suspend_lock_and_exit_all_stop_timer(self):
        for command in ("توقف", "نوم", "اقفال", "خروج"):
            self.run_cmd("ابدأ")
            self.run_cmd(command)
            self.assertFalse(self.cm.notifier.running, command)


class TestExitFromMenu(unittest.TestCase):
    """كتابة خروج في القائمة يجب أن تنفّذ الأمر فعلاً (كانت تغلق البرنامج فقط)."""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp()
        for name in ("commands.json", "config.json"):
            shutil.copy(os.path.join(REPO_DIR, name), self._tmp)
        os.chdir(self._tmp)

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_typing_exit_archives_session_and_stops_timer(self):
        manager = main.SessionManager()
        manager.cmd_manager.notifier, _, _ = make_notifier()
        with patch("builtins.input", side_effect=["ابدأ", "خروج"]), \
                redirect_stdout(io.StringIO()):
            manager.run()
        self.assertEqual(manager.session.data["status"], "closed")
        self.assertEqual(len(os.listdir(main.ARCHIVE_DIR)), 1)
        self.assertFalse(manager.cmd_manager.notifier.running)


if __name__ == "__main__":
    unittest.main()
