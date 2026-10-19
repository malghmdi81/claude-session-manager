#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مدير جلسة كلود - Claude Session Manager
الإصدار: 1.0.0
الغرض: تطبيق تحكم بـ 9 أوامر عربية لإدارة جلسات العمل مع Claude
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ============================================================================
# الثوابت والإعدادات
# ============================================================================

CONFIG_FILE = "config.json"
COMMANDS_FILE = "commands.json"
SESSION_FILE = "current_session.json"
ARCHIVE_DIR = "sessions_archive"
HISTORY_FILE = ".history"

# ============================================================================
# فئة إدارة الملفات
# ============================================================================

class FileManager:
    """إدارة الملفات والبيانات المحفوظة"""

    @staticmethod
    def ensure_directories():
        """التأكد من وجود المجلدات الأساسية"""
        Path(ARCHIVE_DIR).mkdir(exist_ok=True)

    @staticmethod
    def load_json(filename: str) -> Dict:
        """تحميل ملف JSON"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ خطأ: الملف '{filename}' غير موجود")
            return {}

    @staticmethod
    def save_json(filename: str, data: Dict):
        """حفظ بيانات JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================================
# فئة الجلسة
# ============================================================================

class Session:
    """إدارة حالة الجلسة الحالية"""

    def __init__(self):
        self.data = self._load_session()
        self.history = self._load_history()

    def _load_session(self) -> Dict:
        """تحميل بيانات الجلسة الحالية"""
        if os.path.exists(SESSION_FILE):
            return FileManager.load_json(SESSION_FILE)
        return {
            "id": self._generate_id(),
            "start_time": None,
            "end_time": None,
            "status": "inactive",
            "timer_minutes": 0,
            "model": "claude-haiku-4.5",
            "commands_executed": [],
            "tokens_used": 0
        }

    def _load_history(self) -> List:
        """تحميل سجل العمليات"""
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f.readlines()]
        return []

    def _generate_id(self) -> str:
        """توليد معرف فريد للجلسة"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}"

    def save(self):
        """حفظ الجلسة الحالية"""
        FileManager.save_json(SESSION_FILE, self.data)

    def add_to_history(self, command: str):
        """إضافة أمر للسجل"""
        entry = f"[{datetime.now().isoformat()}] {command}"
        self.history.append(entry)
        if len(self.history) > 100:  # الاحتفاظ بـ 100 سجل فقط
            self.history.pop(0)
        self._save_history()

    def _save_history(self):
        """حفظ السجل"""
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            for entry in self.history:
                f.write(entry + '\n')

    def get_undo_steps(self) -> List:
        """الحصول على خيارات التراجع"""
        return self.history[-20:] if self.history else []

# ============================================================================
# فئة إدارة الأوامر
# ============================================================================

class CommandManager:
    """تنفيذ وإدارة الأوامر التسعة"""

    def __init__(self, session: Session, config: Dict, commands: Dict):
        self.session = session
        self.config = config
        self.commands = commands

    def execute(self, command_name: str) -> Dict:
        """تنفيذ أمر محدد"""
        cmd = self._find_command(command_name)
        if not cmd:
            return {"success": False, "message": f"❌ الأمر '{command_name}' غير موجود"}

        action = cmd['action']

        if action == "start_session":
            return self.cmd_start()
        elif action == "stop_session":
            return self.cmd_stop()
        elif action == "undo":
            return self.cmd_undo()
        elif action == "pause_timer":
            return self.cmd_pause()
        elif action == "resume_timer":
            return self.cmd_resume()
        elif action == "exit_session":
            return self.cmd_exit()
        elif action == "suspend_session":
            return self.cmd_suspend()
        elif action == "lock_session":
            return self.cmd_lock()
        elif action == "restore_session":
            return self.cmd_restore()
        else:
            return {"success": False, "message": f"❌ الإجراء '{action}' غير معروف"}

    def _find_command(self, name: str) -> Optional[Dict]:
        """البحث عن أمر بالاسم"""
        for cmd in self.commands.get('commands', []):
            if cmd['name'] == name:
                return cmd
        return None

    def cmd_start(self) -> Dict:
        """1. ابدأ - تجهيز + بدء المؤقت"""
        self.session.data['status'] = 'active'
        self.session.data['start_time'] = datetime.now().isoformat()
        self.session.add_to_history("START_SESSION")
        self.session.save()
        return {
            "success": True,
            "message": "✅ تم بدء الجلسة",
            "session_id": self.session.data['id'],
            "start_time": self.session.data['start_time']
        }

    def cmd_stop(self) -> Dict:
        """2. توقف - إيقاف + عرض الاقتراحات"""
        self.session.data['status'] = 'paused'
        self.session.data['end_time'] = datetime.now().isoformat()
        self.session.add_to_history("STOP_SESSION")
        self.session.save()

        suggestions = [
            "💡 حفظ التقدم الحالي",
            "💡 مراجعة ملخص العمل",
            "💡 أخذ فترة راحة قصيرة"
        ]

        return {
            "success": True,
            "message": "✅ تم إيقاف الجلسة",
            "suggestions": suggestions
        }

    def cmd_undo(self) -> Dict:
        """3. تراجع - الرجوع خطوة من التاريخ"""
        steps = self.session.get_undo_steps()
        if not steps:
            return {"success": False, "message": "❌ لا توجد خطوات للتراجع"}

        print("\n📜 الخطوات المتاحة للتراجع:")
        for i, step in enumerate(steps[-10:], 1):
            print(f"  {i}. {step}")

        self.session.add_to_history("UNDO_REQUEST")
        return {
            "success": True,
            "message": "✅ تم عرض خيارات التراجع",
            "available_steps": len(steps)
        }

    def cmd_pause(self) -> Dict:
        """4. بريك - توقف مؤقت للمؤقت"""
        self.session.data['status'] = 'paused'
        self.session.add_to_history("PAUSE_TIMER")
        self.session.save()

        print("\n⏸️  المؤقت متوقف - اعتن بصحتك!")
        print("💧 شرب المياه")
        print("🧘 تمرين استرخاء سريع")
        print("👀 أراح العينين قليلاً")

        return {
            "success": True,
            "message": "✅ تم إيقاف المؤقت مؤقتاً"
        }

    def cmd_resume(self) -> Dict:
        """5. اكمل - استئناف المؤقت"""
        self.session.data['status'] = 'active'
        self.session.add_to_history("RESUME_TIMER")
        self.session.save()
        return {
            "success": True,
            "message": "✅ تم استئناف المؤقت - هيا بنا!"
        }

    def cmd_exit(self) -> Dict:
        """6. خروج - مغادرة مع حفظ"""
        self.session.data['status'] = 'closed'
        self.session.data['end_time'] = datetime.now().isoformat()
        self.session.add_to_history("EXIT_SESSION")

        # أرشفة الجلسة
        archive_file = os.path.join(
            ARCHIVE_DIR,
            f"{self.session.data['id']}.json"
        )
        FileManager.save_json(archive_file, self.session.data)
        self.session.save()

        return {
            "success": True,
            "message": "✅ تم إغلاق الجلسة وحفظ البيانات",
            "archive_file": archive_file
        }

    def cmd_suspend(self) -> Dict:
        """7. نوم - تعليق مع ملخص"""
        self.session.data['status'] = 'suspended'
        self.session.add_to_history("SUSPEND_SESSION")

        summary = {
            "session_id": self.session.data['id'],
            "start_time": self.session.data['start_time'],
            "suspend_time": datetime.now().isoformat(),
            "commands_count": len(self.session.data['commands_executed'])
        }

        self.session.save()
        return {
            "success": True,
            "message": "✅ تم تعليق الجلسة - شهادة عند العودة",
            "summary": summary
        }

    def cmd_lock(self) -> Dict:
        """8. اقفال - إغلاق + نقل للأرشيف"""
        self.session.data['status'] = 'locked'
        self.session.data['end_time'] = datetime.now().isoformat()
        self.session.add_to_history("LOCK_SESSION")

        archive_file = os.path.join(
            ARCHIVE_DIR,
            f"{self.session.data['id']}_locked.json"
        )
        FileManager.save_json(archive_file, self.session.data)

        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)

        self.session.save()
        return {
            "success": True,
            "message": "✅ تم إغلاق وأرشفة الجلسة",
            "archive_file": archive_file
        }

    def cmd_restore(self) -> Dict:
        """9. عودة - استعادة جلسة سابقة"""
        archive_files = os.listdir(ARCHIVE_DIR) if os.path.exists(ARCHIVE_DIR) else []

        if not archive_files:
            return {"success": False, "message": "❌ لا توجد جلسات مؤرشفة"}

        print("\n📁 الجلسات المتاحة:")
        for i, file in enumerate(archive_files[-10:], 1):
            print(f"  {i}. {file}")

        self.session.add_to_history("RESTORE_REQUEST")
        return {
            "success": True,
            "message": "✅ جلسات متاحة للاستعادة",
            "available_sessions": len(archive_files)
        }

# ============================================================================
# البرنامج الرئيسي
# ============================================================================

class SessionManager:
    """إدارة التطبيق الرئيسية"""

    def __init__(self):
        FileManager.ensure_directories()

        self.config = FileManager.load_json(CONFIG_FILE)
        self.commands = FileManager.load_json(COMMANDS_FILE)
        self.session = Session()
        self.cmd_manager = CommandManager(self.session, self.config, self.commands)

    def display_menu(self):
        """عرض القائمة الرئيسية"""
        print("\n" + "="*50)
        print("🎯 مدير جلسة كلود - Claude Session Manager v1.0")
        print("="*50)
        print("\n📋 الأوامر المتاحة:")

        for cmd in self.commands.get('commands', []):
            print(f"  {cmd['number']}. {cmd['name']:8} - {cmd['description']}")

        print("\n" + "-"*50)
        print("اكتب رقم الأمر أو اسمه (بالعربية)")
        print("أو اكتب 'خروج' للإنهاء")
        print("-"*50 + "\n")

    def run(self):
        """حلقة البرنامج الرئيسية"""
        while True:
            self.display_menu()

            try:
                user_input = input("📌 اختر أمراً: ").strip()

                if user_input.lower() in ['خروج', 'exit', 'quit']:
                    print("\n👋 وداعاً!")
                    break

                # محاولة تنفيذ الأمر
                result = self.cmd_manager.execute(user_input)

                if result['success']:
                    print(f"\n{result['message']}")
                    if 'suggestions' in result:
                        print("\n💡 الاقتراحات:")
                        for sug in result['suggestions']:
                            print(f"  • {sug}")
                else:
                    print(f"\n{result['message']}")

            except KeyboardInterrupt:
                print("\n\n⚠️  تم الإيقاف من قبل المستخدم")
                break
            except Exception as e:
                print(f"\n❌ خطأ: {str(e)}")

# ============================================================================
# نقطة الدخول
# ============================================================================

if __name__ == "__main__":
    manager = SessionManager()
    manager.run()
