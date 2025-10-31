#!/usr/bin/env python3
"""
Test script for PPT Agent functionality
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from agents.ppt_generator_agent import PPTContentGenerator
from utils.ppt_creator import PPTCreator
from crewAI.ppt_crew import PPTCrew

def test_ppt_content_generator():
    """Test the PPT content generator"""
    print("🧪 Testing PPT Content Generator...")
    
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
    
    print(f"✅ Generated presentation: {result.get('presentation_title', 'Unknown')}")
    print(f"📊 Number of slides: {len(result.get('slides', []))}")
    
    return result

def test_ppt_creator():
    """Test the PPT file creator"""
    print("\n🧪 Testing PPT File Creator...")
    
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
    print(f"✅ Created PPT file: {file_path}")
    
    # Get file info
    info = creator.get_presentation_info(file_path)
    print(f"📊 File info: {info}")
    
    return file_path

def test_ppt_crew():
    """Test the PPT Crew integration"""
    print("\n🧪 Testing PPT Crew Integration...")
    
    crew = PPTCrew()
    
    # Test topic-based generation
    topic = "Cell Division"
    content = """
    Cell division is the process by which a parent cell divides into two or more daughter cells.
    There are two main types:
    1. Mitosis - produces identical diploid cells for growth and repair
    2. Meiosis - produces haploid gametes for reproduction
    
    The cell cycle consists of interphase (G1, S, G2) and mitotic phase (mitosis and cytokinesis).
    """
    
    result = crew.generate_presentation_from_topic(topic, content, num_slides=5)
    
    if result["success"]:
        print(f"✅ Generated presentation successfully!")
        print(f"📁 File: {result['file_path']}")
        print(f"📊 Info: {result['presentation_info']}")
    else:
        print(f"❌ Error: {result['error']}")
    
    return result

def main():
    """Run all tests"""
    print("🚀 Starting PPT Agent Tests...\n")
    
    try:
        # Test 1: Content Generator
        content_data = test_ppt_content_generator()
        
        # Test 2: PPT Creator
        file_path = test_ppt_creator()
        
        # Test 3: PPT Crew
        crew_result = test_ppt_crew()
        
        print("\n🎉 All tests completed!")
        print(f"📁 Test files created in: {os.path.dirname(file_path)}")
        
        # List all presentations
        crew = PPTCrew()
        presentations = crew.list_presentations()
        print(f"\n📋 Total presentations: {len(presentations)}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

