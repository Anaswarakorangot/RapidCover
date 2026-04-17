#!/usr/bin/env python3
"""
Fix ALL fetch calls in admin components to use authenticatedFetch.
No exceptions - every fetch call gets replaced.
"""

import re
from pathlib import Path

ADMIN_DIR = Path("frontend/src/components/admin")

def fix_file(filepath):
    """Aggressively fix all fetch calls."""
    content = filepath.read_text(encoding='utf-8')
    original = content

    # Skip if no fetch calls
    if 'await fetch(' not in content:
        return False

    # Add import if not present
    if 'authenticatedFetch' not in content:
        # Find first import
        first_import = re.search(r"import .+ from .+;", content)
        if first_import:
            pos = first_import.end()
            content = content[:pos] + "\nimport { authenticatedFetch } from '../../services/adminApi';" + content[pos:]

    # Replace ALL fetch calls - aggressive regex
    # Pattern 1: const res = await fetch(url); ...handle res.ok... res.json()
    content = re.sub(
        r'const\s+(\w+)\s*=\s*await\s+fetch\(([^)]+)\);\s*if\s*\(\s*!\s*\1\.ok\s*\)[^}]+}\s*(?:const\s+\w+\s*=\s*await\s+)?\1\.json\(\)',
        r'await authenticatedFetch(\2)',
        content,
        flags=re.DOTALL
    )

    # Pattern 2: await fetch(...) - just replace directly
    content = re.sub(
        r'await\s+fetch\(',
        r'await authenticatedFetch(',
        content
    )

    if content != original:
        filepath.write_text(content, encoding='utf-8')
        print(f"[OK] {filepath.name}")
        return True
    return False

if __name__ == "__main__":
    files = list(ADMIN_DIR.glob("*.jsx"))
    fixed = sum(fix_file(f) for f in files)
    print(f"\n[DONE] Fixed {fixed} files")
