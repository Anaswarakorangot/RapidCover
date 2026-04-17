#!/usr/bin/env python3
"""
Fix all admin panel components to use authenticated fetch.
Adds import and replaces direct fetch calls with authenticatedFetch.
"""

import re
from pathlib import Path

ADMIN_COMPONENTS_DIR = Path("frontend/src/components/admin")

def fix_component(filepath):
    """Add authenticatedFetch import and update fetch calls."""
    content = filepath.read_text(encoding='utf-8')
    original = content

    # Skip if already using authenticatedFetch
    if 'authenticatedFetch' in content:
        print(f"[SKIP] {filepath.name} - already using authenticatedFetch")
        return False

    # Skip if no fetch calls
    if 'await fetch(' not in content:
        print(f"[SKIP] {filepath.name} - no fetch calls")
        return False

    # Add import if not present
    if "import { authenticatedFetch }" not in content:
        # Find the last import statement
        import_pattern = r"(import .+ from .+;)"
        imports = list(re.finditer(import_pattern, content))
        if imports:
            last_import = imports[-1]
            insert_pos = last_import.end()
            content = (
                content[:insert_pos] +
                "\nimport { authenticatedFetch } from '../../services/adminApi';" +
                content[insert_pos:]
            )

    # Replace fetch calls
    # Pattern: await fetch(`${API_BASE}/path`)
    # Replace with: await authenticatedFetch(`${API_BASE}/path`)
    content = re.sub(
        r'await fetch\((`\$\{API_BASE\}[^`]+`)\)',
        r'await authenticatedFetch(\1)',
        content
    )

    # Pattern: const res = await fetch(url); followed by res.json()
    # Replace with direct authenticatedFetch call
    content = re.sub(
        r'const res = await authenticatedFetch\(([^)]+)\);\s+if \(!res\.ok\) \{\s+throw new Error\([^)]+\);\s+\}\s+const data = await res\.json\(\);',
        r'const data = await authenticatedFetch(\1);',
        content,
        flags=re.DOTALL
    )

    if content != original:
        filepath.write_text(content, encoding='utf-8')
        print(f"[OK] Fixed: {filepath.name}")
        return True
    else:
        print(f"[NO CHANGE] {filepath.name}")
        return False

if __name__ == "__main__":
    print("Fixing admin panel components to use authenticated fetch...")
    print()

    components = list(ADMIN_COMPONENTS_DIR.glob("*.jsx"))
    fixed_count = 0

    for component in components:
        if fix_component(component):
            fixed_count += 1

    print()
    print(f"[DONE] Fixed {fixed_count}/{len(components)} components")
