import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

class PPTCreator:
    """Creates PowerPoint presentations with professional academic aesthetics"""

    def __init__(
        self,
        storage_dir: str = "storage/presentations",
        template_dir: str = "storage/templates",
    ):
        base_dir = os.getcwd()
        if "backend" not in base_dir and os.path.exists("backend"):
            base_dir = os.path.join(base_dir, "backend")

        self.storage_dir = Path(base_dir) / storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.template_dir = Path(base_dir) / template_dir
        self.template_dir.mkdir(parents=True, exist_ok=True)

        self.template_path = self.template_dir / "template.pptx"
        
        # Professional Color Palette
        self.PRIMARY_COLOR = RGBColor(0, 32, 96)  # Deep Navy Blue
        self.ACCENT_COLOR = RGBColor(0, 112, 192)   # Academic Blue

    def create_presentation(self, content_data: Dict, filename: str = None) -> str:
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_title = "".join(
                    c
                    for c in content_data.get("presentation_title", "Presentation")
                    if c.isalnum() or c in (" ", "-", "_")
                ).rstrip()
                filename = f"{safe_title}_{timestamp}.pptx"

            slides_data = content_data.get("slides", [])

            # Initialize Presentation
            if self.template_path.exists():
                print(f"🎨 Using template: {self.template_path}")
                prs = Presentation(str(self.template_path))
            else:
                print("✨ Creating premium 16:9 presentation from scratch")
                prs = Presentation()
                # Set 16:9 Widescreen Aspect Ratio
                prs.slide_width = Inches(13.33)
                prs.slide_height = Inches(7.5)

            # Process Slides
            for slide_data in slides_data:
                slide_type = slide_data.get("slide_type", "content")
                
                if slide_type == "title":
                    layout = prs.slide_layouts[0]
                    slide = prs.slides.add_slide(layout)
                    self._fill_title_slide(slide, slide_data, content_data)
                else:
                    layout = prs.slide_layouts[1]
                    slide = prs.slides.add_slide(layout)
                    self._fill_content_slide(slide, slide_data)

            # Add Thank You slide if it's a long presentation
            if len(slides_data) > 3:
                thank_layout = prs.slide_layouts[2] if len(prs.slide_layouts) > 2 else prs.slide_layouts[0]
                slide = prs.slides.add_slide(thank_layout)
                self._fill_thankyou_slide(slide)

            file_path = self.storage_dir / filename
            prs.save(str(file_path))
            return str(file_path)

        except Exception as e:
            print(f"❌ Error creating presentation: {e}")
            raise e

    def _fill_title_slide(self, slide, slide_data: Dict, content_data: Dict):
        title_text = content_data.get("presentation_title", slide_data.get("title", "Presentation"))
        subtitle_text = content_data.get("presentation_subtitle", "")

        if slide.shapes.title:
            slide.shapes.title.text = title_text
            # Style title
            for paragraph in slide.shapes.title.text_frame.paragraphs:
                paragraph.font.size = Pt(44)
                paragraph.font.bold = True
                paragraph.font.color.rgb = self.PRIMARY_COLOR
                paragraph.font.name = 'Calibri'

        for shape in slide.placeholders:
            if shape.placeholder_format.type == PP_PLACEHOLDER.SUBTITLE and shape.has_text_frame:
                shape.text_frame.text = subtitle_text
                for paragraph in shape.text_frame.paragraphs:
                    paragraph.font.size = Pt(24)
                    paragraph.font.italic = True
                    paragraph.font.color.rgb = RGBColor(80, 80, 80)
                    paragraph.font.name = 'Calibri'

    def _fill_content_slide(self, slide, slide_data: Dict):
        # 1. Slide Title
        if slide.shapes.title:
            slide.shapes.title.text = slide_data.get("title", "Slide Title")
            for paragraph in slide.shapes.title.text_frame.paragraphs:
                paragraph.font.size = Pt(32)
                paragraph.font.bold = True
                paragraph.font.color.rgb = self.PRIMARY_COLOR
                paragraph.font.name = 'Calibri'
            
            # Add a subtle footer-like line below title
            title_bottom = slide.shapes.title.top + slide.shapes.title.height
            slide.shapes.add_connector(
                1, # Straight line
                Inches(0.5), title_bottom, 
                Inches(12.8), title_bottom
            ).line.color.rgb = self.ACCENT_COLOR

        # 2. Body Placeholder Detection
        content_shape = None
        for shape in slide.placeholders:
            if shape.placeholder_format.type == PP_PLACEHOLDER.BODY and shape.has_text_frame:
                content_shape = shape
                break
        
        if not content_shape:
            for shape in slide.placeholders:
                if shape.has_text_frame and shape != slide.shapes.title:
                    content_shape = shape
                    break

        # 3. Handle Content and Image Alignment
        has_image = bool(slide_data.get("image_path") and os.path.exists(slide_data.get("image_path")))
        
        if content_shape:
            tf = content_shape.text_frame
            tf.clear()
            tf.word_wrap = True
            
            # Adjust content width if image exists (Two-column layout)
            if has_image:
                content_shape.width = Inches(7.5)
                content_shape.left = Inches(0.5)
            else:
                content_shape.width = Inches(12.3)
                content_shape.left = Inches(0.5)

            for i, point in enumerate(slide_data.get("content", [])):
                p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
                p.text = str(point)
                p.level = 0
                p.font.size = Pt(18)
                p.font.name = 'Calibri'
                p.space_after = Pt(10)

        if has_image:
            self._add_image_to_slide(slide, slide_data)
        
        self._add_speaker_notes(slide, slide_data)

    def _add_image_to_slide(self, slide, slide_data: Dict):
        image_path = slide_data.get("image_path")
        if image_path and os.path.exists(image_path):
            try:
                # Professional placement: Right side, vertically centered
                slide.shapes.add_picture(
                    image_path,
                    left=Inches(8.5),
                    top=Inches(2.0),
                    width=Inches(4.3),
                )
            except Exception as e:
                print(f"⚠️ Image add failed: {e}")

    def _fill_thankyou_slide(self, slide):
        thank_text = "Thank You"
        if slide.shapes.title:
            slide.shapes.title.text = thank_text
            for paragraph in slide.shapes.title.text_frame.paragraphs:
                paragraph.font.size = Pt(60)
                paragraph.font.bold = True
                paragraph.font.color.rgb = self.PRIMARY_COLOR
                paragraph.alignment = PP_ALIGN.CENTER

    def _add_speaker_notes(self, slide, slide_data: Dict):
        speaker_notes = slide_data.get("speaker_notes", "")
        if speaker_notes:
            try:
                slide.notes_slide.notes_text_frame.text = speaker_notes
            except Exception:
                pass

    def get_presentation_info(self, file_path: str) -> Dict:
        try:
            prs = Presentation(file_path)
            # Use file modification time or creation time for 'created_at'
            # st_mtime is more reliable across platforms
            mtime = os.path.getmtime(file_path)
            dt_mtime = datetime.fromtimestamp(mtime)
            
            return {
                "file_path": file_path,
                "filename": os.path.basename(file_path),
                "num_slides": len(prs.slides),
                "file_size": os.path.getsize(file_path),
                "created_at": dt_mtime.isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_presentations(self) -> List[Dict]:
        presentations = []
        if not self.storage_dir.exists():
            return []
            
        for file_path in self.storage_dir.glob("*.pptx"):
            info = self.get_presentation_info(str(file_path))
            if "error" not in info:
                presentations.append(info)

        # Sort by created_at descending (newest first)
        return sorted(
            presentations, 
            key=lambda x: x.get("created_at", ""), 
            reverse=True
        )
