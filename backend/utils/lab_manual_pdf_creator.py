"""
Lab Manual PDF Creator - Creates professional PDF lab manuals from structured data
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
        KeepTogether
    )
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class LabManualPDFCreator:
    """Creates professional PDF lab manuals from structured lab manual data"""
    
    def __init__(self, storage_dir: str = "storage/lab_manuals"):
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
        """Setup custom paragraph styles for lab manuals"""
        # Title style - Large, bold, centered
        self.title_style = ParagraphStyle(
            'LabTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#000000'),
            spaceAfter=8,
            spaceBefore=0,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=26
        )
        
        # Course code style
        self.course_code_style = ParagraphStyle(
            'CourseCode',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Section header style
        self.section_style = ParagraphStyle(
            'LabSection',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#000000'),
            spaceAfter=10,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            leading=18,
            leftIndent=0
        )
        
        # Subsection style
        self.subsection_style = ParagraphStyle(
            'LabSubsection',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#000000'),
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            leading=16
        )
        
        # Module heading style
        self.module_style = ParagraphStyle(
            'ModuleHeading',
            parent=self.styles['Heading2'],
            fontSize=15,
            textColor=colors.HexColor('#000000'),
            spaceAfter=8,
            spaceBefore=16,
            fontName='Helvetica-Bold',
            leading=17,
            leftIndent=0
        )
        
        # Experiment heading style
        self.experiment_style = ParagraphStyle(
            'ExperimentHeading',
            parent=self.styles['Heading3'],
            fontSize=13,
            textColor=colors.HexColor('#000000'),
            spaceAfter=6,
            spaceBefore=10,
            fontName='Helvetica-Bold',
            leading=15
        )
        
        # Body text style - ensure proper wrapping
        self.body_style = ParagraphStyle(
            'LabBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#000000'),
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName='Helvetica',
            leading=13,
            wordWrap='CJK'  # Enable word wrapping
        )
        
        # Bullet point style
        self.bullet_style = ParagraphStyle(
            'LabBullet',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#000000'),
            spaceAfter=4,
            spaceBefore=2,
            leftIndent=20,
            bulletIndent=10,
            fontName='Helvetica',
            leading=13
        )
        
        # Objective/Description style
        self.objective_style = ParagraphStyle(
            'LabObjective',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
            spaceBefore=4,
            leftIndent=15,
            fontName='Helvetica',
            leading=13,
            fontStyle='italic'
        )
    
    def create_lab_manual_pdf(
        self,
        manual_data: Dict,
        filename: Optional[str] = None
    ) -> str:
        """
        Create a PDF lab manual from structured lab manual data
        
        Args:
            manual_data: Dictionary containing lab manual structure
            filename: Optional custom filename
            
        Returns:
            Path to the created PDF file
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is not available")
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_subject = "".join(c for c in manual_data.get("subject", "LabManual") if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_subject}_{timestamp}.pdf"
        
        # Ensure filename ends with .pdf
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        
        file_path = self.storage_dir / filename
        
        # Create PDF document
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
        
        # Add header/title
        self._add_header(story, manual_data)
        
        # Add prerequisites
        prerequisites = manual_data.get("prerequisites", "")
        if prerequisites:
            self._add_prerequisites(story, prerequisites)
        
        # Add lab objectives
        lab_objectives = manual_data.get("lab_objectives", [])
        if lab_objectives:
            self._add_lab_objectives(story, lab_objectives)
        
        # Add lab outcomes
        lab_outcomes = manual_data.get("lab_outcomes", [])
        if lab_outcomes:
            self._add_lab_outcomes(story, lab_outcomes)
        
        # Add experiments list
        self._add_experiments_list(story, manual_data)
        
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
    
    def _add_header(self, story, manual_data):
        """Add professional header section"""
        subject = manual_data.get("subject", "Lab Manual")
        course_code = manual_data.get("course_code")
        
        # Title in a bordered box
        title_data = [
            [Paragraph(f"<b>{subject}</b>", self.title_style)]
        ]
        
        title_table = Table(title_data, colWidths=[6.5*inch])
        title_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f0f0')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#000000')),
        ]))
        story.append(title_table)
        story.append(Spacer(1, 0.1 * inch))
        
        # Course code
        if course_code and course_code != "N/A":
            story.append(Paragraph(f"<b>Course Code:</b> {course_code}", self.course_code_style))
            story.append(Spacer(1, 0.2 * inch))
    
    def _add_prerequisites(self, story, prerequisites):
        """Add prerequisites section"""
        # Section header with line
        section_header = Table([
            [Paragraph("PREREQUISITES", self.section_style)]
        ], colWidths=[6.5*inch])
        section_header.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#000000')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8e8e8')),
        ]))
        story.append(section_header)
        story.append(Spacer(1, 0.1 * inch))
        
        # Prerequisites text - handle long text properly
        # Split long text into paragraphs if needed
        prereq_paragraphs = prerequisites.split('\n') if prerequisites else []
        if prereq_paragraphs:
            for para in prereq_paragraphs:
                if para.strip():
                    # Escape HTML special characters and wrap text
                    escaped_text = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(escaped_text, self.body_style))
        else:
            if prerequisites:
                escaped_text = prerequisites.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(escaped_text, self.body_style))
        story.append(Spacer(1, 0.2 * inch))
    
    def _add_lab_objectives(self, story, lab_objectives):
        """Add lab objectives section"""
        # Section header
        section_header = Table([
            [Paragraph("LAB OBJECTIVES", self.section_style)]
        ], colWidths=[6.5*inch])
        section_header.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#000000')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8e8e8')),
        ]))
        story.append(section_header)
        story.append(Spacer(1, 0.1 * inch))
        
        # Objectives as bullet points - handle long text
        for obj in lab_objectives:
            if obj.strip():
                # Escape HTML and ensure full text is displayed
                escaped_obj = obj.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(f"• {escaped_obj}", self.bullet_style))
        
        story.append(Spacer(1, 0.2 * inch))
    
    def _add_lab_outcomes(self, story, lab_outcomes):
        """Add lab outcomes section"""
        # Section header
        section_header = Table([
            [Paragraph("LAB OUTCOMES", self.section_style)]
        ], colWidths=[6.5*inch])
        section_header.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#000000')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8e8e8')),
        ]))
        story.append(section_header)
        story.append(Spacer(1, 0.1 * inch))
        
        # Outcomes introduction
        story.append(Paragraph("At the end of the course, the students will be able to:", self.body_style))
        story.append(Spacer(1, 0.1 * inch))
        
        # Outcomes as bullet points - handle long text
        for outcome in lab_outcomes:
            if outcome.strip():
                # Escape HTML and ensure full text is displayed
                escaped_outcome = outcome.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(f"• {escaped_outcome}", self.bullet_style))
        
        story.append(Spacer(1, 0.2 * inch))
    
    def _add_experiments_list(self, story, manual_data):
        """Add experiments list section"""
        # Section header
        section_header = Table([
            [Paragraph("SUGGESTED LIST OF EXPERIMENTS", self.section_style)]
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
        
        # Modules
        modules = manual_data.get("modules", [])
        for module in modules:
            module_num = module.get("module_number", 0)
            module_title = module.get("module_title", f"Module {module_num}")
            selection_req = module.get("selection_requirement", "All")
            
            # Module heading
            if selection_req == "All":
                module_heading = f"Module {module_num}: {module_title}"
            else:
                module_heading = f"Module {module_num} ({selection_req}): {module_title}"
            
            # Module header with background
            module_header = Table([
                [Paragraph(module_heading, self.module_style)]
            ], colWidths=[6.5*inch])
            module_header.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ]))
            story.append(module_header)
            story.append(Spacer(1, 0.1 * inch))
            
            # Experiments
            experiments = module.get("experiments", [])
            for exp in experiments:
                exp_num = exp.get("experiment_number", 0)
                exp_title = exp.get("title", "")
                exp_objective = exp.get("objective", "")
                exp_description = exp.get("description", "")
                
                # Experiment heading - escape HTML
                escaped_title = exp_title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                exp_heading_text = f"Experiment {exp_num}: {escaped_title}"
                story.append(Paragraph(exp_heading_text, self.experiment_style))
                
                # Objective - handle long text
                if exp_objective:
                    escaped_obj = exp_objective.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(f"<b>Objective:</b> {escaped_obj}", self.objective_style))
                
                # Description - handle long text and line breaks
                if exp_description:
                    # Split by line breaks and create separate paragraphs
                    desc_paragraphs = exp_description.split('\n') if exp_description else []
                    if desc_paragraphs:
                        for para in desc_paragraphs:
                            if para.strip():
                                escaped_desc = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                # Format bullet points and numbered lists
                                if para.strip().startswith('-') or para.strip().startswith('*'):
                                    # Convert to HTML bullet list
                                    escaped_desc = escaped_desc.lstrip('-*').strip()
                                    escaped_desc = f"• {escaped_desc}"
                                elif para.strip() and para.strip()[0].isdigit() and '.' in para.strip()[:3]:
                                    # Keep numbered lists as-is but add spacing
                                    pass
                                story.append(Paragraph(escaped_desc, self.body_style))
                    else:
                        escaped_desc = exp_description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(escaped_desc, self.body_style))
                
                story.append(Spacer(1, 0.15 * inch))
            
            story.append(Spacer(1, 0.2 * inch))
