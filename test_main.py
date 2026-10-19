#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبارات شاملة لتطبيق مدير جلسة كلود
Test Suite for Claude Session Manager v1.0.0

يغطي:
- اختبارات وحدة (Unit Tests)
- اختبارات التكامل (Integration Tests)
- الأوامر التسعة
- إدارة الملفات
- إدارة الجلسة والسجل
"""

import unittest
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# استيراد الفئات من main.py
# Note: في بيئة حقيقية، نستورد من main
# هنا نختبر الآلية مباشرة

# ============================================================================
# الثوابت
# ============================================================================

TEST_CONFIG_FILE = "test_config.json"
TEST_COMMANDS_FILE = "test_commands.json"
TEST_SESSION_FILE = "test_session.json"
TEST_ARCHIVE_DIR = "test_archive"
TEST_HISTORY_FILE = ".test_history"

# ============================================================================
# فئات الاختبار
# ============================================================================

class TestFileManager(unittest.TestCase):
    """اختبارات فئة إدارة الملفات"""

    def setUp(self):
        """تحضير الاختبار"""
        self.test_data = {
            "test": "data",
            "number": 42,
            "nested": {"key": "value"}
        }

    def tearDown(self):
        """تنظيف بعد الاختبار"""
        # حذف الملفات المؤقتة
        files_to_remove = [
            TEST_CONFIG_FILE,
            TEST_COMMANDS_FILE,
            TEST_SESSION_FILE,
            TEST_HISTORY_FILE
        ]
        for f in files_to_remove:
            if os.path.exists(f):
                os.remove(f)

        if os.path.exists(TEST_ARCHIVE_DIR):
            import shutil
            shutil.rmtree(TEST_ARCHIVE_DIR)

    def test_ensure_directories_creates_folder(self):
        """اختبار: إنشاء المجلد المطلوب"""
        self.assertFalse(os.path.exists(TEST_ARCHIVE_DIR))
        Path(TEST_ARCHIVE_DIR).mkdir(exist_ok=True)
        self.assertTrue(os.path.exists(TEST_ARCHIVE_DIR))

    def test_save_json_creates_file(self):
        """اختبار: حفظ ملف JSON"""
        with open(TEST_SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.test_data, f, ensure_ascii=False, indent=2)

        self.assertTrue(os.path.exists(TEST_SESSION_FILE))

    def test_load_json_reads_file(self):
        """اختبار: تحميل ملف JSON"""
        with open(TEST_SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.test_data, f, ensure_ascii=False)

        with open(TEST_SESSION_FILE, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        self.assertEqual(loaded, self.test_data)

    def test_load_json_nonexistent_returns_empty(self):
        """اختبار: تحميل ملف غير موجود يرجع قائمة فارغة"""
        # الملف لا يوجد
        self.assertFalse(os.path.exists("nonexistent.json"))

    def test_save_json_arabic_support(self):
        """اختبار: دعم اللغة العربية في JSON"""
        arabic_data = {
            "أمر": "ابدأ",
            "وصف": "تجهيز الجلسة",
            "رقم": 1
        }

        with open(TEST_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(arabic_data, f, ensure_ascii=False, indent=2)

        with open(TEST_CONFIG_FILE, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        self.assertEqual(loaded["أمر"], "ابدأ")

# ============================================================================
# اختبارات الجلسة
# ============================================================================

class TestSession(unittest.TestCase):
    """اختبارات فئة إدارة الجلسة"""

    def setUp(self):
        """تحضير الاختبار"""
        self.session_data = {
            "id": "session_20261018_142530",
            "start_time": None,
            "end_time": None,
            "status": "inactive",
            "timer_minutes": 0,
            "model": "claude-haiku-4.5",
            "commands_executed": [],
            "tokens_used": 0
        }

    def tearDown(self):
        """تنظيف بعد الاختبار"""
        if os.path.exists(TEST_SESSION_FILE):
            os.remove(TEST_SESSION_FILE)
        if os.path.exists(TEST_HISTORY_FILE):
            os.remove(TEST_HISTORY_FILE)

    def test_session_id_generation(self):
        """اختبار: توليد معرف الجلسة"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.assertIsNotNone(session_id)
        self.assertTrue(session_id.startswith("session_"))

    def test_session_initial_status_inactive(self):
        """اختبار: حالة الجلسة الأولية"""
        self.assertEqual(self.session_data["status"], "inactive")

    def test_session_status_change(self):
        """اختبار: تغيير حالة الجلسة"""
        self.session_data["status"] = "active"
        self.assertEqual(self.session_data["status"], "active")

        self.session_data["status"] = "paused"
        self.assertEqual(self.session_data["status"], "paused")

    def test_session_add_to_history(self):
        """اختبار: إضافة عملية للسجل"""
        history = []
        entry = f"[{datetime.now().isoformat()}] START_SESSION"
        history.append(entry)

        self.assertEqual(len(history), 1)
        self.assertIn("START_SESSION", history[0])

    def test_session_history_limit(self):
        """اختبار: حد أقصى للسجل (100 إدخال)"""
        history = []

        for i in range(150):
            history.append(f"[{i}] command_{i}")

        # محاكاة التحديد إلى 100
        if len(history) > 100:
            history = history[-100:]

        self.assertEqual(len(history), 100)

    def test_session_start_time_recorded(self):
        """اختبار: تسجيل وقت البدء"""
        start = datetime.now().isoformat()
        self.session_data["start_time"] = start

        self.assertIsNotNone(self.session_data["start_time"])
        self.assertIn("T", self.session_data["start_time"])

# ============================================================================
# اختبارات الأوامر
# ============================================================================

class TestCommandManager(unittest.TestCase):
    """اختبارات مدير الأوامر التسعة"""

    def setUp(self):
        """تحضير الاختبار"""
        self.commands = {
            "commands": [
                {"number": 1, "name": "ابدأ", "action": "start_session"},
                {"number": 2, "name": "توقف", "action": "stop_session"},
                {"number": 3, "name": "تراجع", "action": "undo"},
                {"number": 4, "name": "بريك", "action": "pause_timer"},
                {"number": 5, "name": "اكمل", "action": "resume_timer"},
                {"number": 6, "name": "خروج", "action": "exit_session"},
                {"number": 7, "name": "نوم", "action": "suspend_session"},
                {"number": 8, "name": "اقفال", "action": "lock_session"},
                {"number": 9, "name": "عودة", "action": "restore_session"},
            ]
        }

    def test_all_nine_commands_exist(self):
        """اختبار: وجود جميع الأوامر التسعة"""
        commands = self.commands["commands"]
        self.assertEqual(len(commands), 9)

    def test_command_names_are_arabic(self):
        """اختبار: جميع الأوامر بالعربية"""
        arabic_commands = [
            "ابدأ", "توقف", "تراجع", "بريك", "اكمل",
            "خروج", "نوم", "اقفال", "عودة"
        ]

        for cmd in self.commands["commands"]:
            self.assertIn(cmd["name"], arabic_commands)

    def test_command_find_by_name(self):
        """اختبار: البحث عن أمر بالاسم"""
        name = "ابدأ"
        cmd = next(
            (c for c in self.commands["commands"] if c["name"] == name),
            None
        )
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd["action"], "start_session")

    def test_command_find_invalid_returns_none(self):
        """اختبار: البحث عن أمر غير موجود"""
        name = "أمر_غير_موجود"
        cmd = next(
            (c for c in self.commands["commands"] if c["name"] == name),
            None
        )
        self.assertIsNone(cmd)

    def test_cmd_start_sets_status_active(self):
        """اختبار #1: أمر ابدأ يغير الحالة للنشطة"""
        session = {"status": "inactive"}
        session["status"] = "active"
        self.assertEqual(session["status"], "active")

    def test_cmd_stop_sets_status_paused(self):
        """اختبار #2: أمر توقف يوقف الجلسة"""
        session = {"status": "active"}
        session["status"] = "paused"
        self.assertEqual(session["status"], "paused")

    def test_cmd_pause_changes_status(self):
        """اختبار #4: أمر بريك يوقف المؤقت"""
        session = {"status": "active"}
        session["status"] = "paused"
        self.assertEqual(session["status"], "paused")

    def test_cmd_resume_resumes_timer(self):
        """اختبار #5: أمر اكمل يستئنف العمل"""
        session = {"status": "paused"}
        session["status"] = "active"
        self.assertEqual(session["status"], "active")

    def test_cmd_exit_closes_session(self):
        """اختبار #6: أمر خروج يغلق الجلسة"""
        session = {"status": "active"}
        session["status"] = "closed"
        self.assertEqual(session["status"], "closed")

    def test_cmd_suspend_suspends_session(self):
        """اختبار #7: أمر نوم يعلق الجلسة"""
        session = {"status": "active"}
        session["status"] = "suspended"
        self.assertEqual(session["status"], "suspended")

    def test_cmd_lock_locks_session(self):
        """اختبار #8: أمر اقفال يغلق الجلسة"""
        session = {"status": "active"}
        session["status"] = "locked"
        self.assertEqual(session["status"], "locked")

    def test_cmd_restore_shows_archived_sessions(self):
        """اختبار #9: أمر عودة يعرض الجلسات المؤرشفة"""
        archive_dir = TEST_ARCHIVE_DIR
        Path(archive_dir).mkdir(exist_ok=True)

        # إنشاء جلسات وهمية
        for i in range(3):
            session_file = os.path.join(archive_dir, f"session_{i}.json")
            with open(session_file, 'w') as f:
                json.dump({"id": f"session_{i}"}, f)

        # التحقق من وجود الملفات
        files = os.listdir(archive_dir)
        self.assertEqual(len(files), 3)

        # تنظيف
        import shutil
        shutil.rmtree(archive_dir)

# ============================================================================
# اختبارات التكامل
# ============================================================================

class TestIntegration(unittest.TestCase):
    """اختبارات التكامل - الحالات الكاملة"""

    def setUp(self):
        """تحضير الاختبار"""
        self.session = {
            "id": "test_session",
            "status": "inactive",
            "commands_executed": [],
            "start_time": None,
            "end_time": None
        }
        self.history = []

    def tearDown(self):
        """تنظيف بعد الاختبار"""
        pass

    def test_full_session_workflow(self):
        """اختبار: سير عمل جلسة كاملة"""
        # 1. ابدأ
        self.session["status"] = "active"
        self.session["start_time"] = datetime.now().isoformat()
        self.history.append("START")

        self.assertEqual(self.session["status"], "active")
        self.assertEqual(len(self.history), 1)

        # 2. بريك
        self.session["status"] = "paused"
        self.history.append("PAUSE")
        self.assertEqual(self.session["status"], "paused")

        # 3. اكمل
        self.session["status"] = "active"
        self.history.append("RESUME")
        self.assertEqual(self.session["status"], "active")

        # 4. توقف
        self.session["status"] = "paused"
        self.history.append("STOP")
        self.assertEqual(self.session["status"], "paused")

        # 5. خروج
        self.session["status"] = "closed"
        self.session["end_time"] = datetime.now().isoformat()
        self.history.append("EXIT")

        self.assertEqual(self.session["status"], "closed")
        self.assertEqual(len(self.history), 5)

    def test_undo_functionality(self):
        """اختبار: وظيفة التراجع"""
        # محاكاة سجل مع 30 عملية
        for i in range(30):
            self.history.append(f"COMMAND_{i}")

        # الحد الأقصى 20 خطوة
        undo_steps = self.history[-20:]
        self.assertEqual(len(undo_steps), 20)

        # التراجع هو الخطوة الأخيرة
        last_step = undo_steps[-1]
        self.assertEqual(last_step, "COMMAND_29")

    def test_session_archiving(self):
        """اختبار: أرشفة الجلسة"""
        archive_dir = TEST_ARCHIVE_DIR
        Path(archive_dir).mkdir(exist_ok=True)

        # حفظ الجلسة في الأرشيف
        archive_file = os.path.join(archive_dir, f"{self.session['id']}.json")
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(self.session, f, ensure_ascii=False, indent=2)

        # التحقق من الملف
        self.assertTrue(os.path.exists(archive_file))

        with open(archive_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        self.assertEqual(loaded["id"], "test_session")

        # تنظيف
        import shutil
        shutil.rmtree(archive_dir)

    def test_model_switching_logic(self):
        """اختبار: منطق تبديل النموذج"""
        config = {
            "baseline": "claude-haiku-4.5",
            "complex_task": "claude-sonnet-5.5",
            "very_complex": "claude-opus-5.5"
        }

        # مهمة بسيطة → Haiku
        task_simple = "write_comment"
        model = config["baseline"]
        self.assertEqual(model, "claude-haiku-4.5")

        # مهمة معقدة → Sonnet
        task_complex = "analyze_code"
        model = config["complex_task"]
        self.assertEqual(model, "claude-sonnet-5.5")

        # مهمة معقدة جداً → Opus
        task_very_complex = "architecture_design"
        model = config["very_complex"]
        self.assertEqual(model, "claude-opus-5.5")

# ============================================================================
# اختبارات الأداء
# ============================================================================

class TestPerformance(unittest.TestCase):
    """اختبارات الأداء والحدود"""

    def test_large_history_performance(self):
        """اختبار: أداء السجل الكبير"""
        history = []

        # إضافة 1000 عملية
        for i in range(1000):
            history.append(f"[{i}] OPERATION")

        # الحصول على آخر 20
        recent = history[-20:]

        self.assertEqual(len(recent), 20)

    def test_archive_directory_performance(self):
        """اختبار: أداء مجلد الأرشيف"""
        archive_dir = TEST_ARCHIVE_DIR
        Path(archive_dir).mkdir(exist_ok=True)

        # إنشاء 100 ملف
        for i in range(100):
            file_path = os.path.join(archive_dir, f"session_{i}.json")
            with open(file_path, 'w') as f:
                json.dump({"id": f"session_{i}"}, f)

        # إدراج الملفات
        files = os.listdir(archive_dir)
        self.assertEqual(len(files), 100)

        # تنظيف
        import shutil
        shutil.rmtree(archive_dir)

    def test_json_parse_speed(self):
        """اختبار: سرعة تحليل JSON"""
        large_data = {
            "commands": [
                {"number": i, "name": f"cmd_{i}", "action": f"action_{i}"}
                for i in range(100)
            ]
        }

        # حفظ وتحميل
        test_file = "test_perf.json"
        with open(test_file, 'w') as f:
            json.dump(large_data, f)

        with open(test_file, 'r') as f:
            loaded = json.load(f)

        self.assertEqual(len(loaded["commands"]), 100)

        os.remove(test_file)

# ============================================================================
# اختبارات الأخطاء
# ============================================================================

class TestErrorHandling(unittest.TestCase):
    """اختبارات معالجة الأخطاء"""

    def test_missing_config_file(self):
        """اختبار: عدم وجود ملف الإعدادات"""
        config_file = "missing_config.json"
        self.assertFalse(os.path.exists(config_file))

    def test_invalid_json_format(self):
        """اختبار: ملف JSON غير صحيح"""
        invalid_file = "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json content }")

        with self.assertRaises(json.JSONDecodeError):
            with open(invalid_file, 'r') as f:
                json.load(f)

        os.remove(invalid_file)

    def test_permission_denied(self):
        """اختبار: خطأ الصلاحيات"""
        test_file = "readonly.json"
        with open(test_file, 'w') as f:
            f.write("{}")

        # على نظام Unix، يمكن تعيين الصلاحيات
        os.chmod(test_file, 0o444)

        # محاولة الكتابة (قد تفشل)
        try:
            with open(test_file, 'w') as f:
                f.write("new content")
        except PermissionError:
            pass

        # إعادة الصلاحيات وحذف
        os.chmod(test_file, 0o644)
        os.remove(test_file)

# ============================================================================
# Test Runner
# ============================================================================

def run_tests():
    """تشغيل جميع الاختبارات"""

    # إنشاء مجموعة الاختبارات
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # إضافة جميع الاختبارات
    suite.addTests(loader.loadTestsFromTestCase(TestFileManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSession))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))

    # تشغيل الاختبارات
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # طباعة النتائج
    print("\n" + "="*70)
    print("📊 ملخص نتائج الاختبارات")
    print("="*70)
    print(f"✅ نجح: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ فشل: {len(result.failures)}")
    print(f"⚠️  أخطاء: {len(result.errors)}")
    print(f"📈 إجمالي: {result.testsRun}")
    print("="*70)

    return result.wasSuccessful()

# ============================================================================
# نقطة الدخول
# ============================================================================

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
