import os
import json
import re
from dotenv import load_dotenv
from typing import Dict, List, Optional, Literal, Tuple
from pydantic import BaseModel, Field
import sys
from pathlib import Path

# CrewAI imports for agent/task exports
try:
    from crewai import Agent, Task
except ImportError:
    Agent = None
    Task = None

load_dotenv()

# Add utils to path for model_manager import
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from utils.model_manager import ModelManager, ModelType

class PPTContentGenerator:
    """PPT Content Generator with 5 PPT Modes support"""
    
    def __init__(self):
        self.model_manager = ModelManager()
        # Pick default model based on available API keys
        if self.model_manager.gemini_api_key:
            self.default_model: ModelType = "gemini"
        elif self.model_manager.groq_api_key:
            self.default_model: ModelType = "groq_llama"
        else:
            raise RuntimeError("Neither GEMINI_API_KEY nor GROQ_API_KEY is set. Please add one to backend/.env")

    def _detect_ppt_mode(self, prompt: str) -> str:
        """
        Detect PPT mode based on EXACT prompt structure (not guessing).
        
        Priority order (most specific first):
        1. Mode 3: "Use EXACT content" + "Do NOT modify" + "Content:" sections
        2. Mode 5: "Slide instructions:" section
        3. Mode 4: "Image placement:" section
        4. Mode 2: "Slide titles:" section OR "Slide structure:" section
        5. Mode 1: "Use a default slide structure" or "Generate all slide titles"
        """
        if not prompt:
            print(f"⚠️  _detect_ppt_mode: prompt is None or empty")
            return "mode_1"  # Default to Mode 1
        
        prompt_str = str(prompt)
        prompt_lower = prompt_str.lower()
        
        print(f"🔍 _detect_ppt_mode: Checking prompt (length: {len(prompt_str)})")
        
        # MODE 3: Exact Content (STRICT) - Highest priority
        has_exact_marker = "use exact content" in prompt_lower or "exact content" in prompt_lower
        has_no_modify = "do not modify" in prompt_lower or "don't modify" in prompt_lower
        has_content_sections = "content:" in prompt_lower or re.search(r'slide\s+\d+.*?content:', prompt_lower, re.IGNORECASE | re.DOTALL)
        
        if has_exact_marker and has_no_modify and has_content_sections:
            print(f"✅ MODE 3 DETECTED: Exact Content (STRICT)")
            return "mode_3"
        
        # MODE 5: Mixed/Advanced - "Slide instructions:" section
        if "slide instructions:" in prompt_lower:
            print(f"✅ MODE 5 DETECTED: Mixed/Advanced")
            return "mode_5"
        
        # MODE 4: Image-Controlled - "Image placement:" section (check BEFORE Mode 2)
        # Mode 4 has both "Slide structure:" AND "Image placement:", so check for Image placement first
        if "image placement:" in prompt_lower:
            print(f"✅ MODE 4 DETECTED: Image-Controlled (found 'Image placement:')")
            return "mode_4"
        
        # MODE 2: Custom Slide Titles - "Slide titles:" OR "Slide structure:" section
        # Only if NOT Mode 4 (Mode 4 also has "Slide structure:" but has "Image placement:" too)
        if re.search(r'slide\s+titles?\s*:', prompt_lower) or "slide structure:" in prompt_lower:
            print(f"✅ MODE 2 DETECTED: Custom Slide Titles (has 'Slide titles:' or 'Slide structure:')")
            return "mode_2"
        
        # MODE 1: Quick Auto PPT - "Use a default slide structure" or "Generate all slide titles"
        has_default_structure = "default slide structure" in prompt_lower or "use a default" in prompt_lower
        has_generate_all = "generate all slide titles" in prompt_lower or "generate all content yourself" in prompt_lower
        
        if has_default_structure or has_generate_all:
            print(f"✅ MODE 1 DETECTED: Quick Auto PPT")
            return "mode_1"
        
        # Fallback: If no clear mode, default to Mode 1
        print(f"⚠️  No clear mode detected, defaulting to Mode 1 (Quick Auto)")
        print(f"   Prompt preview: {prompt_str[:200]}")
        return "mode_1"
    
    def _parse_mode_1(self, prompt: str) -> Dict:
        """
        Parse Mode 1: Auto PPT (Fully Generated)
        
        Extract: NUMBER, TOPIC, SUBJECT
        Generate: Everything (titles, content, images)
        """
        print(f"🔍 MODE 1 PARSER: Starting extraction...")
        
        # Extract NUMBER
        number_match = re.search(r'(\d+)[-\s]slide', prompt, re.IGNORECASE)
        if not number_match:
            number_match = re.search(r'create\s+(\d+)\s+slides?', prompt, re.IGNORECASE)
        if not number_match:
            number_match = re.search(r'(\d+)\s+slides?', prompt, re.IGNORECASE)
        number = int(number_match.group(1)) if number_match else 8
        
        # Extract TOPIC
        topic_match = re.search(r'ppt\s+on\s+([^.]+?)(?:\.|Subject:)', prompt, re.IGNORECASE)
        if not topic_match:
            topic_match = re.search(r'on\s+([^.]+?)(?:\.|Subject:)', prompt, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else "General Topic"
        
        # Extract SUBJECT
        subject_match = re.search(r'Subject:\s*([^\n]+)', prompt, re.IGNORECASE)
        subject = subject_match.group(1).strip() if subject_match else "General"
        
        print(f"  ✓ Extracted: NUMBER={number}, TOPIC='{topic}', SUBJECT='{subject}'")
        
        return {
            'mode': 'mode_1',
            'number': number,
            'topic': topic,
            'subject': subject,
            'slide_titles': None,  # Will be generated
            'exact_content': None,
            'image_mappings': None
        }
    
    def _parse_mode_2(self, prompt: str) -> Dict:
        """
        Parse Mode 2: Custom Slide Titles
        
        Extract: NUMBER, TOPIC, SUBJECT, EXACT slide titles
        Generate: Content only (8-10 bullets per slide)
        """
        print(f"🔍 MODE 2 PARSER: Starting extraction...")
        
        # Extract NUMBER
        number_match = re.search(r'(\d+)[-\s]slide', prompt, re.IGNORECASE)
        if not number_match:
            number_match = re.search(r'create\s+(\d+)\s+slides?', prompt, re.IGNORECASE)
        if not number_match:
            number_match = re.search(r'(\d+)\s+slides?', prompt, re.IGNORECASE)
        number = int(number_match.group(1)) if number_match else 8
        
        # Extract TOPIC
        topic_match = re.search(r'ppt\s+on\s+([^.]+?)(?:\.|Subject:)', prompt, re.IGNORECASE)
        if not topic_match:
            topic_match = re.search(r'on\s+([^.]+?)(?:\.|Subject:)', prompt, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else "General Topic"
        
        # Extract SUBJECT
        subject_match = re.search(r'Subject:\s*([^\n]+)', prompt, re.IGNORECASE)
        subject = subject_match.group(1).strip() if subject_match else "General"
        
        # CRITICAL: Extract slide titles - EXACT extraction (user titles are LAW)
        slide_titles = []
        
        print(f"  🔍 Searching for 'Slide titles:' in prompt (length: {len(prompt)})")
        
        # MODE_2_TITLE_PATTERN: Match "Slide X: TITLE" format
        MODE_2_TITLE_PATTERN = r"Slide\s+(\d+)\s*:\s*(.+)"
        
        # Strategy 1: Find "Slide titles:" section first
        titles_section = None
        titles_start_match = re.search(r'Slide\s+titles?:\s*', prompt, re.IGNORECASE)
        if titles_start_match:
            print(f"  ✓ Found 'Slide titles:' at index {titles_start_match.start()}")
            # Get everything after "Slide titles:" until we hit "Generate" or end of prompt
            remaining = prompt[titles_start_match.end():]
            # Find where the titles section ends (look for "Generate" or end)
            end_match = re.search(r'(?:Generate\s+content|Generate\s+|$)', remaining, re.IGNORECASE)
            if end_match:
                titles_section = remaining[:end_match.start()].strip()
            else:
                titles_section = remaining.strip()
            print(f"  🔍 Titles section length: {len(titles_section)}, preview: {titles_section[:200]}")
        
        # Extract titles from the section
        if titles_section:
            matches = re.finditer(MODE_2_TITLE_PATTERN, titles_section, re.IGNORECASE)
            for match in matches:
                slide_num = int(match.group(1))
                title = match.group(2).strip()
                # CRITICAL: Use title EXACTLY as provided - only remove trailing whitespace
                title = title.rstrip()  # Only remove trailing whitespace
                if title:  # Only add if title is not empty
                    slide_titles.append({'slide_number': slide_num, 'title': title})
                    print(f"  ✓ Extracted title for Slide {slide_num}: '{title}'")
        
        # Strategy 2: If no titles found, search entire prompt for "Slide X: TITLE" patterns
        if not slide_titles:
            print(f"  🔍 No titles found in 'Slide titles:' section, searching entire prompt...")
            matches = re.finditer(MODE_2_TITLE_PATTERN, prompt, re.IGNORECASE)
            for match in matches:
                slide_num = int(match.group(1))
                title = match.group(2).strip()
                # Skip if it's part of "Slide titles:" header itself
                if 'titles' not in title.lower() and 'structure' not in title.lower():
                    title = title.rstrip()  # Only remove trailing whitespace
                    if title:  # Only add if title is not empty
                        slide_titles.append({'slide_number': slide_num, 'title': title})
                        print(f"  ✓ Found title for Slide {slide_num}: '{title}'")
        
        # Sort by slide number
        slide_titles.sort(key=lambda x: x['slide_number'])
        
        # Remove duplicates (keep first occurrence)
        seen = set()
        unique_titles = []
        for t in slide_titles:
            if t['slide_number'] not in seen:
                seen.add(t['slide_number'])
                unique_titles.append(t)
        slide_titles = unique_titles
        
        # CRITICAL: Determine actual number from extracted titles
        if slide_titles:
            max_slide_num = max(t['slide_number'] for t in slide_titles)
            # Update number to match extracted titles
            number = max(number, max_slide_num)
            
            # CRITICAL VALIDATION: Must have exactly 'number' titles
            if len(slide_titles) != number:
                print(f"  ⚠ WARNING: Extracted {len(slide_titles)} titles but {number} slides requested")
                print(f"  Extracted slide numbers: {[t['slide_number'] for t in slide_titles]}")
                # For Mode 2, this is an error - user titles are LAW
                if len(slide_titles) < number:
                    raise ValueError(f"Mode 2 requires exactly {number} slide titles. Only found {len(slide_titles)} titles. Please provide all {number} titles in 'Slide titles:' section.")
                # If we have more titles, trim to requested number
                if len(slide_titles) > number:
                    print(f"  ⚠ WARNING: Found {len(slide_titles)} titles, trimming to {number} as requested")
                    slide_titles = [t for t in slide_titles if t['slide_number'] <= number]
        
        # CRITICAL: If no titles found, this is an error for Mode 2
        if not slide_titles:
            print(f"  ❌ ERROR: No slide titles extracted from 'Slide titles:' section")
            print(f"  Prompt preview: {prompt[:500]}")
            raise ValueError("Mode 2 requires slide titles in 'Slide titles:' section. No titles were found. Please use the format: 'Slide titles: Slide 1: {TITLE} Slide 2: {TITLE} ...'")
        
        print(f"  ✅ Mode 2: Extracted {len(slide_titles)} titles:")
        for t in slide_titles:
            print(f"    - Slide {t['slide_number']}: '{t['title']}'")
        print(f"  ✓ Extracted: NUMBER={number}, TOPIC='{topic}', SUBJECT='{subject}'")
        
        return {
            'mode': 'mode_2',
            'number': number,
            'topic': topic,
            'subject': subject,
            'slide_titles': slide_titles,
            'exact_content': None,
            'image_mappings': None
        }
    
    def _parse_mode_3(self, prompt: str) -> Dict:
        """
        Parse Mode 3: Exact Content (STRICT MODE)
        
        Extract: NUMBER, TOPIC, SUBJECT, EXACT titles, EXACT bullets
        Generate: NOTHING (use exact content)
        """
        print(f"🔍 MODE 3 PARSER: Starting extraction...")
        
        # Extract NUMBER
        number_match = re.search(r'(\d+)[-\s]slide', prompt, re.IGNORECASE)
        if not number_match:
            number_match = re.search(r'create\s+(\d+)\s+slides?', prompt, re.IGNORECASE)
        if not number_match:
            number_match = re.search(r'(\d+)\s+slides?', prompt, re.IGNORECASE)
        number = int(number_match.group(1)) if number_match else 8
        
        # Extract TOPIC
        topic_match = re.search(r'ppt\s+on\s+([^.]+?)(?:\.|Subject:)', prompt, re.IGNORECASE)
        if not topic_match:
            topic_match = re.search(r'on\s+([^.]+?)(?:\.|Subject:)', prompt, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else "General Topic"
        
        # Extract SUBJECT
        subject_match = re.search(r'Subject:\s*([^\n]+)', prompt, re.IGNORECASE)
        subject = subject_match.group(1).strip() if subject_match else "General"
        
        # Extract exact content
        exact_content = []
        
        # Find all "Slide X:" occurrences
        slide_pattern = r'Slide\s+(\d+):'
        slide_matches = list(re.finditer(slide_pattern, prompt, re.IGNORECASE))
        
        for idx, match in enumerate(slide_matches):
            slide_num = int(match.group(1))
            slide_start = match.end()
            
            # Find where this slide section ends (next "Slide X:" or end of prompt)
            if idx + 1 < len(slide_matches):
                slide_end = slide_matches[idx + 1].start()
            else:
                slide_end = len(prompt)
            
            slide_text = prompt[slide_start:slide_end]
            
            # Extract title - look for "Title: ..." on same line or next line
            title_match = re.search(r'Title:\s*([^\n]+)', slide_text, re.IGNORECASE)
            if not title_match:
                print(f"  ⚠ Could not find title for Slide {slide_num}")
                continue
            
            title = title_match.group(1).strip()
            
            # Extract content section - find "Content:" and get everything until next "Slide" or end
            content_match = re.search(r'Content:\s*(.*?)(?=\n\s*Slide\s+\d+:|$)', slide_text, re.IGNORECASE | re.DOTALL)
            if not content_match:
                print(f"  ⚠ Could not find content for Slide {slide_num}")
                continue
            
            content_text = content_match.group(1)
            
            # Extract bullets/content lines - handle blank lines between content
            bullets = []
            if content_text:
                # Split by newlines
                lines = content_text.split('\n')
                for line in lines:
                    line = line.strip()
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Handle bullet format (starts with -)
                    if line.startswith('-'):
                        bullet = line.lstrip('-').strip()
                        if bullet:
                            bullets.append(bullet)
                    # Handle plain text format (no bullet prefix)
                    else:
                        # Add non-empty lines as-is (exact content)
                        if line and not line.isspace():
                            bullets.append(line)
            
            if bullets:
                exact_content.append({
                    'slide_number': slide_num,
                    'title': title,
                    'content': bullets
                })
                print(f"  ✓ Extracted Slide {slide_num}: '{title}' with {len(bullets)} content lines")
            else:
                print(f"  ⚠ Slide {slide_num} has no content lines")
        
        # Sort by slide number
        exact_content.sort(key=lambda x: x['slide_number'])
        
        # Determine actual number from extracted slides
        if exact_content:
            number = max(number, max(s['slide_number'] for s in exact_content))
        
        print(f"  ✓ Extracted: NUMBER={number}, TOPIC='{topic}', SUBJECT='{subject}'")
        print(f"  ✓ Extracted {len(exact_content)} slides with exact content:")
        for s in exact_content:
            print(f"    - Slide {s['slide_number']}: '{s['title']}' ({len(s['content'])} bullets/content lines)")
        
        if not exact_content:
            print(f"  ⚠ WARNING: No exact content extracted from prompt!")
        
        return {
            'mode': 'mode_3',
            'number': number,
            'topic': topic,
            'subject': subject,
            'slide_titles': None,
            'exact_content': exact_content,
            'image_mappings': None
        }
    
    def _parse_mode_4(self, prompt: str) -> Dict:
        """
        Parse Mode 4: Image-Controlled PPT
        
        Extract: NUMBER, TOPIC, SUBJECT, slide titles, image-to-slide mappings
        Generate: Content (8-10 bullets per slide)
        """
        print(f"🔍 MODE 4 PARSER: Starting extraction...")
        
        # Extract NUMBER
        number_match = re.search(r'(\d+)[-\s]slide', prompt, re.IGNORECASE)
        if not number_match:
            number_match = re.search(r'create\s+(\d+)\s+slides?', prompt, re.IGNORECASE)
        if not number_match:
            number_match = re.search(r'(\d+)\s+slides?', prompt, re.IGNORECASE)
        number = int(number_match.group(1)) if number_match else 8
        
        # Extract TOPIC
        topic_match = re.search(r'ppt\s+on\s+([^.]+?)(?:\.|Subject:)', prompt, re.IGNORECASE)
        if not topic_match:
            topic_match = re.search(r'on\s+([^.]+?)(?:\.|Subject:)', prompt, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else "General Topic"
        
        # Extract SUBJECT
        subject_match = re.search(r'Subject:\s*([^\n]+)', prompt, re.IGNORECASE)
        subject = subject_match.group(1).strip() if subject_match else "General"
        
        # Extract slide titles from "Slide structure:" section
        slide_titles = []
        
        print(f"  🔍 Searching for 'Slide structure:' in prompt (length: {len(prompt)})")
        
        # Try to find "Slide structure:" section
        structure_patterns = [
            r'Slide\s+structure:\s*(.*?)(?:\n\nImage\s+placement:|Image\s+placement:|$)',
            r'Slide\s+structure:\s*(.*?)(?:Image\s+placement:|$)',
            r'Slide\s+structure:\s*(.*?)(?:\nImage\s+placement:|Image\s+placement:|$)',
        ]
        
        structure_section = None
        for pattern in structure_patterns:
            structure_section = re.search(pattern, prompt, re.IGNORECASE | re.DOTALL)
            if structure_section:
                print(f"  ✓ Found 'Slide structure:' section using pattern")
                break
        
        if structure_section:
            titles_text = structure_section.group(1)
            title_pattern = r'Slide\s+(\d+):\s*([^\n]+)'
            matches = list(re.finditer(title_pattern, titles_text, re.IGNORECASE))
            
            for match in matches:
                slide_num = int(match.group(1))
                title = match.group(2).strip()
                title = title.rstrip()  # Only remove trailing whitespace
                if title:  # Only add if title is not empty
                    slide_titles.append({'slide_number': slide_num, 'title': title})
                    print(f"  ✓ Extracted title for Slide {slide_num}: '{title}'")
        
        # Fallback to "Slide titles:"
        if not slide_titles:
            titles_section = re.search(r'Slide\s+titles?:\s*(.*?)(?:\n\nImage\s+placement:|Image\s+placement:|$)', prompt, re.IGNORECASE | re.DOTALL)
            if titles_section:
                titles_text = titles_section.group(1)
                title_pattern = r'Slide\s+(\d+):\s*([^\n]+)'
                matches = re.finditer(title_pattern, titles_text, re.IGNORECASE)
                for match in matches:
                    slide_num = int(match.group(1))
                    title = match.group(2).strip()
                    title = title.rstrip()
                    if title:
                        slide_titles.append({'slide_number': slide_num, 'title': title})
        
        slide_titles.sort(key=lambda x: x['slide_number'])
        
        # Remove duplicates
        seen = set()
        unique_titles = []
        for t in slide_titles:
            if t['slide_number'] not in seen:
                seen.add(t['slide_number'])
                unique_titles.append(t)
        slide_titles = unique_titles
        
        # Extract image placements
        image_mappings = []
        image_section = re.search(r'Image\s+placement:\s*(.*?)(?:\n\n|$)', prompt, re.IGNORECASE | re.DOTALL)
        if image_section:
            image_text = image_section.group(1)
            image_pattern = r'Use\s+Image\s+(\d+)\s+on\s+Slide\s+(\d+)'
            matches = re.finditer(image_pattern, image_text, re.IGNORECASE)
            for match in matches:
                image_num = int(match.group(1))
                slide_num = int(match.group(2))
                image_mappings.append({'image_number': image_num, 'slide_number': slide_num})
        
        # Determine actual number
        if slide_titles:
            number = max(number, max(t['slide_number'] for t in slide_titles))
        
        return {
            'mode': 'mode_4',
            'number': number,
            'topic': topic,
            'subject': subject,
            'slide_titles': slide_titles,
            'exact_content': None,
            'image_mappings': image_mappings
        }
    
    def _parse_mode_5(self, prompt: str) -> Dict:
        """
        Parse Mode 5: Mixed Control (Advanced)
        """
        print(f"🔍 MODE 5 PARSER: Starting extraction...")
        
        # Extract NUMBER
        number_match = re.search(r'(\d+)[-\s]slide', prompt, re.IGNORECASE)
        if not number_match:
            number_match = re.search(r'create\s+(\d+)\s+slides?', prompt, re.IGNORECASE)
        if not number_match:
            number_match = re.search(r'(\d+)\s+slides?', prompt, re.IGNORECASE)
        number = int(number_match.group(1)) if number_match else 8
        
        # Extract TOPIC
        topic_match = re.search(r'ppt\s+on\s+([^.]+?)(?:\.|Subject:)', prompt, re.IGNORECASE)
        if not topic_match:
            topic_match = re.search(r'on\s+([^.]+?)(?:\.|Subject:)', prompt, re.IGNORECASE)
        topic = topic_match.group(1).strip() if topic_match else "General Topic"
        
        # Extract SUBJECT
        subject_match = re.search(r'Subject:\s*([^\n]+)', prompt, re.IGNORECASE)
        subject = subject_match.group(1).strip() if subject_match else "General"
        
        # Extract per-slide instructions
        slide_instructions = []
        instructions_section = re.search(r'Slide\s+instructions:\s*(.*?)$', prompt, re.IGNORECASE | re.DOTALL)
        if instructions_section:
            instructions_text = instructions_section.group(1)
            
            # BLOCK-BASED PARSING
            slide_block_pattern = r'Slide\s+(\d+):'
            slide_blocks = list(re.finditer(slide_block_pattern, instructions_text, re.IGNORECASE))
            
            for idx, block_match in enumerate(slide_blocks):
                slide_num = int(block_match.group(1))
                block_start = block_match.start()
                
                if idx + 1 < len(slide_blocks):
                    block_end = slide_blocks[idx + 1].start()
                else:
                    block_end = len(instructions_text)
                
                slide_block = instructions_text[block_start:block_end]
                
                # Extract title
                title_match = re.search(r'Title:\s*([^\n]+)', slide_block, re.IGNORECASE)
                if not title_match:
                    continue
                title = title_match.group(1).strip()
                
                # Determine if generate or exact
                should_generate = "generate content" in slide_block.lower()
                exact_content = None
                
                # BLOCK-BASED EXACT CONTENT EXTRACTION
                if not should_generate and "exact content" in slide_block.lower():
                    exact_marker_idx = slide_block.lower().find("use exact content:")
                    if exact_marker_idx >= 0:
                        content_section = slide_block[exact_marker_idx + len("use exact content:"):]
                        lines = content_section.split('\n')
                        
                        bullets = []
                        for line in lines:
                            line_stripped = line.strip()
                            if re.match(r'^\s*Slide\s+\d+:', line_stripped, re.IGNORECASE):
                                break
                            if line_stripped.lower().startswith('use image') or line_stripped.lower() == 'no image':
                                break
                            if line_stripped.startswith('-') or line_stripped.startswith('•'):
                                bullet_text = line_stripped
                                if bullet_text.startswith('- '): bullet_text = bullet_text[2:].strip()
                                elif bullet_text.startswith('-'): bullet_text = bullet_text[1:].strip()
                                elif bullet_text.startswith('• '): bullet_text = bullet_text[2:].strip()
                                elif bullet_text.startswith('•'): bullet_text = bullet_text[1:].strip()
                                if bullet_text: bullets.append(bullet_text)
                        
                        if not bullets:
                            raise ValueError(f"Mode 5 EXACT content declared for Slide {slide_num} but no bullets parsed.")
                        
                        exact_content = bullets
                
                # Extract image instruction
                image_num = None
                image_mode = "QUERY"
                
                image_match = re.search(r'Use\s+Image\s+(\d+)', slide_block, re.IGNORECASE)
                if image_match:
                    image_num = int(image_match.group(1))
                    image_mode = "UPLOAD"
                elif "no image" in slide_block.lower():
                    image_mode = "NONE"
                
                slide_instructions.append({
                    'slide_number': slide_num,
                    'title': title,
                    'should_generate': should_generate,
                    'exact_content': exact_content,
                    'image_number': image_num,
                    'no_image': image_mode == "NONE",
                    'image_mode': image_mode
                })
        
        slide_instructions.sort(key=lambda x: x['slide_number'])
        
        # Determine actual number
        if slide_instructions:
            number = max(number, max(s['slide_number'] for s in slide_instructions))
        
        return {
            'mode': 'mode_5',
            'number': number,
            'topic': topic,
            'subject': subject,
            'slide_titles': None,
            'exact_content': None,
            'image_mappings': None,
            'slide_instructions': slide_instructions
        }
    
    def _generate_single_slide_content(self, slide_num: int, title: str, topic: str, subject: str, 
                                       context: str, model_type: ModelType) -> List[str]:
        """
        Generate 8-10 bullet points for a single slide.
        """
        effective_model = "groq_llama" if model_type != "gemini" else model_type
        
        prompt = f"""You are a SENIOR ACADEMIC PPT GENERATOR.
Generate 8-10 concise, teachable bullet points for a PowerPoint slide.

TOPIC: {topic}
SUBJECT: {subject}
SLIDE TITLE: {title}

CRITICAL INSTRUCTIONS:
1. **Academic Depth**: Provide in-depth content suitable for a university lecture. Avoid surface-level definitions.
2. **Concise Format**:
   - Each bullet point MUST be 5-12 words long.
   - Use a clear, direct style.
   - Avoid textbook blurbs or long sentences.
3. **Mathematical & Technical Precision**:
   - Include relevant formulas/equations if applicable.
   - Use standard text/Unicode (e.g., E = mc^2).
   - Do NOT use LaTeX.
4. **Structure**:
   - Do NOT modify the slide title.
   - Return ONLY content (bullet points).

Return ONLY JSON:
{{
    "content": ["bullet 1", "bullet 2", "bullet 3", ...]
}}
"""
        
        try:
            response = self.model_manager.generate_content(prompt, effective_model)
            
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            content = result.get("content", [])
            
            if not isinstance(content, list):
                content = []
            
            # Ensure 8-10 bullets
            if len(content) < 8:
                retry_prompt = f"""Generate 8-10 bullet points about {topic} related to "{title}".
Return JSON: {{"content": ["point 1", "point 2", ...]}}"""
                retry_response = self.model_manager.generate_content(retry_prompt, effective_model)
                try:
                    if "```json" in retry_response:
                        retry_response = retry_response.split("```json")[1].split("```")[0].strip()
                    retry_result = json.loads(retry_response)
                    content = retry_result.get("content", [])
                except:
                    pass
            
            return content[:10] if len(content) > 0 else self._generate_fallback_bullets(title, topic, subject)
            
        except Exception as e:
            print(f"⚠ Error generating content for slide {slide_num}: {e}")
            return self._generate_fallback_bullets(title, topic, subject)
    
    def _generate_fallback_bullets(self, title: str, topic: str, subject: str) -> List[str]:
        """Generate fallback bullets if LLM fails"""
        return [
            f"Key concept about {title} in the context of {topic}",
            f"Important aspect of {title} relevant to {subject}",
            f"Fundamental principle related to {title}",
            f"Practical application of {title} in {topic}",
            f"Core understanding of {title}",
            f"Essential knowledge about {title}",
            f"Significant detail regarding {title}",
            f"Critical point about {title} in {subject}"
        ]
    
    def _get_default_slide_titles(self, num_slides: int, topic: str) -> List[Dict]:
        """Generate default slide titles for Mode 1"""
        default_titles = [
            "Introduction",
            "Core Concept / Architecture",
            "Mathematical / Logical Explanation",
            "Applications / Use Cases",
            "Summary & Key Takeaways"
        ]
        
        titles = []
        for i in range(1, num_slides + 1):
            if i <= len(default_titles):
                titles.append({'slide_number': i, 'title': default_titles[i-1]})
            else:
                titles.append({'slide_number': i, 'title': f"Key Concept {i}"})
        
        return titles
    
    def generate_slide_content(self, topic: str, content: str, num_slides: int = 8, 
                               subject: Optional[str] = None, module: Optional[str] = None, 
                               model_type: Optional[ModelType] = None, 
                               user_input: Optional[str] = None) -> Dict:
        """
        Main entry point for PPT generation with mode support.
        """
        print(f"🔍 GENERATOR ENTRY | user_input={repr(user_input)[:100]}")
        
        is_mode_2_request = False
        if user_input:
            is_mode_2_request = "slide titles:" in str(user_input).lower()
        
        if is_mode_2_request and (not user_input or len(str(user_input).strip()) == 0):
            raise ValueError("Mode 2 requires user_input but received None/empty.")
        
        if user_input:
            detected_mode = self._detect_ppt_mode(user_input)
            print(f"🧠 DETECTED MODE: {detected_mode}")
            
            if detected_mode == "mode_2":
                parsed = self._parse_mode_2(user_input)
                expected_slides = parsed.get('number', 0) + 1
                result = self._generate_mode_2(parsed, content, model_type)
                if len(result.get('slides', [])) != expected_slides:
                    raise ValueError(f"Mode 2 slide count mismatch!")
                return result
            elif detected_mode == "mode_1":
                parsed = self._parse_mode_1(user_input)
                return self._generate_mode_1(parsed, content, model_type)
            elif detected_mode == "mode_3":
                parsed = self._parse_mode_3(user_input)
                return self._generate_mode_3(parsed, content, model_type)
            elif detected_mode == "mode_4":
                parsed = self._parse_mode_4(user_input)
                return self._generate_mode_4(parsed, content, model_type)
            elif detected_mode == "mode_5":
                parsed = self._parse_mode_5(user_input)
                return self._generate_mode_5(parsed, content, model_type)
        
        return self._generate_legacy(topic, content, num_slides, subject, module, model_type, user_input)
    
    def _generate_mode_1(self, parsed: Dict, context: str, model_type: Optional[ModelType]) -> Dict:
        """Generate Mode 1: Auto PPT"""
        slide_titles = self._get_default_slide_titles(parsed['number'], parsed['topic'])
        slides = []
        for title_info in slide_titles:
            slide_num = title_info['slide_number']
            title = title_info['title']
            bullets = self._generate_single_slide_content(slide_num, title, parsed['topic'], parsed['subject'], context, model_type)
            slides.append({'slide_number': slide_num + 1, 'slide_type': 'content', 'title': title, 'content': bullets, 'speaker_notes': f"Explain {title}."})
        
        slides.insert(0, {'slide_number': 1, 'slide_type': 'title', 'title': parsed['topic'], 'content': [parsed['subject'] or "Educational Presentation"], 'speaker_notes': f"Intro to {parsed['topic']}."})
        self._add_image_hints(slides[1:], parsed['topic'], parsed['subject'])
        
        return self._enforce_bullet_constraints({'presentation_title': parsed['topic'], 'presentation_subtitle': parsed['subject'] or "Educational Presentation", 'slides': slides})
    
    def _generate_mode_2(self, parsed: Dict, context: str, model_type: Optional[ModelType]) -> Dict:
        """Generate Mode 2: Custom Titles"""
        slides = []
        user_titles_dict = {t['slide_number']: t['title'] for t in parsed['slide_titles']}
        
        for title_info in parsed['slide_titles']:
            slide_num = title_info['slide_number']
            user_title = title_info['title']
            bullets = self._generate_single_slide_content(slide_num, user_title, parsed['topic'], parsed['subject'], context, model_type)
            slide = {'slide_number': slide_num + 1, 'slide_type': 'content', 'content': bullets, 'speaker_notes': f"Explain {user_title}.", 'title': user_title, 'title_locked': True}
            slides.append(slide)
        
        slides.insert(0, {'slide_number': 1, 'slide_type': 'title', 'title': parsed['topic'], 'content': [parsed['subject'] or "Educational Presentation"], 'speaker_notes': f"Intro to {parsed['topic']}."})
        result = {'presentation_title': parsed['topic'], 'presentation_subtitle': parsed['subject'] or "Educational Presentation", 'slides': slides, '_mode_2_title_pure': True}
        return self._enforce_bullet_constraints(result)

    def _generate_mode_3(self, parsed: Dict, context: str, model_type: Optional[ModelType]) -> Dict:
        """Generate Mode 3: Exact Content"""
        slides = []
        for exact_slide in parsed['exact_content']:
            slide_num = exact_slide['slide_number']
            slides.append({'slide_number': slide_num + 1, 'slide_type': 'content', 'title': exact_slide['title'], 'content': exact_slide['content'], 'speaker_notes': f"Present {exact_slide['title']}."})
        
        slides.insert(0, {'slide_number': 1, 'slide_type': 'title', 'title': parsed['topic'], 'content': [parsed['subject'] or "Educational Presentation"], 'speaker_notes': f"Intro to {parsed['topic']}."})
        return self._enforce_bullet_constraints({'presentation_title': parsed['topic'], 'presentation_subtitle': parsed['subject'] or "Educational Presentation", 'slides': slides})

    def _generate_mode_4(self, parsed: Dict, context: str, model_type: Optional[ModelType]) -> Dict:
        """Generate Mode 4: Image Controlled"""
        slides = []
        for title_info in parsed['slide_titles']:
            slide_num = title_info['slide_number']
            title = title_info['title']
            bullets = self._generate_single_slide_content(slide_num, title, parsed['topic'], parsed['subject'], context, model_type)
            slide = {'slide_number': slide_num + 1, 'slide_type': 'content', 'title': title, 'content': bullets, 'speaker_notes': f"Explain {title}."}
            for img_map in parsed['image_mappings']:
                if img_map['slide_number'] == slide_num: slide['image_number'] = img_map['image_number']
            slides.append(slide)
        
        slides.insert(0, {'slide_number': 1, 'slide_type': 'title', 'title': parsed['topic'], 'content': [parsed['subject'] or "Educational Presentation"], 'speaker_notes': ""})
        return self._enforce_bullet_constraints({'presentation_title': parsed['topic'], 'presentation_subtitle': parsed['subject'] or "Educational Presentation", 'slides': slides})

    def _generate_mode_5(self, parsed: Dict, context: str, model_type: Optional[ModelType]) -> Dict:
        """Generate Mode 5: Mixed Control"""
        slides = []
        expected_total = 1 + len(parsed['slide_instructions'])
        
        for instruction in parsed['slide_instructions']:
            slide_num = instruction['slide_number']
            title = instruction['title']
            slide = {'slide_number': slide_num + 1, 'slide_type': 'content', 'title': title, 'content': [], 'speaker_notes': ""}
            
            if instruction.get('image_mode') == "UPLOAD": slide['image_number'] = instruction['image_number']
            elif instruction.get('image_mode') == "NONE": slide['_no_image'] = True
            
            if not instruction['should_generate'] and instruction.get('exact_content'):
                slide['content'] = instruction['exact_content']
                slide['_is_exact_content'] = True
            else:
                slide['content'] = self._generate_single_slide_content(slide_num, title, parsed['topic'], parsed['subject'], context, model_type)
            slides.append(slide)
            
        slides.insert(0, {'slide_number': 1, 'slide_type': 'title', 'title': parsed['topic'], 'content': [parsed['subject'] or "Educational Presentation"], 'speaker_notes': ""})
        result = self._enforce_bullet_constraints({'presentation_title': parsed['topic'], 'presentation_subtitle': parsed['subject'] or "Educational Presentation", 'slides': slides}, _mode_5_exact_guard=True)
        return result

    def _generate_legacy(self, topic: str, content: str, num_slides: int, subject: Optional[str], module: Optional[str], model_type: Optional[ModelType], user_input: Optional[str]) -> Dict:
        """Legacy generation method"""
        if model_type is None: model_type = "groq_llama"
        prompt = f"Generate {num_slides} PowerPoint slides about '{topic}'. JSON: {{\"slides\": [{{\"slide_number\": 1, \"title\": \"...\", \"content\": [...]}}]}}"
        try:
            res = self.model_manager.generate_content(prompt, model_type)
            if "```json" in res: res = res.split("```json")[1].split("```")[0].strip()
            parsed = json.loads(res)
            slides = parsed.get("slides", [])
            for s in slides: s["slide_number"] = s.get("slide_number", 0) + 1
            slides.insert(0, {"slide_number": 1, "slide_type": "title", "title": topic, "content": [subject or "Presentation"]})
            self._add_image_hints(slides[1:], topic, subject)
            return self._enforce_bullet_constraints({"presentation_title": topic, "presentation_subtitle": subject or "Presentation", "slides": slides})
        except:
            return self._create_fallback_slides(topic, subject, num_slides)

    def _create_fallback_slides(self, topic: str, subject: Optional[str], num_slides: int) -> Dict:
        slides = [{"slide_number": 1, "slide_type": "title", "title": topic, "content": [subject or "Presentation"]}]
        for i in range(1, num_slides + 1):
            slides.append({"slide_number": i + 1, "slide_type": "content", "title": f"Key Concept {i}", "content": [f"Point 1 about {topic}"]})
        return {"presentation_title": topic, "presentation_subtitle": subject or "Presentation", "slides": slides}

    def _add_image_hints(self, slides: list[dict], topic: str, subject: Optional[str], max_hints: int = 3) -> None:
        hints = 0
        for s in slides:
            if hints >= max_hints: break
            if s.get("_no_image") or s.get("image_mode") == "NONE": continue
            title = (s.get("title") or "").lower()
            if "intro" in title or "architecture" in title or "diagram" in title:
                s["image_query"] = f"{topic} {title}"
                hints += 1

    def _enforce_bullet_constraints(self, slide_data: Dict, max_bullets: int = 10, max_len: int = 140, _mode_5_exact_guard: bool = False) -> Dict:
        """Keep bullets concise and slide-ready"""
        is_mode_2 = slide_data.get("_mode_2_title_pure", False)
        slides = slide_data.get("slides", [])
        for slide in slides:
            if _mode_5_exact_guard and slide.get("_is_exact_content"): continue
            content = slide.get("content", [])
            if not isinstance(content, list): continue
            trimmed = []
            for point in content:
                p = str(point).strip()
                if len(p) > max_len: p = p[:max_len-3] + "..."
                trimmed.append(p)
                if len(trimmed) >= max_bullets: break
            slide["content"] = trimmed
        return slide_data

    def generate_slides_for_topics(self, topics: list[str], subject: str, total_slides: Optional[int] = None, min_slides_per_topic: int = 3) -> dict:
        """Generate multiple slides per topic"""
        model_type = self.model_manager.detect_model_preference(subject + " " + " ".join(topics), self.default_model)
        slides = [{"slide_number": 1, "slide_type": "title", "title": f"{subject} - Topics", "content": ["Topics Overview"]}]
        slide_num = 2
        per_topic = max(min_slides_per_topic, (total_slides - 1) // len(topics) if total_slides else 3)
        for topic in topics:
            for _ in range(per_topic):
                prompt = f"Generate slide for {topic}. JSON: {{\"title\": \"...\", \"content\": [...]}}"
                try:
                    res = self.model_manager.generate_content(prompt, model_type)
                    if "```json" in res: res = res.split("```json")[1].split("```")[0].strip()
                    obj = json.loads(res)
                    obj["slide_number"] = slide_num
                    slides.append(obj)
                except:
                    slides.append({"slide_number": slide_num, "title": topic, "content": [f"Point about {topic}"]})
                slide_num += 1
        return self._enforce_bullet_constraints({"presentation_title": subject, "presentation_subtitle": "Topics Overview", "slides": slides})

# --- CrewAI Exports ---

# Instance for API usage
ppt_generator_agent_instance = PPTContentGenerator()

if Agent:
    ppt_generator_agent = Agent(
        role="PowerPoint Content Specialist",
        goal="Generate high-quality, structured academic PowerPoint content",
        backstory="""You are an expert academic curriculum designer. You specialize in 
        converting complex topics into bite-sized, teachable slide content with 
        mathematical precision and pedagogical depth.""",
        verbose=True,
        allow_delegation=False
    )
else:
    ppt_generator_agent = None

def create_ppt_generation_task(topic: str, content: str, num_slides: int) -> Optional[Task]:
    """Helper function to create a CrewAI task for PPT generation"""
    if not Task:
        return None
        
    return Task(
        description=f"""
        Generate a PowerPoint presentation structure for the topic: '{topic}'.
        
        Guidelines:
        1. Number of slides requested: {num_slides}
        2. Content context: {content[:1000] if content else 'Use your own architectural knowledge'}
        3. Follow the standard JSON format expected by the PPTCreator.
        
        Ensure you include:
        - A title slide
        - Logical content slides with 8-10 bullets each
        - In-depth academic content
        """,
        expected_output="A JSON object containing presentation_title, presentation_subtitle, and a list of slides.",
        agent=ppt_generator_agent
    )