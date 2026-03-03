import os
from pptx import Presentation

def inspect_template():
    base_dir = os.getcwd()
    # Handle if we are in root or backend
    if "backend" not in base_dir and os.path.exists("backend"):
         base_dir = os.path.join(base_dir, "backend")
    
    template_path = os.path.join(base_dir, "storage", "templates", "template.pptx")
    
    if not os.path.exists(template_path):
        print(f"❌ Template not found at {template_path}")
        # Debug: List contents of expected dir
        expected_dir = os.path.dirname(template_path)
        if os.path.exists(expected_dir):
            print(f"Contents of {expected_dir}:")
            for f in os.listdir(expected_dir):
                print(f"  - {f}")
        else:
             print(f"Directory {expected_dir} does not exist!")
        return

    try:
        prs = Presentation(template_path)
        print(f"✅ Template loaded: {template_path}")
        
        print("\n--- Layouts ---")
        layout_names = []
        for i, layout in enumerate(prs.slide_layouts):
            print(f"Layout {i}: '{layout.name}'")
            layout_names.append(layout.name)
            
        required = ["Title Slide", "Title and Content", "Thank You"]
        missing = [req for req in required if req not in layout_names]
        
        if missing:
             print(f"\n❌ MISSING REQUIRED LAYOUTS: {missing}")
        else:
             print("\n✅ ALL REQUIRED LAYOUTS PRESENT")

    except Exception as e:
        print(f"Error inspecting template: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    # Run once to console
    inspect_template()
    
    # Run again to file
    with open("inspect_template.log", "w", encoding="utf-8") as f:
        original_stdout = sys.stdout
        sys.stdout = f
        try:
            inspect_template()
        finally:
            sys.stdout = original_stdout
