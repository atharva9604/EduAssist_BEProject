#!/usr/bin/env python3
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def verify_prompt_construction():
    """Verify the prompt constructed by PPTContentGenerator"""
    print("Verifying PPT Prompt Construction...")
    
    # Mock ModelManager before importing PPTContentGenerator to avoid __init__ error
    with patch('utils.model_manager.ModelManager') as MockModelManager:
        # Check if we can bypass the __init__ check or if we need to mock the instance
        mock_instance = MockModelManager.return_value
        mock_instance.gemini_api_key = "test_key" # Fake key to pass init
        
        from agents.ppt_generator_agent import PPTContentGenerator
        
        generator = PPTContentGenerator()
        
        # Patch generate_content to capture the prompt - return enough items to avoid retry
        generator.model_manager.generate_content = MagicMock(return_value='{"content": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8"]}')
        
        # Test Parameters
        title = "Projectile Motion Equations"
        topic = "Kinematics"
        subject = "Physics"
        
        print(f"\n--- Generating content for: {title} ---")
        generator._generate_single_slide_content(1, title, topic, subject, "", "gemini")
        
        # Get the call args
        args, _ = generator.model_manager.generate_content.call_args
        prompt_sent = args[0]
        
        print("\n--- CAPTURED PROMPT ---")
        # Write to file for full inspection
        with open("prompt_debug.txt", "w", encoding="utf-8") as f:
            f.write(prompt_sent)
        print("Prompt written to prompt_debug.txt")
        print("\n-----------------------")
        
        # Verification Checks
        checks = {
            "Senior Academic Role": "SENIOR ACADEMIC PPT GENERATOR" in prompt_sent,
            "Target Word Count": "5-12 words long" in prompt_sent,
            "Math Instruction": "include relevant formulas/equations" in prompt_sent,
            "No Latex": "Do NOT use LaTeX format" in prompt_sent,
            "Teachable Bullets": "teachable bullet points" in prompt_sent
        }
        
        all_passed = True
        for name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
            if not passed:
                all_passed = False
                
        if all_passed:
            print("\n✅ Verification Successful: Prompt contains all required elements.")
        else:
            print("\n❌ Verification Failed: Some elements are missing.")

if __name__ == "__main__":
    verify_prompt_construction()
