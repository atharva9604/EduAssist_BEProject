import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from pptx import Presentation
from pptx.util import Inches
from pptx.enum.shapes import PP_PLACEHOLDER


class PPTCreator:
    """Creates PowerPoint presentations from structured content data"""

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

    # ==========================================================
    # MAIN FUNCTION
    # ==========================================================
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

            # ================= TEMPLATE MODE =================
            if self.template_path.exists():
                print(f"🎨 Using template: {self.template_path}")
                prs = Presentation(str(self.template_path))

                title_layout = prs.slide_layouts[0]
                content_layout = prs.slide_layouts[1]
                thank_layout = prs.slide_layouts[2] if len(prs.slide_layouts) > 2 else None

                # 1️⃣ Title Slide
                title_slide_data = next(
                    (s for s in slides_data if s.get("slide_type") == "title"),
                    None,
                )

                if title_slide_data:
                    slide = prs.slides.add_slide(title_layout)
                    self._fill_title_slide(slide, title_slide_data, content_data)

                # 2️⃣ Content Slides
                for slide_data in slides_data:
                    if slide_data.get("slide_type") != "title":
                        slide = prs.slides.add_slide(content_layout)
                        self._fill_content_slide(slide, slide_data)

                # 3️⃣ Thank You Slide
                if thank_layout:
                    slide = prs.slides.add_slide(thank_layout)
                    self._fill_thankyou_slide(slide)

            # ================= NO TEMPLATE MODE =================
            else:
                print("⚠️ Template not found. Using default theme.")
                prs = Presentation()

                for slide_data in slides_data:
                    slide_type = slide_data.get("slide_type", "content")

                    if slide_type == "title":
                        slide = prs.slides.add_slide(prs.slide_layouts[0])
                        self._fill_title_slide(slide, slide_data, content_data)
                    else:
                        slide = prs.slides.add_slide(prs.slide_layouts[1])
                        self._fill_content_slide(slide, slide_data)

            file_path = self.storage_dir / filename
            prs.save(str(file_path))

            return str(file_path)

        except Exception as e:
            print(f"❌ Error creating presentation: {e}")
            raise e

    # ==========================================================
    # TITLE SLIDE
    # ==========================================================
    def _fill_title_slide(self, slide, slide_data: Dict, content_data: Dict):

        if slide.shapes.title:
            slide.shapes.title.text = content_data.get(
                "presentation_title",
                slide_data.get("title", "Presentation"),
            )

        subtitle = content_data.get("presentation_subtitle", "")

        for shape in slide.placeholders:
            if (
                shape.placeholder_format.type == PP_PLACEHOLDER.SUBTITLE
                and shape.has_text_frame
            ):
                shape.text_frame.clear()
                shape.text_frame.text = subtitle
                break

    # ==========================================================
    # CONTENT SLIDE
    # ==========================================================
    def _fill_content_slide(self, slide, slide_data: Dict):

        # ---- FIXED TITLE ISSUE ----
        if slide.shapes.title:
            slide.shapes.title.text = slide_data.get("title", "Slide Title")

        # ---- PROPER BODY PLACEHOLDER DETECTION ----
        content_shape = None

        for shape in slide.placeholders:
            if (
                shape.placeholder_format.type == PP_PLACEHOLDER.BODY
                and shape.has_text_frame
            ):
                content_shape = shape
                break

        # fallback (if template is weird)
        if not content_shape:
            for shape in slide.placeholders:
                if shape.has_text_frame and shape != slide.shapes.title:
                    content_shape = shape
                    break

        if content_shape:
            tf = content_shape.text_frame
            tf.clear()

            for i, point in enumerate(slide_data.get("content", [])):
                if i == 0:
                    p = tf.paragraphs[0]
                else:
                    p = tf.add_paragraph()
                p.text = point
                p.level = 0

        self._add_image_to_slide(slide, slide_data)
        self._add_speaker_notes(slide, slide_data)

    # ==========================================================
    # THANK YOU SLIDE
    # ==========================================================
    def _fill_thankyou_slide(self, slide):

        thank_text = "Thank You"

        # Use title if exists
        if slide.shapes.title:
            slide.shapes.title.text = thank_text
            return

        # Otherwise use first text placeholder
        for shape in slide.placeholders:
            if shape.has_text_frame:
                shape.text_frame.clear()
                shape.text_frame.text = thank_text
                return

        # Ultimate fallback
        txBox = slide.shapes.add_textbox(
            Inches(4),
            Inches(3),
            Inches(5),
            Inches(1),
        )
        tf = txBox.text_frame
        tf.text = thank_text

    # ==========================================================
    # IMAGE
    # ==========================================================
    def _add_image_to_slide(self, slide, slide_data: Dict):

        image_path = slide_data.get("image_path")

        if image_path and os.path.exists(image_path):
            try:
                slide.shapes.add_picture(
                    image_path,
                    left=Inches(8.0),
                    top=Inches(2.0),
                    width=Inches(4.5),
                )
            except Exception as e:
                print(f"⚠️ Image add failed: {e}")

    # ==========================================================
    # NOTES
    # ==========================================================
    def _add_speaker_notes(self, slide, slide_data: Dict):

        speaker_notes = slide_data.get("speaker_notes", "")

        if speaker_notes:
            try:
                notes = slide.notes_slide.notes_text_frame
                notes.text = speaker_notes
            except Exception:
                pass

    # ==========================================================
    # UTILITIES
    # ==========================================================
    def get_presentation_info(self, file_path: str) -> Dict:
        try:
            prs = Presentation(file_path)
            return {
                "file_path": file_path,
                "filename": os.path.basename(file_path),
                "num_slides": len(prs.slides),
                "file_size": os.path.getsize(file_path),
            }
        except Exception as e:
            return {"error": str(e)}

    def list_presentations(self) -> List[Dict]:
        presentations = []

        for file_path in self.storage_dir.glob("*.pptx"):
            info = self.get_presentation_info(str(file_path))
            if "error" not in info:
                presentations.append(info)

        return presentations