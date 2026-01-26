"""
PDF Creator - Creates PDF question papers from structured question data
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
        KeepTogether, HRFlowable, PageTemplate, Frame, BaseDocTemplate
    )
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
    from reportlab.platypus.frames import Frame
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class PDFCreator:
    """Creates PDF question papers from structured question data"""
    
    def __init__(self, storage_dir: str = "storage/question_papers"):
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab is required for PDF creation. Install with: pip install reportlab"
            )
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.styles = getSampleStyleSheet()
        
        # Define custom styles
        self._setup_styles()
    
    def _setup_styles(self):
        """Setup custom paragraph styles for question papers"""
        # Title style - Large, bold, centered
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#000000'),
            spaceAfter=8,
            spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=24
        )
        
        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        # Section header style - Bold with underline effect
        self.section_style = ParagraphStyle(
            'CustomSection',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#000000'),
            spaceAfter=10,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            leading=18,
            borderWidth=0,
            borderPadding=0
        )
        
        # Question style - Bold, larger font
        self.question_style = ParagraphStyle(
            'CustomQuestion',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#000000'),
            spaceAfter=8,
            spaceBefore=12,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
            leading=14,
            leftIndent=0
        )
        
        # Question number style
        self.question_num_style = ParagraphStyle(
            'CustomQuestionNum',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#000000'),
            spaceAfter=0,
            spaceBefore=0,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        # Option style - Indented, regular font
        self.option_style = ParagraphStyle(
            'CustomOption',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#000000'),
            spaceAfter=4,
            spaceBefore=2,
            leftIndent=30,
            fontName='Helvetica',
            leading=13
        )
        
        # Marks style - Right aligned, smaller
        self.marks_style = ParagraphStyle(
            'CustomMarks',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=0,
            alignment=TA_RIGHT,
            fontName='Helvetica'
        )
        
        # Instructions style
        self.instruction_style = ParagraphStyle(
            'CustomInstruction',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#000000'),
            spaceAfter=4,
            spaceBefore=2,
            alignment=TA_LEFT,
            fontName='Helvetica',
            leftIndent=0
        )
        
        # Metadata style
        self.metadata_style = ParagraphStyle(
            'CustomMetadata',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#000000'),
            spaceAfter=4,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )
    
    def create_question_paper(
        self,
        questions_data: Dict,
        total_marks: int = 100,
        difficulty: str = "medium",
        filename: Optional[str] = None,
        subject: Optional[str] = None,
        course_code: Optional[str] = None,
        duration: Optional[str] = None
    ) -> str:
        """
        Create a PDF question paper from structured question data
        
        Args:
            questions_data: Dictionary containing questions in format:
                {
                    "mcq_questions": [...],
                    "short_answer_questions": [...],
                    "long_answer_questions": [...],
                    "set_number": 1 (optional),
                    "set_name": "Set A" (optional)
                }
            total_marks: Total marks for the paper
            difficulty: Difficulty level
            filename: Optional custom filename
            subject: Optional subject name
            course_code: Optional course code
            duration: Optional exam duration
            
        Returns:
            Path to the created PDF file
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is not available")
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            set_info = ""
            if questions_data.get("set_number"):
                set_info = f"_Set_{questions_data.get('set_number')}"
            filename = f"Question_Paper{set_info}_{timestamp}.pdf"
        
        # Ensure filename ends with .pdf
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        
        file_path = self.storage_dir / filename
        
        # Create PDF document with custom page template for page numbers
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )
        
        # Build story (content)
        story = []
        
        # Add professional header/title with border
        self._add_header(story, questions_data, subject, course_code, total_marks, duration)
        
        # Add instructions in a box
        self._add_instructions(story, difficulty)
        
        story.append(Spacer(1, 0.3 * inch))
        
        # Track question numbers
        self.question_counter = 0
        
        # Add MCQ questions
        mcq_questions = questions_data.get("mcq_questions", [])
        if mcq_questions:
            self._add_mcq_section(story, mcq_questions)
        
        # Add Short Answer questions
        short_questions = questions_data.get("short_answer_questions", [])
        if short_questions:
            self._add_short_answer_section(story, short_questions)
        
        # Add Long Answer questions
        long_questions = questions_data.get("long_answer_questions", [])
        if long_questions:
            self._add_long_answer_section(story, long_questions)
        
        # Build PDF with page numbers
        def add_page_number(canvas, doc):
            """Add page number to each page"""
            page_num = canvas.getPageNumber()
            text = f"Page {page_num}"
            canvas.saveState()
            canvas.setFont('Helvetica', 9)
            canvas.setFillColor(colors.grey)
            canvas.drawRightString(doc.pagesize[0] - 2*cm, 1.5*cm, text)
            canvas.restoreState()
        
        doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
        
        return str(file_path)
    
    def _add_header(self, story, questions_data, subject, course_code, total_marks, duration):
        """Add professional header section with border"""
        # Title
        title = subject or "Question Paper"
        if course_code:
            title = f"{course_code} - {title}"
        
        set_info = ""
        if questions_data.get("set_number"):
            set_info = f" (Set {questions_data.get('set_number')})"
        if questions_data.get("set_name"):
            set_info = f" ({questions_data.get('set_name')})"
        
        # Create header table with border
        header_data = [
            [Paragraph(f"<b>{title}{set_info}</b>", self.title_style)]
        ]
        
        header_table = Table(header_data, colWidths=[6.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f0f0')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#000000')),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#000000')),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.15 * inch))
        
        # Metadata in a clean table
        metadata_rows = [
            [Paragraph("<b>Total Marks:</b>", self.metadata_style), 
             Paragraph(str(total_marks), self.metadata_style)]
        ]
        if duration:
            metadata_rows.append([
                Paragraph("<b>Duration:</b>", self.metadata_style),
                Paragraph(duration, self.metadata_style)
            ])
        
        metadata_table = Table(metadata_rows, colWidths=[2.5*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 0.2 * inch))
    
    def _add_instructions(self, story, difficulty):
        """Add instructions section in a bordered box"""
        instructions_data = [
            [Paragraph("<b>INSTRUCTIONS</b>", ParagraphStyle(
                'InstructionTitle',
                parent=self.styles['Normal'],
                fontSize=12,
                fontName='Helvetica-Bold',
                alignment=TA_LEFT
            ))]
        ]
        
        instructions_list = [
            "1. Answer all questions.",
            "2. Write clearly and legibly.",
            f"3. Difficulty Level: <b>{difficulty.capitalize()}</b>",
            "4. Read all questions carefully before answering.",
            "5. All questions are compulsory.",
        ]
        
        for instruction in instructions_list:
            instructions_data.append([
                Paragraph(instruction, self.instruction_style)
            ])
        
        instructions_table = Table(instructions_data, colWidths=[6.5*inch])
        instructions_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#999999')),
        ]))
        story.append(instructions_table)
        story.append(Spacer(1, 0.25 * inch))
    
    def _add_mcq_section(self, story, mcq_questions):
        """Add MCQ questions section with professional formatting"""
        # Section header with line
        section_header = Table([
            [Paragraph("SECTION A: MULTIPLE CHOICE QUESTIONS", self.section_style)]
        ], colWidths=[6.5*inch])
        section_header.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#000000')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8e8e8')),
        ]))
        story.append(section_header)
        story.append(Spacer(1, 0.15 * inch))
        
        for idx, q in enumerate(mcq_questions, 1):
            self.question_counter += 1
            question_num = self.question_counter
            
            # Question text with marks
            question_text = q.get("question", "")
            marks = q.get("marks", 1)
            
            # Create question row with number and marks
            question_data = [
                [
                    Paragraph(f"Q{question_num}.", self.question_num_style),
                    Paragraph(question_text, self.question_style),
                    Paragraph(f"[{marks} mark{'s' if marks != 1 else ''}]", self.marks_style)
                ]
            ]
            
            question_table = Table(question_data, colWidths=[0.5*inch, 5*inch, 1*inch])
            question_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(question_table)
            
            # Options in a clean format
            options = q.get("options", [])
            option_labels = ["a)", "b)", "c)", "d)"]
            
            for opt_idx, option in enumerate(options[:4]):  # Limit to 4 options
                story.append(Paragraph(
                    f"<b>{option_labels[opt_idx]}</b> {option}",
                    self.option_style
                ))
            
            story.append(Spacer(1, 0.2 * inch))
    
    def _add_short_answer_section(self, story, short_questions):
        """Add Short Answer questions section with answer space"""
        story.append(PageBreak())
        
        # Section header
        section_header = Table([
            [Paragraph("SECTION B: SHORT ANSWER QUESTIONS", self.section_style)]
        ], colWidths=[6.5*inch])
        section_header.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#000000')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8e8e8')),
        ]))
        story.append(section_header)
        story.append(Spacer(1, 0.15 * inch))
        
        for q in short_questions:
            self.question_counter += 1
            question_num = self.question_counter
            
            question_text = q.get("question", "")
            marks = q.get("marks", 3)
            
            # Question with marks
            question_data = [
                [
                    Paragraph(f"Q{question_num}.", self.question_num_style),
                    Paragraph(question_text, self.question_style),
                    Paragraph(f"[{marks} marks]", self.marks_style)
                ]
            ]
            
            question_table = Table(question_data, colWidths=[0.5*inch, 5*inch, 1*inch])
            question_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(question_table)
            
            # Answer space box
            answer_space = Table([
                [Paragraph("", ParagraphStyle('AnswerSpace', fontSize=10))]
            ], colWidths=[6.5*inch], rowHeights=[0.8*inch])
            answer_space.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(answer_space)
            story.append(Spacer(1, 0.2 * inch))
    
    def _add_long_answer_section(self, story, long_questions):
        """Add Long Answer questions section with larger answer space"""
        story.append(PageBreak())
        
        # Section header
        section_header = Table([
            [Paragraph("SECTION C: LONG ANSWER QUESTIONS", self.section_style)]
        ], colWidths=[6.5*inch])
        section_header.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#000000')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8e8e8')),
        ]))
        story.append(section_header)
        story.append(Spacer(1, 0.15 * inch))
        
        for q in long_questions:
            self.question_counter += 1
            question_num = self.question_counter
            
            question_text = q.get("question", "")
            marks = q.get("marks", 5)
            
            # Question with marks
            question_data = [
                [
                    Paragraph(f"Q{question_num}.", self.question_num_style),
                    Paragraph(question_text, self.question_style),
                    Paragraph(f"[{marks} marks]", self.marks_style)
                ]
            ]
            
            question_table = Table(question_data, colWidths=[0.5*inch, 5*inch, 1*inch])
            question_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(question_table)
            
            # Larger answer space box for long answers
            answer_space = Table([
                [Paragraph("", ParagraphStyle('AnswerSpace', fontSize=10))]
            ], colWidths=[6.5*inch], rowHeights=[2*inch])
            answer_space.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(answer_space)
            story.append(Spacer(1, 0.25 * inch))
