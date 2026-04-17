#!/usr/bin/env python3
"""
Script to add admin authentication to all admin endpoints.

Adds 'admin: Admin = Depends(get_current_admin)' parameter to all
@router decorated functions in admin API files.
"""

import re
from pathlib import Path

FILES_TO_UPDATE = [
    "backend/app/api/admin.py",
    "backend/app/api/admin_panel.py",
    "backend/app/api/admin_drills.py",
    "backend/app/api/admin_monitoring.py",
]

def add_admin_auth_to_file(filepath):
    """Add admin auth parameter to all router endpoints in a file."""
    path = Path(filepath)
    if not path.exists():
        print(f"[SKIP] File not found: {filepath}")
        return

    content = path.read_text(encoding='utf-8')
    original = content

    # Add imports if not present
    if "from app.core.admin_deps import get_current_admin" not in content:
        # Find the imports section and add our import
        import_pattern = r'(from app\.database import get_db)'
        content = re.sub(
            import_pattern,
            r'\1\nfrom app.core.admin_deps import get_current_admin\nfrom app.models.admin import Admin',
            content
        )

    # Find all endpoint functions and add admin parameter
    # Pattern: @router.{method}(...)\ndef function_name(...):
    pattern = r'(@router\.(get|post|put|delete|patch)\([^\)]+\)\s*\n\s*def\s+\w+\s*\([^)]*)(db:\s*Session\s*=\s*Depends\(get_db\))'

    def add_admin_param(match):
        """Add admin parameter before db parameter."""
        prefix = match.group(1)
        db_param = match.group(3)

        # Skip if admin parameter already exists
        if 'admin:' in prefix or 'admin =' in prefix:
            return match.group(0)

        # Add admin parameter before db
        return f"{prefix}admin: Admin = Depends(get_current_admin), {db_param}"

    content = re.sub(pattern, add_admin_param, content)

    if content != original:
        path.write_text(content, encoding='utf-8')
        print(f"[OK] Updated: {filepath}")
    else:
        print(f"[OK] No changes needed: {filepath}")


if __name__ == "__main__":
    print("Adding admin authentication to admin endpoints...")
    print()

    for filepath in FILES_TO_UPDATE:
        add_admin_auth_to_file(filepath)

    print()
    print("[DONE] Admin authentication added to all endpoints.")
    print()
    print("[NOTE] Some endpoints may need manual review if they have")
    print("       non-standard parameter patterns.")
