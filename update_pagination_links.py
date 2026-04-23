import os
import re

TEMPLATES_DIR = 'templates'

for filename in os.listdir(TEMPLATES_DIR):
    if filename.startswith('admin_') and filename.endswith('.html'):
        filepath = os.path.join(TEMPLATES_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Regex to find url_for('admin_xxx', ...) that doesn't already have search=
        # We look for: url_for('admin_[^']+', [^)]+)
        # We need to insert `search=request.args.get('search', '')` before the closing parenthesis.
        # But wait, what about url_for('admin_update_...)? We only want to add it to pagination/search links.
        # It's safer to only append `search=request.args.get('search', '')` if the url_for has `page=` or `_page=`.
        
        def replacer(match):
            full_match = match.group(0)
            if 'search=' in full_match:
                return full_match
            if 'page=' in full_match or '_page=' in full_match:
                # Add search
                return full_match.replace(')', ", search=request.args.get('search', ''))")
            return full_match

        new_content = re.sub(r"url_for\('admin_[^']+',[^)]+\)", replacer, content)

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated search param in {filename}")
