import os
import json
import re
from dotenv import load_dotenv
from typing import Dict, List, Optional, Literal, Tuple
from pydantic import BaseModel, Field
import sys
from pathlib import Path

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
        
        # Extract exact content - handle both formats:
        # Format 1: "Slide X: Title: ... Content: - bullet1 - bullet2"
        # Format 2: "Slide X: Title: ... Content:\n\nline1\n\nline2\n\nline3"
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
                    # Handle plain text format (no bullet prefix) - this is the user's format
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
            print(f"  Prompt preview: {prompt[:800]}")
        
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
        
        # Try to find "Slide structure:" section - be more flexible with the pattern
        # Look for "Slide structure:" followed by titles, then "Image placement:"
        structure_patterns = [
            r'Slide\s+structure:\s*(.*?)(?:\n\nImage\s+placement:|Image\s+placement:|$)',  # Original pattern
            r'Slide\s+structure:\s*(.*?)(?:Image\s+placement:|$)',  # Without double newline requirement
            r'Slide\s+structure:\s*(.*?)(?:\nImage\s+placement:|Image\s+placement:|$)',  # Single newline
        ]
        
        structure_section = None
        for pattern in structure_patterns:
            structure_section = re.search(pattern, prompt, re.IGNORECASE | re.DOTALL)
            if structure_section:
                print(f"  ✓ Found 'Slide structure:' section using pattern")
                break
        
        if structure_section:
            titles_text = structure_section.group(1)
            print(f"  🔍 Titles text length: {len(titles_text)}, preview: {titles_text[:200]}")
            
            # Match "Slide X: TITLE" patterns - be more flexible with whitespace
            title_pattern = r'Slide\s+(\d+):\s*([^\n]+)'
            matches = list(re.finditer(title_pattern, titles_text, re.IGNORECASE))
            print(f"  🔍 Found {len(matches)} title matches in structure section")
            
            for match in matches:
                slide_num = int(match.group(1))
                title = match.group(2).strip()
                # CRITICAL: Use title EXACTLY as provided - only remove trailing whitespace
                # Do NOT remove punctuation - user's title is exact
                title = title.rstrip()  # Only remove trailing whitespace
                if title:  # Only add if title is not empty
                    slide_titles.append({'slide_number': slide_num, 'title': title})
                    print(f"  ✓ Extracted title for Slide {slide_num}: '{title}'")
        
        # If not found, try "Slide titles:" as fallback
        if not slide_titles:
            print(f"  🔍 Trying 'Slide titles:' as fallback")
            titles_section = re.search(r'Slide\s+titles?:\s*(.*?)(?:\n\nImage\s+placement:|Image\s+placement:|$)', prompt, re.IGNORECASE | re.DOTALL)
            if titles_section:
                titles_text = titles_section.group(1)
                title_pattern = r'Slide\s+(\d+):\s*([^\n]+)'
                matches = re.finditer(title_pattern, titles_text, re.IGNORECASE)
                for match in matches:
                    slide_num = int(match.group(1))
                    title = match.group(2).strip()
                    # CRITICAL: Use title EXACTLY as provided
                    title = title.rstrip()  # Only remove trailing whitespace
                    if title:  # Only add if title is not empty
                        slide_titles.append({'slide_number': slide_num, 'title': title})
                        print(f"  ✓ Found title for Slide {slide_num}: '{title}'")
        
        # If still not found, try searching entire prompt for "Slide X: TITLE" after "Slide structure:"
        if not slide_titles:
            print(f"  🔍 Searching entire prompt for 'Slide X: TITLE' patterns")
            # Find where "Slide structure:" appears
            structure_start = re.search(r'Slide\s+structure:', prompt, re.IGNORECASE)
            if structure_start:
                # Get everything after "Slide structure:" until "Image placement:" or end
                remaining = prompt[structure_start.end():]
                image_start = re.search(r'Image\s+placement:', remaining, re.IGNORECASE)
                if image_start:
                    remaining = remaining[:image_start.start()]
                
                # Match "Slide X: TITLE" patterns
                title_pattern = r'Slide\s+(\d+):\s*([^\n]+)'
                matches = re.finditer(title_pattern, remaining, re.IGNORECASE)
                for match in matches:
                    slide_num = int(match.group(1))
                    title = match.group(2).strip()
                    # CRITICAL: Use title EXACTLY as provided
                    title = title.rstrip()  # Only remove trailing whitespace
                    if title:  # Only add if title is not empty
                        slide_titles.append({'slide_number': slide_num, 'title': title})
                        print(f"  ✓ Found title for Slide {slide_num}: '{title}'")
        
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
        
        print(f"  ✓ Extracted: NUMBER={number}, TOPIC='{topic}', SUBJECT='{subject}'")
        print(f"  ✓ Extracted {len(slide_titles)} slide titles:")
        for t in slide_titles:
            print(f"    - Slide {t['slide_number']}: '{t['title']}'")
        print(f"  ✓ Extracted {len(image_mappings)} image mappings:")
        for img in image_mappings:
            print(f"    - Image {img['image_number']} → Slide {img['slide_number']}")
        
        if not slide_titles:
            print(f"  ⚠ WARNING: No slide titles extracted from prompt!")
            print(f"  Prompt preview: {prompt[:500]}")
        
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
        
        Extract: NUMBER, TOPIC, SUBJECT, per-slide instructions
        (title, generate/exact flag, image instructions)
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
        
        # Extract per-slide instructions - BLOCK-BASED PARSING (replaces fragile regex)
        slide_instructions = []
        instructions_section = re.search(r'Slide\s+instructions:\s*(.*?)$', prompt, re.IGNORECASE | re.DOTALL)
        if instructions_section:
            instructions_text = instructions_section.group(1)
            
            # BLOCK-BASED PARSING: Find all "Slide X:" blocks
            slide_block_pattern = r'Slide\s+(\d+):'
            slide_blocks = list(re.finditer(slide_block_pattern, instructions_text, re.IGNORECASE))
            
            for idx, block_match in enumerate(slide_blocks):
                slide_num = int(block_match.group(1))
                block_start = block_match.start()
                
                # Find end of this block (start of next "Slide X:" or end of text)
                if idx + 1 < len(slide_blocks):
                    block_end = slide_blocks[idx + 1].start()
                else:
                    block_end = len(instructions_text)
                
                slide_block = instructions_text[block_start:block_end]
                
                # Extract title
                title_match = re.search(r'Title:\s*([^\n]+)', slide_block, re.IGNORECASE)
                if not title_match:
                    print(f"  ⚠ Warning: Could not find title for Slide {slide_num}, skipping")
                    continue
                title = title_match.group(1).strip()
                
                # Determine if generate or exact
                should_generate = "generate content" in slide_block.lower()
                exact_content = None
                
                # BLOCK-BASED EXACT CONTENT EXTRACTION
                if not should_generate and "exact content" in slide_block.lower():
                    # Find "Use EXACT content:" marker
                    exact_marker_idx = slide_block.lower().find("use exact content:")
                    if exact_marker_idx >= 0:
                        # Get all lines after the marker
                        content_section = slide_block[exact_marker_idx + len("use exact content:"):]
                        lines = content_section.split('\n')
                        
                        # Extract bullets - only lines starting with "-" or "•"
                        bullets = []
                        for line in lines:
                            line_stripped = line.strip()
                            
                            # Stop at next slide block
                            if re.match(r'^\s*Slide\s+\d+:', line_stripped, re.IGNORECASE):
                                break
                            
                            # Stop at image instructions
                            if line_stripped.lower().startswith('use image') or line_stripped.lower() == 'no image':
                                break
                            
                            # Keep ONLY lines starting with "-" or "•"
                            if line_stripped.startswith('-') or line_stripped.startswith('•'):
                                # Remove leading "- " or "-" or "• " or "•"
                                bullet_text = line_stripped
                                if bullet_text.startswith('- '):
                                    bullet_text = bullet_text[2:].strip()
                                elif bullet_text.startswith('-'):
                                    bullet_text = bullet_text[1:].strip()
                                elif bullet_text.startswith('• '):
                                    bullet_text = bullet_text[2:].strip()
                                elif bullet_text.startswith('•'):
                                    bullet_text = bullet_text[1:].strip()
                                
                                if bullet_text:  # Only add non-empty bullets
                                    bullets.append(bullet_text)
                        
                        # HARD FAIL RULE: If EXACT is declared but no bullets found
                        if not bullets:
                            error_msg = f"Mode 5 EXACT content declared for Slide {slide_num} but no bullets parsed. EXACT content is required when 'Use EXACT content:' is specified."
                            print(f"❌ {error_msg}")
                            print(f"   Slide block preview: {slide_block[:200]}")
                            raise ValueError(error_msg)
                        
                        exact_content = bullets
                        print(f"🔒 MODE 5 EXACT PARSED: Slide {slide_num}, bullets={len(bullets)}")
                        for i, bullet in enumerate(bullets[:3], 1):  # Show first 3 bullets
                            print(f"    - Bullet {i}: {bullet[:60]}...")
                
                # Extract image instruction - MODE 5 IMAGE MODE DETECTION
                image_num = None
                image_mode = "QUERY"  # Default: allow topic-based queries
                
                # Check for explicit image instructions
                image_match = re.search(r'Use\s+Image\s+(\d+)', slide_block, re.IGNORECASE)
                if image_match:
                    image_num = int(image_match.group(1))
                    image_mode = "UPLOAD"  # User uploaded image
                    print(f"  📷 MODE 5: Slide {slide_num} → image_mode=UPLOAD (Image {image_num})")
                elif "no image" in slide_block.lower():
                    image_mode = "NONE"  # Explicitly no image
                    print(f"🚫 MODE 5 IMAGE LOCK: Slide {slide_num} explicitly forbids images")
                else:
                    # No explicit instruction - allow topic-based queries (default)
                    image_mode = "QUERY"
                
                slide_instructions.append({
                    'slide_number': slide_num,
                    'title': title,
                    'should_generate': should_generate,
                    'exact_content': exact_content,
                    'image_number': image_num,
                    'no_image': image_mode == "NONE",
                    'image_mode': image_mode  # NEW: Explicit image intent flag
                })
        
        slide_instructions.sort(key=lambda x: x['slide_number'])
        
        # Determine actual number
        if slide_instructions:
            number = max(number, max(s['slide_number'] for s in slide_instructions))
        
        print(f"  ✓ Extracted: NUMBER={number}, TOPIC='{topic}', SUBJECT='{subject}'")
        print(f"  ✓ Extracted {len(slide_instructions)} slide instructions")
        
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
        Returns list of bullet strings.
        """
        effective_model = "groq_llama" if model_type != "gemini" else model_type
        
        prompt = f"""Generate 8-10 bullet points for a PowerPoint slide.

TOPIC: {topic}
SUBJECT: {subject}
SLIDE TITLE: {title}

CRITICAL INSTRUCTIONS:
- Generate educational bullet points (14-22 words each) about {topic} related to "{title}".
- DO NOT generate or modify the slide title - the title "{title}" is already provided and must be used exactly as-is.
- Generate ONLY content (bullet points), NOT the title.

Return ONLY JSON:
{{
    "content": ["bullet 1", "bullet 2", "bullet 3", ...]
}}

CRITICAL: Return at least 8 bullets, maximum 10. Each bullet should be 14-22 words. DO NOT include the title in your response."""
        
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
                # Retry with simpler prompt
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
            
            # Limit to 10 bullets max
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
        for i in range(1, min(num_slides + 1, len(default_titles) + 1)):
            if i <= len(default_titles):
                titles.append({'slide_number': i, 'title': default_titles[i-1]})
            else:
                titles.append({'slide_number': i, 'title': f"Key Concept {i}"})
        
        return titles
    
    def generate_slide_content(self, topic: str, content: str, num_slides: int = 8, 
                               subject: Optional[str] = None, module: Optional[str] = None, 
                               model_type: Optional[ModelType] = None, 
                               user_input: Optional[str] = None, 
                               custom_slides: Optional[List[Dict]] = None, 
                               slide_structure: Optional[List[Dict]] = None, 
                               ppt_mode: str = "auto_generate") -> Dict:
        """
        Main entry point for PPT generation with mode support.
        
        If user_input is provided, detect mode and parse from prompt.
        Otherwise, use legacy parameters.
        """
        # STEP 1: TRACE DATA FLOW - Log entry point
        print(f"🔍 GENERATOR ENTRY | user_input type={type(user_input)}, len={len(user_input) if user_input else 0}, preview={repr(user_input)[:300] if user_input else 'None/Empty'}")
        
        # STEP 2: HARD FAIL RULE - Mode 2 requires user_input
        # Check if this is Mode 2 BEFORE checking user_input
        is_mode_2_request = False
        if user_input:
            # Quick check for Mode 2 indicators
            user_input_lower = str(user_input).lower()
            is_mode_2_request = "slide titles:" in user_input_lower
        
        if is_mode_2_request and (not user_input or len(str(user_input).strip()) == 0):
            error_msg = "Mode 2 requires user_input but received None/empty. Cannot generate PPT without user-provided titles."
            print(f"❌ HARD FAIL: {error_msg}")
            raise ValueError(error_msg)
        
        # STEP 3: If user_input provided, use mode-based generation
        if user_input:
            print(f"🔍 Checking user_input for mode detection...")
            print(f"🔍 user_input preview: {str(user_input)[:200]}")
            detected_mode = self._detect_ppt_mode(user_input)
            print(f"🧠 DETECTED MODE: {detected_mode}")
            
            # STEP 4: DISABLE LEGACY GENERATION FOR MODE 2
            if detected_mode == "mode_2":
                print("🔍 MODE 2 PARSER CALLED")
                try:
                    parsed = self._parse_mode_2(user_input)
                    print(f"✅ MODE 2 PARSER SUCCESS: Extracted {len(parsed.get('slide_titles', []))} titles")
                    
                    # STEP 5: SLIDE COUNT ENFORCEMENT - Verify before generation
                    expected_slides = parsed.get('number', 0) + 1  # 1 base + N user slides
                    print(f"🔍 MODE 2: Expected slide count = {expected_slides} (1 base + {parsed.get('number', 0)} user)")
                    
                    result = self._generate_mode_2(parsed, content, model_type)
                    generated_slides = result.get('slides', [])
                    actual_count = len(generated_slides)
                    
                    print(f"🔍 MODE 2: Generated {actual_count} slides, expected {expected_slides}")
                    
                    # STEP 5: Assertion - fail if count mismatch
                    if actual_count != expected_slides:
                        error_msg = f"Mode 2 slide count mismatch! Generated {actual_count} slides but expected {expected_slides} (1 base + {parsed.get('number', 0)} user). DO NOT auto-fix."
                        print(f"❌ {error_msg}")
                        raise ValueError(error_msg)
                    
                    # STEP 6: TITLE LOCK ENFORCEMENT - Verify titles match exactly
                    user_titles = {t['slide_number']: t['title'] for t in parsed.get('slide_titles', [])}
                    print(f"🔍 MODE 2: Verifying titles match user-provided titles exactly...")
                    print(f"🔍 MODE 2: User titles: {user_titles}")
                    
                    for slide in generated_slides:
                        slide_num = slide.get('slide_number', 0)
                        if slide_num > 1:  # Skip base slide
                            user_slide_num = slide_num - 1  # Convert to user's slide number
                            generated_title = slide.get('title', '')
                            expected_title = user_titles.get(user_slide_num)
                            
                            if expected_title:
                                if generated_title != expected_title:
                                    error_msg = f"Mode 2 title mismatch! Slide {slide_num} (user's slide {user_slide_num}) has title '{generated_title}' but expected '{expected_title}'. User titles are LAW - no rewriting allowed."
                                    print(f"❌ {error_msg}")
                                    raise ValueError(error_msg)
                                else:
                                    print(f"  ✅ Mode 2: Slide {slide_num} title matches: '{generated_title}'")
                    
                    print(f"✅ MODE 2 GENERATOR SUCCESS: Generated {len(generated_slides)} slides with correct titles")
                    return result
                except Exception as e:
                    print(f"❌ MODE 2 ERROR: {str(e)}")
                    import traceback
                    print(f"   Traceback: {traceback.format_exc()}")
                    raise  # Re-raise - DO NOT fall back to legacy
            elif detected_mode == "mode_1":
                print("🔍 MODE 1 PARSER CALLED")
                parsed = self._parse_mode_1(user_input)
                return self._generate_mode_1(parsed, content, model_type)
            elif detected_mode == "mode_3":
                print("🔍 MODE 3 PARSER CALLED")
                parsed = self._parse_mode_3(user_input)
                return self._generate_mode_3(parsed, content, model_type)
            elif detected_mode == "mode_4":
                print("🔍 MODE 4 PARSER CALLED")
                parsed = self._parse_mode_4(user_input)
                return self._generate_mode_4(parsed, content, model_type)
            elif detected_mode == "mode_5":
                print("🔍 MODE 5 PARSER CALLED")
                parsed = self._parse_mode_5(user_input)
                return self._generate_mode_5(parsed, content, model_type)
            else:
                # Invalid mode detected - throw error instead of falling back
                raise ValueError("Invalid PPT Mode format. Please use a PPT Mode template.")
        
        # STEP 4: Legacy fallback ONLY when user_input is None AND NOT Mode 2
        # Mode 2 is FORBIDDEN from using legacy generation
        if is_mode_2_request:
            error_msg = "Mode 2 detected but user_input is None/empty. Mode 2 requires user-provided titles. Legacy generation is FORBIDDEN for Mode 2."
            print(f"❌ HARD FAIL: {error_msg}")
            raise ValueError(error_msg)
        
        print(f"⚠️  No user_input provided, using legacy generation (NOT Mode 2)")
        return self._generate_legacy(topic, content, num_slides, subject, module, model_type, user_input)
    
    def _generate_mode_1(self, parsed: Dict, context: str, model_type: Optional[ModelType]) -> Dict:
        """Generate Mode 1: Auto PPT - Generate everything"""
        print(f"🚀 MODE 1 GENERATION: Generating {parsed['number']} slides with auto-generated titles")
        
        if model_type is None:
            model_type = "groq_llama"
        
        # Generate default slide titles
        slide_titles = self._get_default_slide_titles(parsed['number'], parsed['topic'])
        
        # Generate content for each slide
        slides = []
        for title_info in slide_titles:
            slide_num = title_info['slide_number']
            title = title_info['title']
            
            bullets = self._generate_single_slide_content(
                slide_num, title, parsed['topic'], parsed['subject'], context, model_type
            )
            
            slides.append({
                'slide_number': slide_num + 1,  # Shift by +1 for base slide
                'slide_type': 'content',
                'title': title,
                'content': bullets,
                'speaker_notes': f"Explain {title} in the context of {parsed['topic']}."
            })
        
        # Add base slide
        base_slide = {
            'slide_number': 1,
            'slide_type': 'title',
            'title': parsed['topic'],
            'content': [parsed['subject'] or "Educational Presentation"],
            'speaker_notes': f"Introduction to the presentation on {parsed['topic']}."
        }
        slides.insert(0, base_slide)
        
        # Add image hints
        user_slides = [s for s in slides if s.get('slide_number', 0) > 1]
        self._add_image_hints(user_slides, parsed['topic'], parsed['subject'])
        
        result = {
            'presentation_title': parsed['topic'],
            'presentation_subtitle': parsed['subject'] or "Educational Presentation",
            'slides': slides
        }
        
        return self._enforce_bullet_constraints(result)
    
    def _generate_mode_2(self, parsed: Dict, context: str, model_type: Optional[ModelType]) -> Dict:
        """Generate Mode 2: Custom Titles - Generate content only, use titles exactly
        
        CRITICAL RULES:
        - Titles MUST come ONLY from user (parsed['slide_titles'])
        - DO NOT generate titles
        - DO NOT use fallback titles
        - DO NOT merge with LLM titles
        - Generate ONLY content (8-10 bullets) for each user title
        """
        print(f"🚀 MODE 2 GENERATION: Generating content for {len(parsed['slide_titles'])} slides with exact titles")
        
        # CRITICAL: Validate that we have slide titles - this is MANDATORY for Mode 2
        if not parsed['slide_titles'] or len(parsed['slide_titles']) == 0:
            raise ValueError("Mode 2 requires slide titles. No titles were extracted from the prompt. Please use the format: 'Slide titles: Slide 1: {TITLE} Slide 2: {TITLE} ...'")
        
        # CRITICAL VALIDATION: Titles count must match requested slides
        expected_slides = parsed['number']
        if len(parsed['slide_titles']) != expected_slides:
            raise ValueError(f"Mode 2 requires exactly {expected_slides} slide titles. Found {len(parsed['slide_titles'])} titles. User titles are LAW - cannot proceed with mismatch.")
        
        print(f"  ✅ VALIDATION PASSED: {len(parsed['slide_titles'])} titles match {expected_slides} requested slides")
        print(f"  📋 User-provided titles (EXACT, no modification):")
        user_titles_dict = {}  # Store for verification
        for t in parsed['slide_titles']:
            print(f"    - Slide {t['slide_number']}: '{t['title']}'")
            user_titles_dict[t['slide_number']] = t['title']
        
        if model_type is None:
            model_type = "groq_llama"
        
        # CRITICAL: Generate slides in EXACT order - one slide per user title, NO MORE, NO LESS
        # MODE 2 TITLE-PURE: Titles are NEVER modified, generated, rewritten, or passed to any LLM
        slides = []
        for title_info in parsed['slide_titles']:
            slide_num = title_info['slide_number']
            user_title = title_info['title']  # EXACT title from user - this is the SOURCE OF TRUTH
            
            # TITLE-PURE RULE: Use user_title directly - NO intermediate variables, NO modifications
            print(f"  📝 Generating content for Slide {slide_num}: '{user_title}' (EXACT title from user - TITLE-PURE)")
            
            # Generate content ONLY - LLM must NOT generate title
            # Pass user_title to LLM for context, but LLM is instructed NOT to modify it
            bullets = self._generate_single_slide_content(
                slide_num, user_title, parsed['topic'], parsed['subject'], context, model_type
            )
            
            # TITLE-PURE: Direct assignment - slide['title'] = user_title (NO modifications)
            slide = {
                'slide_number': slide_num + 1,  # Shift by +1 for base slide
                'slide_type': 'content',
                'content': bullets,
                'speaker_notes': f"Explain {user_title} in the context of {parsed['topic']}.",
            }
            
            # TITLE-PURE: Assign title DIRECTLY from user_title - NO intermediate steps
            slide['title'] = user_title  # DIRECT ASSIGNMENT - user title is LAW
            
            # HARD ASSERTION BEFORE LOCKING: Title must be EXACTLY user_title
            assert slide['title'] == user_title, f"Mode 2 title modified before lock! Slide {slide_num} title is '{slide['title']}' but must be '{user_title}'. TITLE-PURE violation!"
            
            # Lock title AFTER assertion passes
            slide['title_locked'] = True  # CRITICAL: Lock title to prevent modification
            slide['original_title'] = user_title  # Store original for verification
            
            # SECOND ASSERTION: Verify title wasn't modified during slide creation
            if slide['title'] != user_title:
                error_msg = f"Mode 2 title corruption detected! Slide {slide_num} title was '{slide['title']}' but should be '{user_title}'. User titles are LAW - no rewriting allowed."
                print(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            slides.append(slide)
        
        # STEP 5: SLIDE COUNT ENFORCEMENT - Validate before adding base slide
        if len(slides) != expected_slides:
            error_msg = f"Mode 2 generation error: Generated {len(slides)} content slides but {expected_slides} expected. DO NOT auto-fix."
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        # Add base slide
        base_slide = {
            'slide_number': 1,
            'slide_type': 'title',
            'title': parsed['topic'],
            'content': [parsed['subject'] or "Educational Presentation"],
            'speaker_notes': f"Introduction to the presentation on {parsed['topic']}."
        }
        slides.insert(0, base_slide)
        
        # Mode 2: No auto images (per spec)
        # Skip image hints for Mode 2 - DO NOT call _add_image_hints (it doesn't modify titles, but we're being extra safe)
        
        result = {
            'presentation_title': parsed['topic'],
            'presentation_subtitle': parsed['subject'] or "Educational Presentation",
            'slides': slides,
            '_mode_2_title_pure': True  # Flag to prevent title modification in any downstream function
        }
        
        print(f"✅ MODE 2 COMPLETE: Generated {len(slides)} slides (1 base + {len(slides)-1} content)")
        print(f"  Expected: {expected_slides} content slides")
        print(f"  Actual: {len(slides)-1} content slides")
        print(f"  Final slide titles: {[s.get('title') for s in slides]}")
        
        # STEP 5: Final slide count assertion (1 base + N user slides)
        final_expected = expected_slides + 1  # +1 for base slide
        if len(slides) != final_expected:
            error_msg = f"Mode 2 final slide count mismatch! Generated {len(slides)} slides (expected {final_expected}: 1 base + {expected_slides} user). DO NOT auto-fix."
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        # STEP 6: TITLE LOCK ENFORCEMENT - Final verification BEFORE any function calls
        print(f"🔍 MODE 2: Final title verification BEFORE _enforce_bullet_constraints...")
        for slide in slides:
            slide_num = slide.get('slide_number', 0)
            if slide_num > 1:  # Skip base slide
                user_slide_num = slide_num - 1
                generated_title = slide.get('title', '')
                expected_title = user_titles_dict.get(user_slide_num)
                if expected_title and generated_title != expected_title:
                    error_msg = f"Mode 2 final title mismatch! Slide {slide_num} (user's slide {user_slide_num}) has title '{generated_title}' but expected '{expected_title}'. User titles are LAW."
                    print(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                print(f"  ✅ MODE 2: Slide {slide_num} title verified: '{generated_title}' == '{expected_title}'")
        
        print(f"✅ MODE 2: All titles verified - exact match with user-provided titles")
        
        # CRITICAL: Final assertions - fail loudly if violated
        assert len(slides) == final_expected, f"Mode 2 slide count violation! Expected {final_expected} slides (1 base + {expected_slides} user), but got {len(slides)}"
        
        # TITLE-PURE: _enforce_bullet_constraints only modifies content, not titles - safe to call
        # But we'll verify titles again AFTER to be absolutely sure
        result = self._enforce_bullet_constraints(result)
        
        # TITLE-PURE: Final verification AFTER _enforce_bullet_constraints
        print(f"🔍 MODE 2: Final title verification AFTER _enforce_bullet_constraints...")
        for slide in result.get('slides', []):
            slide_num = slide.get('slide_number', 0)
            if slide_num > 1:  # Skip base slide
                user_slide_num = slide_num - 1
                final_title = slide.get('title', '')
                expected_title = user_titles_dict.get(user_slide_num)
                if expected_title and final_title != expected_title:
                    error_msg = f"Mode 2 title modified by _enforce_bullet_constraints! Slide {slide_num} (user's slide {user_slide_num}) has title '{final_title}' but expected '{expected_title}'. TITLE-PURE violation!"
                    print(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                print(f"  ✅ MODE 2: Slide {slide_num} title still pure: '{final_title}' == '{expected_title}'")
        
        print(f"✅ MODE 2: TITLE-PURE verified - no modifications detected")
        return result
    
    def _generate_mode_3(self, parsed: Dict, context: str, model_type: Optional[ModelType]) -> Dict:
        """Generate Mode 3: Exact Content - Use exact content, NO LLM generation"""
        print(f"🚀 MODE 3 GENERATION: Using exact content for {len(parsed['exact_content'])} slides")
        
        # CRITICAL: Validate that we have exact content
        if not parsed['exact_content'] or len(parsed['exact_content']) == 0:
            raise ValueError("Mode 3 requires exact content. No content was extracted from the prompt. Please use the format: 'Slide X: Title: ... Content: ...'")
        
        slides = []
        for exact_slide in parsed['exact_content']:
            slide_num = exact_slide['slide_number']
            title = exact_slide['title']  # EXACT title - use as-is
            bullets = exact_slide['content']  # EXACT bullets - use word-for-word, no modification
            
            print(f"  📝 Creating Slide {slide_num + 1}: '{title}' with {len(bullets)} exact content lines")
            
            slides.append({
                'slide_number': slide_num + 1,  # Shift by +1 for base slide
                'slide_type': 'content',
                'title': title,  # EXACT - no modification
                'content': bullets,  # EXACT - word-for-word, no modification
                'speaker_notes': f"Present the exact content provided for {title}."
            })
        
        # Add base slide
        base_slide = {
            'slide_number': 1,
            'slide_type': 'title',
            'title': parsed['topic'],
            'content': [parsed['subject'] or "Educational Presentation"],
            'speaker_notes': f"Introduction to the presentation on {parsed['topic']}."
        }
        slides.insert(0, base_slide)
        
        # Mode 3: No auto images (exact content mode)
        # Skip image hints for Mode 3
        
        result = {
            'presentation_title': parsed['topic'],
            'presentation_subtitle': parsed['subject'] or "Educational Presentation",
            'slides': slides
        }
        
        print(f"✓ MODE 3 COMPLETE: Generated {len(slides)} slides (1 base + {len(parsed['exact_content'])} exact content)")
        
        return self._enforce_bullet_constraints(result)
    
    def _generate_mode_4(self, parsed: Dict, context: str, model_type: Optional[ModelType]) -> Dict:
        """Generate Mode 4: Image Controlled - Generate content, apply images exactly
        
        CRITICAL RULES:
        - Titles MUST come ONLY from user (parsed['slide_titles'])
        - DO NOT generate titles
        - DO NOT use fallback titles
        - DO NOT merge with LLM titles
        - Generate ONLY content (8-10 bullets) for each user title
        """
        print(f"🚀 MODE 4 GENERATION: Generating content for {len(parsed['slide_titles'])} slides with image mappings")
        
        # CRITICAL: Validate that we have slide titles - this is MANDATORY for Mode 4
        if not parsed['slide_titles'] or len(parsed['slide_titles']) == 0:
            raise ValueError("Mode 4 requires slide titles. No titles were extracted from the prompt. Please use the format: 'Slide structure: Slide 1: {TITLE} Slide 2: {TITLE} ...'")
        
        # CRITICAL VALIDATION: Titles count must match requested slides
        expected_slides = parsed['number']
        if len(parsed['slide_titles']) != expected_slides:
            raise ValueError(f"Mode 4 requires exactly {expected_slides} slide titles. Found {len(parsed['slide_titles'])} titles. User titles are LAW - cannot proceed with mismatch.")
        
        print(f"  ✅ VALIDATION PASSED: {len(parsed['slide_titles'])} titles match {expected_slides} requested slides")
        print(f"  📋 User-provided titles (EXACT, no modification):")
        for t in parsed['slide_titles']:
            print(f"    - Slide {t['slide_number']}: '{t['title']}'")
        
        if model_type is None:
            model_type = "groq_llama"
        
        # CRITICAL: Generate slides in EXACT order - one slide per user title, NO MORE, NO LESS
        slides = []
        for title_info in parsed['slide_titles']:
            slide_num = title_info['slide_number']
            title = title_info['title']  # EXACT title - use as-is, NO modification
            
            print(f"  📝 Generating content for Slide {slide_num}: '{title}' (EXACT title from user)")
            
            # Generate content ONLY - LLM must NOT generate title
            bullets = self._generate_single_slide_content(
                slide_num, title, parsed['topic'], parsed['subject'], context, model_type
            )
            
            slide = {
                'slide_number': slide_num + 1,  # Shift by +1 for base slide
                'slide_type': 'content',
                'title': title,  # EXACT title from user - NO modification, NO generation
                'content': bullets,
                'speaker_notes': f"Explain {title} in the context of {parsed['topic']}."
            }
            
            # Apply image mapping if exists (user-specified images only)
            # slide_num is user's slide number (1, 2, 3), we shift it to actual slide number (2, 3, 4)
            for img_map in parsed['image_mappings']:
                if img_map['slide_number'] == slide_num:
                    slide['image_number'] = img_map['image_number']
                    print(f"  ✓ Mapped Image {img_map['image_number']} to user's slide {slide_num} (actual slide {slide_num + 1})")
            
            slides.append(slide)
        
        # CRITICAL: Validate slide count - must be exactly expected_slides
        if len(slides) != expected_slides:
            raise ValueError(f"Mode 4 generation error: Generated {len(slides)} slides but {expected_slides} expected. This should never happen.")
        
        # Add base slide
        base_slide = {
            'slide_number': 1,
            'slide_type': 'title',
            'title': parsed['topic'],
            'content': [parsed['subject'] or "Educational Presentation"],
            'speaker_notes': f"Introduction to the presentation on {parsed['topic']}."
        }
        slides.insert(0, base_slide)
        
        # Mode 4: NO auto images - only user-specified images
        # DO NOT call _add_image_hints for Mode 4
        
        result = {
            'presentation_title': parsed['topic'],
            'presentation_subtitle': parsed['subject'] or "Educational Presentation",
            'slides': slides
        }
        
        print(f"✅ MODE 4 COMPLETE: Generated {len(slides)} slides (1 base + {len(slides)-1} content)")
        print(f"  Expected: {expected_slides} content slides")
        print(f"  Actual: {len(slides)-1} content slides")
        print(f"  Images: {len(parsed['image_mappings'])} user-specified images applied, NO auto images")
        print(f"  Final slide titles: {[s.get('title') for s in slides]}")
        
        return self._enforce_bullet_constraints(result)
    
    def _generate_mode_5(self, parsed: Dict, context: str, model_type: Optional[ModelType]) -> Dict:
        """Generate Mode 5: Mixed Control - Process each slide independently
        
        CRITICAL RULES:
        - Slide count MUST be locked BEFORE LLM calls
        - LLM may ONLY generate content, never create slides
        - Retries must ONLY regenerate content, never recreate slides
        - Total slides = 1 base + len(user_slide_instructions)
        """
        print(f"🚀 MODE 5 GENERATION: Processing {len(parsed['slide_instructions'])} slides with mixed instructions")
        
        # MODE 5 SLIDE COUNT LOCK: Compute expected total BEFORE any LLM calls
        expected_user_slides = len(parsed['slide_instructions'])
        expected_total_slides = 1 + expected_user_slides  # 1 base + N user slides
        print(f"🔒 MODE 5 SLIDE COUNT LOCK: Expected total = {expected_total_slides} (1 base + {expected_user_slides} user)")
        
        if model_type is None:
            model_type = "groq_llama"
        
        # MODE 5 SLIDE COUNT LOCK: Create slides list ONCE, before LLM calls
        slides = []
        
        # Process each slide instruction - create slide structure FIRST
        for instruction in parsed['slide_instructions']:
            slide_num = instruction['slide_number']
            title = instruction['title']  # EXACT title
            
            # MODE 5 SLIDE COUNT LOCK: Create slide structure BEFORE LLM call
            slide = {
                'slide_number': slide_num + 1,  # Shift by +1 for base slide
                'slide_type': 'content',
                'title': title,  # EXACT title
                'content': [],  # Will be filled below
                'speaker_notes': f"Present {title} in the context of {parsed['topic']}."
            }
            
            # MODE 5 IMAGE MODE ENFORCEMENT: Apply image instruction based on image_mode
            image_mode = instruction.get('image_mode', 'QUERY')
            slide['_mode_5_image_mode'] = image_mode  # Store flag for downstream enforcement
            
            if image_mode == "UPLOAD":
                # User uploaded image
                if instruction['image_number']:
                    slide['image_number'] = instruction['image_number']
                    print(f"  📷 MODE 5: Slide {slide_num} → image_mode=UPLOAD (Image {instruction['image_number']})")
            elif image_mode == "NONE":
                # Explicitly no image - set flag to prevent any image operations
                slide['_no_image'] = True
                print(f"🚫 MODE 5 IMAGE LOCK: Slide {slide_num} marked as NO IMAGE - will skip all image operations")
            else:
                # image_mode == "QUERY" - allow topic-based queries (default behavior)
                pass
            
            # MODE 5 EXACT CONTENT GUARD: Short-circuit LLM for EXACT slides
            is_exact_slide = not instruction['should_generate'] and instruction.get('exact_content')
            
            if is_exact_slide:
                # EXACT SLIDE SHORT-CIRCUIT: DO NOT call LLM, use exact content verbatim
                exact_bullets = instruction['exact_content']
                
                # HARD FAIL: EXACT content must exist (should be caught in parser, but double-check)
                if not exact_bullets or len(exact_bullets) == 0:
                    error_msg = f"MODE 5 EXACT CONTENT ERROR: Slide {slide_num} marked as EXACT but exact_content is empty. Cannot proceed. This should have been caught during parsing."
                    print(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                
                # Inject bullets verbatim - NO modification
                slide['content'] = exact_bullets.copy() if isinstance(exact_bullets, list) else list(exact_bullets)
                slide['_is_exact_content'] = True  # Flag to prevent modification in _enforce_bullet_constraints
                print(f"🔒 MODE 5 EXACT LOCK: Injected user-provided content for slide {slide_num} ({len(slide['content'])} bullets)")
                print(f"🚫 MODE 5: Skipping LLM generation for slide {slide_num} (EXACT content)")
            elif instruction['should_generate']:
                # Generate content - retries here will ONLY affect bullets, not slide structure
                bullets = self._generate_single_slide_content(
                    slide_num, title, parsed['topic'], parsed['subject'], context, model_type
                )
                slide['content'] = bullets
                slide['_is_exact_content'] = False  # Mark as generated
                print(f"  📝 MODE 5 GENERATE: Slide {slide_num} generated content ({len(bullets)} bullets)")
            else:
                # Fallback: no exact content and not generating - use empty list
                slide['content'] = []
                slide['_is_exact_content'] = False
                print(f"  ⚠ MODE 5 WARNING: Slide {slide_num} has no content (not EXACT, not GENERATE)")
            
            slides.append(slide)
        
        # MODE 5 SLIDE COUNT LOCK: Assert user slides count BEFORE adding base slide
        if len(slides) != expected_user_slides:
            error_msg = f"MODE 5 SLIDE COUNT LOCK violation! Generated {len(slides)} user slides but expected {expected_user_slides}. This should never happen."
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        # Add base slide
        base_slide = {
            'slide_number': 1,
            'slide_type': 'title',
            'title': parsed['topic'],
            'content': [parsed['subject'] or "Educational Presentation"],
            'speaker_notes': f"Introduction to the presentation on {parsed['topic']}."
        }
        slides.insert(0, base_slide)
        
        # MODE 5 SLIDE COUNT LOCK: Final assertion - total must match expected
        if len(slides) != expected_total_slides:
            error_msg = f"MODE 5 SLIDE COUNT LOCK violation! Generated {len(slides)} total slides but expected {expected_total_slides} (1 base + {expected_user_slides} user). DO NOT auto-fix."
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
        print(f"✅ MODE 5 SLIDE COUNT LOCK: Verified {len(slides)} slides (matches expected {expected_total_slides})")
        
        # Add image hints for slides without explicit image instructions
        # MODE 5 IMAGE LOCK: Skip slides with image_mode == "NONE"
        user_slides = []
        for s in slides:
            if s.get('slide_number', 0) > 1:  # Skip base slide
                image_mode = s.get('_mode_5_image_mode', 'QUERY')
                if image_mode == "NONE":
                    print(f"🚫 MODE 5 IMAGE LOCK: Skipping image hints for slide {s.get('slide_number')} (No image declared)")
                    continue  # Skip this slide - no images allowed
                if 'image_number' not in s:  # Only add hints if no uploaded image
                    user_slides.append(s)
        
        if user_slides:
            self._add_image_hints(user_slides, parsed['topic'], parsed['subject'])
        
        result = {
            'presentation_title': parsed['topic'],
            'presentation_subtitle': parsed['subject'] or "Educational Presentation",
            'slides': slides
        }
        
        # MODE 5 SLIDE COUNT LOCK: Assert again after bullet constraints
        result = self._enforce_bullet_constraints(result, _mode_5_exact_guard=True)
        final_slides = result.get('slides', [])
        if len(final_slides) != expected_total_slides:
            error_msg = f"MODE 5 SLIDE COUNT LOCK violation after bullet constraints! Has {len(final_slides)} slides but expected {expected_total_slides}. DO NOT auto-fix."
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        # MODE 5 EXACT CONTENT VERIFICATION: Assert EXACT slides contain exact content
        print(f"🔍 MODE 5: Verifying EXACT content was not modified...")
        for instruction in parsed['slide_instructions']:
            slide_num = instruction['slide_number']
            actual_slide_num = slide_num + 1  # Shift for base slide
            is_exact = not instruction['should_generate'] and instruction.get('exact_content')
            
            if is_exact:
                # Find the corresponding slide
                for slide in final_slides:
                    if slide.get('slide_number') == actual_slide_num:
                        expected_bullets = instruction['exact_content']
                        actual_bullets = slide.get('content', [])
                        
                        # Verify content matches (allow for list vs string comparison)
                        if isinstance(expected_bullets, list) and isinstance(actual_bullets, list):
                            # Compare lists
                            if len(expected_bullets) != len(actual_bullets):
                                error_msg = f"MODE 5 EXACT CONTENT violation! Slide {actual_slide_num} (user's slide {slide_num}) has {len(actual_bullets)} bullets but expected {len(expected_bullets)}. EXACT content was modified!"
                                print(f"❌ {error_msg}")
                                print(f"   Expected: {expected_bullets}")
                                print(f"   Actual: {actual_bullets}")
                                raise ValueError(error_msg)
                            
                            # Compare each bullet
                            for i, (expected, actual) in enumerate(zip(expected_bullets, actual_bullets)):
                                if str(expected).strip() != str(actual).strip():
                                    error_msg = f"MODE 5 EXACT CONTENT violation! Slide {actual_slide_num} bullet {i+1} was modified. Expected: '{expected}', Got: '{actual}'"
                                    print(f"❌ {error_msg}")
                                    raise ValueError(error_msg)
                            
                            print(f"  ✅ MODE 5 EXACT: Slide {actual_slide_num} content verified - {len(actual_bullets)} bullets match exactly")
                        else:
                            error_msg = f"MODE 5 EXACT CONTENT violation! Slide {actual_slide_num} content type mismatch. Expected list, got {type(actual_bullets)}"
                            print(f"❌ {error_msg}")
                            raise ValueError(error_msg)
                        break
        
        print(f"✅ MODE 5: All EXACT content verified - no modifications detected")
        
        return result
    
    def _generate_legacy(self, topic: str, content: str, num_slides: int, 
                        subject: Optional[str], module: Optional[str], 
                        model_type: Optional[ModelType], user_input: Optional[str]) -> Dict:
        """Legacy generation method (fallback)"""
        if model_type is None:
            model_type = "groq_llama"
        
        # Simple generation
        prompt = f"""Generate {num_slides} PowerPoint slides about "{topic}".

SUBJECT: {subject or 'General'}

Each slide must have:
- A descriptive title
- 8-10 bullet points (14-22 words each)

Return JSON:
{{
    "slides": [
        {{"slide_number": 1, "title": "...", "content": ["...", ...]}},
        ...
    ]
}}"""
        
        try:
            result_text = self.model_manager.generate_content(prompt, model_type)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(result_text)
            slides = parsed.get("slides", [])
            
            # Shift slides and add base
            for slide in slides:
                slide["slide_number"] = slide.get("slide_number", 0) + 1
            
            base_slide = {
                "slide_number": 1,
                "slide_type": "title",
                "title": topic,
                "content": [subject or "Educational Presentation"],
                "speaker_notes": f"Introduction to {topic}."
            }
            slides.insert(0, base_slide)
            
            user_slides = [s for s in slides if s.get("slide_number", 0) > 1]
            self._add_image_hints(user_slides, topic, subject)
            
            result = {
                "presentation_title": topic,
                "presentation_subtitle": subject or "Educational Presentation",
                "slides": slides
            }
            
            return self._enforce_bullet_constraints(result)
        except Exception as e:
            print(f"⚠ Legacy generation error: {e}")
            return self._create_fallback_slides(topic, subject, num_slides)
    
    def _create_fallback_slides(self, topic: str, subject: Optional[str], num_slides: int) -> Dict:
        """Create simple fallback slides if LLM generation fails"""
        slides = []
        
        # Base slide
        slides.append({
            "slide_number": 1,
            "slide_type": "title",
            "title": topic,
            "content": [subject or "Educational Presentation"] if subject else ["Generated by EduAssist"],
            "speaker_notes": f"Introduction to the presentation on {topic}."
        })
        
        # User slides
        for i in range(1, num_slides + 1):
            slides.append({
                "slide_number": i + 1,
                "slide_type": "content",
                "title": f"Key Concept {i}",
                "content": [
                    f"Important aspect 1 of {topic}",
                    f"Key point 2 related to {topic}",
                    f"Essential concept 3 about {topic}"
                ],
                "speaker_notes": f"Explain key concept {i} related to {topic}."
            })
        
        return {
            "presentation_title": topic,
            "presentation_subtitle": subject or "Educational Presentation",
            "slides": slides
        }
    
    def _add_image_hints(self, slides: list[dict], topic: str, subject: Optional[str], max_hints: int = 3) -> None:
        """Add image_query hints to intro/title and architecture-like slides.
        
        MODE 5 IMAGE LOCK: Skips slides with image_mode == "NONE"
        """
        if not isinstance(slides, list):
            return
        hints_added = 0
        found_arch = False
        for s in slides:
            # MODE 5 IMAGE LOCK: Skip slides that explicitly forbid images
            if s.get("_mode_5_image_mode") == "NONE" or s.get("_no_image"):
                print(f"🚫 MODE 5 IMAGE LOCK: Skipped image hint for slide {s.get('slide_number')} (No image declared)")
                continue
            
            if hints_added >= max_hints:
                break
            title = (s.get("title") or "").lower()
            if s.get("slide_type") == "title" or "intro" in title or "introduction" in title:
                s["image_query"] = f"{topic} {subject or ''} overview"
                hints_added += 1
            elif any(k in title for k in ["architecture", "diagram", "model", "workflow", "pipeline", "structure", "design"]):
                s["image_query"] = f"{topic} {subject or ''} architecture diagram"
                hints_added += 1
                found_arch = True
        # If no architecture hint was set, force the first content slide to have one
        if not found_arch:
            for s in slides:
                # MODE 5 IMAGE LOCK: Skip slides that explicitly forbid images
                if s.get("_mode_5_image_mode") == "NONE" or s.get("_no_image"):
                    continue
                if s.get("slide_type") == "content":
                    s["image_query"] = f"{topic} {subject or ''} architecture diagram"
                    break

    def _enforce_bullet_constraints(self, slide_data: Dict, max_bullets: int = 10, max_len: int = 140, _mode_5_exact_guard: bool = False) -> Dict:
        """
        Keep bullets concise and slide-ready.
        - Limit bullets per slide to max_bullets.
        - Truncate any bullet longer than max_len characters.
        
        TITLE-PURE: This function NEVER modifies titles, especially for Mode 2.
        EXACT-PURE: This function NEVER modifies EXACT content, especially for Mode 5.
        """
        # TITLE-PURE: Check if this is Mode 2 - if so, store original titles for verification
        is_mode_2 = slide_data.get("_mode_2_title_pure", False)
        original_titles = {}
        if is_mode_2:
            for slide in slide_data.get("slides", []):
                slide_num = slide.get("slide_number", 0)
                if slide_num > 1:  # Skip base slide
                    original_titles[slide_num] = slide.get("title", "")
        
        slides = slide_data.get("slides", [])
        for slide in slides:
            # EXACT-PURE: MODE 5 EXACT CONTENT GUARD - skip modification for EXACT slides
            if _mode_5_exact_guard and slide.get("_is_exact_content", False):
                print(f"  🔒 MODE 5 EXACT: Skipping bullet constraints for slide {slide.get('slide_number')} (EXACT content is LAW)")
                continue  # Skip this slide - EXACT content must not be modified
            
            # TITLE-PURE: NEVER modify titles - only modify content
            content = slide.get("content", [])
            if not isinstance(content, list):
                continue
            trimmed: list[str] = []
            for point in content:
                if not isinstance(point, str):
                    continue
                p = point.strip()
                if len(p) > max_len:
                    p = p[: max_len - 3].rstrip() + "..."
                trimmed.append(p)
                if len(trimmed) >= max_bullets:
                    break
            slide["content"] = trimmed
            
            # TITLE-PURE: Assertion - if Mode 2, title must not be modified
            if is_mode_2:
                slide_num = slide.get("slide_number", 0)
                if slide_num > 1:  # Skip base slide
                    original_title = original_titles.get(slide_num)
                    current_title = slide.get("title", "")
                    if original_title and current_title != original_title:
                        error_msg = f"TITLE-PURE violation! _enforce_bullet_constraints modified Mode 2 title. Slide {slide_num} title changed from '{original_title}' to '{current_title}'. This is FORBIDDEN."
                        print(f"❌ {error_msg}")
                        raise ValueError(error_msg)
        
        return slide_data
    
    def generate_slides_for_topics(self, topics: list[str], subject: str, total_slides: Optional[int] = None, 
                                   min_slides_per_topic: int = 3, model_type: Optional[ModelType] = None, 
                                   user_input: Optional[str] = None, custom_slides: Optional[List[Dict]] = None, 
                                   slide_structure: Optional[List[Dict]] = None) -> dict:
        """Generate multiple slides per topic - simplified version"""
        # Detect model preference
        if model_type is None:
            combined_input = f"{subject} {' '.join(topics)} {user_input or ''}"
            model_type = self.model_manager.detect_model_preference(combined_input, self.default_model)
        
        slides = []
        slide_num = 1
        
        # Base slide
        slides.append({
            "slide_number": slide_num,
            "slide_type": "title",
            "title": f"{subject} - Topics Overview",
            "content": ["Generated by EduAssist PPT Agent"],
            "speaker_notes": f"Welcome to the {subject} presentation covering multiple topics. Today we'll explore: {', '.join(topics)}."
        })
        slide_num += 1
        
        # Calculate slides per topic
        num_topics = max(1, len(topics))
        if total_slides and total_slides > 1:
            remaining = max(0, total_slides - 1)
            per_topic = max(min_slides_per_topic, remaining // num_topics)
        else:
            per_topic = max(min_slides_per_topic, 3)

        # Generate slides for each topic
        for topic in topics:
            for part in range(1, per_topic + 1):
                prompt = f"""Generate a PowerPoint slide about '{topic}' for subject '{subject}'.

REQUIREMENTS:
- Title: Descriptive title for part {part}
- 8-10 bullet points (14-22 words each)
- Speaker notes (2-4 sentences)

Return ONLY JSON:
{{
  "slide_type": "content",
  "title": "<Title>",
  "content": ["bullet 1", "bullet 2", ...],
  "speaker_notes": "..."
}}"""
                result_text = self.model_manager.generate_content(prompt, model_type)
                try:
                    if "```json" in result_text:
                        result_text = result_text.split("```json")[1].split("```", 1)[0].strip()
                    elif "```" in result_text:
                        result_text = result_text.split("```",1)[1].split("```",1)[0].strip()
                    slide_obj = json.loads(result_text)
                    slide_obj["slide_number"] = slide_num
                    slides.append(slide_obj)
                except Exception:
                    slides.append({
                        "slide_number": slide_num,
                        "slide_type": "content",
                        "title": f"{topic} - Part {part}",
                        "content": [f"Key point about {topic}"],
                        "speaker_notes": ""
                    })
                slide_num += 1
        
        # Add image hints
        self._add_image_hints(slides, ", ".join(topics), subject)
        
        result = self._enforce_bullet_constraints({
            "presentation_title": subject or "Topics Presentation",
            "presentation_subtitle": "Generated for: " + ", ".join(topics),
            "slides": slides
        })
        
        return result
