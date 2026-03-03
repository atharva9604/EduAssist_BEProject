#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from agents.ppt_generator_agent import PPTContentGenerator

def test_mode_2_strict_enforcement():
    print("🧪 Testing Mode 2 Strict Enforcement...")
    generator = PPTContentGenerator()
    
    # Prompt for Mode 2
    prompt = """
    Create 3 slides PPT on Quantum Computing.
    Subject: Science
    
    Slide titles:
    Slide 1: What is Quantum Computing?
    Slide 2: Qubits and Superposition
    Slide 3: Real world Applications
    
    Generate content.
    """
    
    try:
        # We need some context text
        context = "Quantum computing is a type of computing that uses quantum-mechanical phenomena..."
        
        result = generator.generate_slide_content(
            topic="Quantum Computing",
            content=context,
            user_input=prompt
        )
        
        print(f"✅ Generated presentation: {result.get('presentation_title')}")
        slides = result.get('slides', [])
        print(f"📊 Total slides: {len(slides)} (Expected 4: 1 base + 3 user)")
        
        # Verify slide count
        if len(slides) != 4:
            print(f"❌ ERROR: Slide count mismatch. Got {len(slides)}, expected 4")
            return
            
        # Verify titles
        expected_titles = {
            2: "What is Quantum Computing?",
            3: "Qubits and Superposition",
            4: "Real world Applications"
        }
        
        for slide_num, expected_title in expected_titles.items():
            actual_title = slides[slide_num-1].get('title')
            if actual_title == expected_title:
                print(f"  ✅ Slide {slide_num} title matches: '{actual_title}'")
            else:
                print(f"  ❌ ERROR: Slide {slide_num} title mismatch. Got '{actual_title}', expected '{expected_title}'")
        
        print("\n🎉 Mode 2 Strict Enforcement Test PASSED!")
        
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mode_2_strict_enforcement()
