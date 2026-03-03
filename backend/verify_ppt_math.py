#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import json

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

def verify_math_content():
    """Verify that the PPT generator produces academic content with formulas"""
    print("Verifying PPT Content Generator Math Capabilities...")
    
    try:
        from agents.ppt_generator_agent import PPTContentGenerator
        
        generator = PPTContentGenerator()
        
        # Test Case 1: Physics Topic
        title = "Projectile Motion Equations"
        topic = "Kinematics in Physics"
        subject = "Physics"
        
        print(f"\n--- TEST CASE 1: {title} ({subject}) ---")
        bullets = generator._generate_single_slide_content(
            slide_num=1,
            title=title,
            topic=topic,
            subject=subject,
            context="",
            model_type=generator.default_model
        )
        
        print(f"Generated {len(bullets)} bullets:")
        has_formula = False
        for i, bullet in enumerate(bullets):
            print(f"{i+1}. {bullet}")
            # Simple check for math symbols
            if any(x in bullet for x in ['=', '^', 'θ', '+', 'v0', '1/2', 'gt']):
                has_formula = True
                
        if has_formula:
            print("\n✅ FORMULA DETECTED in output.")
        else:
            print("\n❌ NO FORMULA DETECTED. Check prompt.")
            
        # Test Case 2: Conciseness Check
        print("\n--- TEST CASE 2: Conciseness Check ---")
        long_bullets = [b for b in bullets if len(b.split()) > 15] # Allow a bit of leeway, but aim for 5-12
        if not long_bullets:
             print("✅ All bullets are concise.")
        else:
             print(f"⚠️ Found {len(long_bullets)} long bullets:")
             for b in long_bullets:
                 print(f"   - ({len(b.split())} words): {b}")

    except Exception as e:
        print(f"Error running verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_math_content()
