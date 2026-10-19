"""اختبارات hook حماية ملفات البيانات: تشغّل السكربت كما يشغّله Claude Code."""

import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".claude", "hooks", "protect_data.py")


def run_hook(file_path, tool="Edit"):
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": file_path}})
    return subprocess.run([sys.executable, HOOK], input=payload, capture_output=True,
                          text=True, encoding="utf-8")


class TestProtectDataHook(unittest.TestCase):

    def test_blocks_session_file(self):
        result = run_hook("/project/current_session.json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("ممنوع", result.stderr)

    def test_blocks_history_file(self):
        self.assertEqual(run_hook("/project/.history", tool="Write").returncode, 2)

    def test_blocks_archive_folder_windows_path(self):
        self.assertEqual(run_hook(r"C:\Users\me\project\sessions_archive\s1.json").returncode, 2)

    def test_allows_source_code(self):
        result = run_hook("/project/main.py")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_allows_similar_name(self):
        self.assertEqual(run_hook("/project/current_session_notes.md").returncode, 0)


if __name__ == "__main__":
    unittest.main()
