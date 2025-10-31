#!/usr/bin/env python3
"""
Simple test for PPT Agent functionality without CrewAI
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_ppt_content_generator():
    """Test the PPT content generator without CrewAI"""
    print("Testing PPT Content Generator...")
    
    try:
        from agents.ppt_generator_agent import PPTContentGenerator
        
        generator = PPTContentGenerator()
        
        # Test with sample content
        topic = "Photosynthesis"
        content = """
        Photosynthesis is the process by which plants convert light energy into chemical energy.
        It occurs in the chloroplasts of plant cells and involves two main stages:
        1. Light-dependent reactions - capture light energy and convert it to ATP and NADPH
        2. Light-independent reactions (Calvin cycle) - use ATP and NADPH to convert CO2 into glucose
        
        The overall equation is: 6CO2 + 6H2O + light energy → C6H12O6 + 6O2
        This process is essential for life on Earth as it produces oxygen and organic compounds.
        """
        
        result = generator.generate_slide_content(topic, content, num_slides=6)
        
        print(f"Generated presentation: {result.get('presentation_title', 'Unknown')}")
        print(f"Number of slides: {len(result.get('slides', []))}")
        
        return result
        
    except Exception as e:
        print(f"Error testing content generator: {e}")
        return None

def test_ppt_creator():
    """Test the PPT file creator"""
    print("\nTesting PPT File Creator...")
    
    try:
        from utils.ppt_creator import PPTCreator
        
        creator = PPTCreator()
        
        # Sample content data
        content_data = {
            "presentation_title": "Introduction to Photosynthesis",
            "presentation_subtitle": "Educational Presentation",
            "slides": [
                {
                    "slide_number": 1,
                    "slide_type": "title",
                    "title": "Introduction to Photosynthesis",
                    "content": ["Understanding the process of photosynthesis"],
                    "visual_suggestion": "Title slide with plant image"
                },
                {
                    "slide_number": 2,
                    "slide_type": "content",
                    "title": "What is Photosynthesis?",
                    "content": [
                        "Process by which plants convert light energy to chemical energy",
                        "Occurs in chloroplasts of plant cells",
                        "Essential for life on Earth"
                    ],
                    "visual_suggestion": "Diagram of plant cell with chloroplasts"
                },
                {
                    "slide_number": 3,
                    "slide_type": "content",
                    "title": "The Photosynthesis Equation",
                    "content": [
                        "6CO2 + 6H2O + light energy → C6H12O6 + 6O2",
                        "Carbon dioxide + Water + Light → Glucose + Oxygen"
                    ],
                    "visual_suggestion": "Chemical equation diagram"
                },
                {
                    "slide_number": 4,
                    "slide_type": "summary",
                    "title": "Key Takeaways",
                    "content": [
                        "Photosynthesis is vital for life on Earth",
                        "It produces oxygen and organic compounds",
                        "Understanding this process helps us appreciate nature"
                    ],
                    "visual_suggestion": "Summary infographic"
                }
            ]
        }
        
        file_path = creator.create_presentation(content_data, "test_presentation.pptx")
        print(f"Created PPT file: {file_path}")
        
        # Get file info
        info = creator.get_presentation_info(file_path)
        print(f"File info: {info}")
        
        return file_path
        
    except Exception as e:
        print(f"Error testing PPT creator: {e}")
        return None

def main():
    """Run all tests"""
    print("Starting Simple PPT Agent Tests...\n")
    
    try:
        # Test 1: Content Generator (without CrewAI)
        print("Note: Skipping CrewAI-dependent tests for now...")
        
        # Test 2: PPT Creator
        file_path = test_ppt_creator()
        
        if file_path:
            print("\nPPT Creator test completed successfully!")
            print(f"Test file created: {file_path}")
            
            # List all presentations
            try:
                from utils.ppt_creator import PPTCreator
                creator = PPTCreator()
                presentations = creator.list_presentations()
                print(f"\nTotal presentations: {len(presentations)}")
            except Exception as e:
                print(f"Note: Could not list presentations: {e}")
        else:
            print("\nPPT Creator test failed")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
