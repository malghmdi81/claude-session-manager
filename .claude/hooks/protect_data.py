"""PreToolUse hook: يمنع الوكيل من تعديل ملفات بيانات الجلسات مباشرة.

يقرأ طلب الأداة من stdin. إذا كان الملف محمياً يخرج بالرمز 2 فيُرفض
التعديل قبل تنفيذه ويصل السبب (stderr) إلى Claude. غير ذلك يخرج بـ 0.
"""

import json
import os
import sys

PROTECTED_FILES = {"current_session.json", ".history"}
PROTECTED_DIRS = {"sessions_archive"}


def is_protected(file_path):
    parts = os.path.normpath(file_path).replace("\\", "/").split("/")
    return parts[-1] in PROTECTED_FILES or any(p in PROTECTED_DIRS for p in parts[:-1])


def main():
    try:
        request = json.load(sys.stdin)
    except ValueError:
        return 0
    file_path = request.get("tool_input", {}).get("file_path", "")
    if file_path and is_protected(file_path):
        sys.stderr.write(
            f"ممنوع: {file_path} ملف بيانات جلسات يكتبه main.py فقط. "
            "عدّل الكود الذي يكتبه بدلاً من تعديل الملف مباشرة.\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
