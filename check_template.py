import os
import shutil
from pathlib import Path

def check_template_status():
    template_dir = Path("backend/storage/templates")
    template_path = template_dir / "template.pptx"
    
    if not template_path.exists():
        print(f"❌ No template found at {template_path}")
        print("Please place your 'template.pptx' in this folder.")
        return

    print(f"✅ Template found at: {template_path}")
    print(f"Size: {template_path.stat().st_size} bytes")
    print(f"Last Modified: {template_path.stat().st_mtime}")
    
    # Check if it looks like the mock template (small size usually)
    if template_path.stat().st_size < 40000: # Mock is around 30KB
        print("⚠️ Warning: This file size suggests it might still be the test template.")
        print("If you have your own branded template, please overwrite this file.")

if __name__ == "__main__":
    check_template_status()
