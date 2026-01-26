import os
import json
from dotenv import load_dotenv
from typing import Dict, List, Optional
from pathlib import Path
from pypdf import PdfReader

load_dotenv()

# Configure Gemini
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")
genai_client = genai.Client(api_key=API_KEY)

class LabManualGenerator:
    """Lab Manual Generator Agent that parses PDF and generates structured lab manuals"""
    
    def __init__(self):
        # Use gemini-2.5-flash for free tier (has quota, unlike gemini-2.5-pro which has limit 0)
        # gemini-pro-latest maps to gemini-2.5-pro which has quota limit 0 on free tier
        # gemini-2.5-flash is free tier compatible and works well
        self.model = os.getenv("LAB_MANUAL_MODEL", "gemini-2.5-flash")
    
    def generate_lab_manual_from_pdf(self, pdf_path: str, num_modules: int = 5) -> Dict:
        """
        Parse PDF and generate a complete lab manual.
        
        Args:
            pdf_path: Path to the PDF file containing prerequisites, objectives, and outcomes
            num_modules: Number of modules to generate (default: 5)
            
        Returns:
            Dictionary with complete lab manual structure including modules and experiments
        """
        try:
            # Step 1: Extract text from PDF
            try:
                reader = PdfReader(pdf_path)
            except Exception as e:
                raise ValueError(f"Failed to read PDF file: {str(e)}. The PDF may be corrupted or encrypted.")
            
            # Check if PDF is encrypted
            if reader.is_encrypted:
                try:
                    reader.decrypt("")  # Try empty password
                except Exception:
                    raise ValueError("PDF is encrypted/password protected. Please provide an unencrypted PDF.")
            
            full_text = ""
            total_pages = len(reader.pages)
            
            if total_pages == 0:
                raise ValueError("PDF has no pages")
            
            print(f"Processing PDF with {total_pages} page(s)...")
            
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        full_text += page_text + "\n"
                        print(f"Extracted {len(page_text)} characters from page {i+1}")
                    else:
                        print(f"Warning: Page {i+1} returned empty text")
                except Exception as e:
                    print(f"Warning: Could not extract text from page {i+1}: {e}")
                    continue
            
            print(f"Total extracted text length: {len(full_text)} characters")
            
            if not full_text.strip():
                raise ValueError("Could not extract any text from PDF. The PDF appears to be image-based (scanned) without a text layer. Please convert it to a text-based PDF where you can select and copy text. You can use online tools like ilovepdf.com or Adobe Acrobat to convert image PDFs to text PDFs.")
            
            # Step 2: Parse PDF to extract prerequisites, objectives, outcomes
            parsed_info = self._parse_pdf_text(full_text)
            
            subject = parsed_info.get("subject", "Unknown Subject")
            course_code = parsed_info.get("course_code")
            prerequisites = parsed_info.get("prerequisites", "")
            lab_objectives = parsed_info.get("lab_objectives", [])
            lab_outcomes = parsed_info.get("lab_outcomes", [])
            
            # Validate extracted data
            if not lab_objectives:
                raise ValueError("Could not extract lab objectives from PDF. Please ensure the PDF contains lab objectives.")
            if not lab_outcomes:
                raise ValueError("Could not extract lab outcomes from PDF. Please ensure the PDF contains lab outcomes.")
            
            # Step 3: Generate lab manual structure
            manual_content = self._generate_lab_manual_structure(
                prerequisites=prerequisites,
                lab_objectives=lab_objectives,
                lab_outcomes=lab_outcomes,
                subject=subject,
                course_code=course_code,
                num_modules=num_modules
            )
            
            return manual_content
            
        except Exception as e:
            print(f"Error generating lab manual from PDF: {e}")
            raise ValueError(f"Failed to generate lab manual: {str(e)}")
    
    def _parse_pdf_text(self, full_text: str) -> Dict:
        """Parse extracted PDF text to find prerequisites, objectives, and outcomes"""
        try:
            prompt = f"""
You are an expert at parsing academic documents. Extract the following information from the provided text:

1. **Subject/Course Name** - The name of the subject or course
2. **Course Code** (if mentioned) - The course code/number
3. **Prerequisites** - Required prerequisites for the course (e.g., "Python Programming, Engineering Mathematics")
4. **Lab Objectives** - List of lab objectives (usually numbered or bulleted, starting with "To" or similar)
5. **Lab Outcomes** - List of lab outcomes (usually starting with "At the end of the course, students will be able to" or similar)

Here is the text from the PDF:

{full_text[:8000]}

Extract and return ONLY valid JSON in this exact structure:
{{
    "subject": "Subject Name",
    "course_code": "Course Code or null",
    "prerequisites": "Prerequisites text or empty string",
    "lab_objectives": [
        "Objective 1",
        "Objective 2"
    ],
    "lab_outcomes": [
        "Outcome 1",
        "Outcome 2"
    ]
}}

If any field is not found, use empty string for strings or empty array for lists.
Return ONLY the JSON, no markdown formatting or extra text.
"""
            
            response = genai_client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            result_text = getattr(response, "text", "") or ""
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(result_text)
            
            # Validate and clean
            if not isinstance(parsed, dict):
                raise ValueError("Invalid response structure from AI")
            
            # Ensure required fields exist
            parsed.setdefault("subject", "")
            parsed.setdefault("course_code", None)
            parsed.setdefault("prerequisites", "")
            parsed.setdefault("lab_objectives", [])
            parsed.setdefault("lab_outcomes", [])
            
            # Clean up lists
            if not isinstance(parsed["lab_objectives"], list):
                parsed["lab_objectives"] = []
            if not isinstance(parsed["lab_outcomes"], list):
                parsed["lab_outcomes"] = []
            
            return parsed
            
        except Exception as e:
            error_msg = str(e)
            # Check for quota errors
            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                raise ValueError(f"Gemini API quota exceeded. Please wait ~30 seconds and try again, or upgrade your API plan. Error: {error_msg[:200]}")
            print(f"Error parsing PDF text: {e}")
            raise
    
    def _generate_lab_manual_structure(
        self,
        prerequisites: str,
        lab_objectives: List[str],
        lab_outcomes: List[str],
        subject: str,
        course_code: Optional[str] = None,
        num_modules: int = 5
    ) -> Dict:
        """Generate structured lab manual from extracted information"""
        try:
            prompt = f"""
You are an expert lab manual creator for college-level courses. Generate a comprehensive, detailed lab manual based on the following information:

**Subject:** {subject}
**Course Code:** {course_code or 'N/A'}
**Prerequisites:** {prerequisites}

**Lab Objectives:**
{chr(10).join(f"{i+1}. {obj}" for i, obj in enumerate(lab_objectives))}

**Lab Outcomes:**
{chr(10).join(f"{i+1}. {outcome}" for i, outcome in enumerate(lab_outcomes))}

Create a structured lab manual with {num_modules} modules. Each module should contain:
- Clear, descriptive module title that reflects the topic
- 2-3 detailed experiments per module
- Each experiment MUST include:
  - Experiment number (sequential across all modules)
  - Descriptive, specific title (e.g., "Implement Linear Regression from Scratch", not just "Linear Regression")
  - Clear objective stating what students will learn/achieve
  - Detailed description with:
    * Specific tasks students need to perform
    * Step-by-step procedures or implementation requirements
    * What code/programs they need to write
    * Expected outputs or results
    * Any specific requirements or constraints

IMPORTANT: Make experiments PRACTICAL and DETAILED. Instead of generic statements like "students will implement codes related to topic", provide:
- Specific programming tasks (e.g., "Write a Python function to calculate gradient descent", "Create a neural network with 2 hidden layers")
- Clear procedures (e.g., "Step 1: Load the dataset. Step 2: Preprocess data. Step 3: Implement the algorithm...")
- Expected deliverables (e.g., "Submit: (1) Source code, (2) Output screenshots, (3) Analysis report")
- Real-world applications suitable for college students

Organize experiments logically, progressing from basic concepts to advanced applications.
Some modules should specify "Any One" or "Any Two" experiments (like in real lab manuals).

Return ONLY valid JSON in this exact structure:
{{
    "subject": "{subject}",
    "course_code": "{course_code or 'N/A'}",
    "prerequisites": "{prerequisites}",
    "lab_objectives": {json.dumps(lab_objectives)},
    "lab_outcomes": {json.dumps(lab_outcomes)},
    "modules": [
        {{
            "module_number": 1,
            "module_title": "Specific Module Title (e.g., 'Introduction to Machine Learning Algorithms')",
            "selection_requirement": "All" | "Any One" | "Any Two",
            "experiments": [
                {{
                    "experiment_number": 1,
                    "title": "Specific Experiment Title (e.g., 'Implement Linear Regression from Scratch using NumPy')",
                    "objective": "Clear learning objective (e.g., 'To understand and implement linear regression algorithm without using sklearn library')",
                    "description": "Detailed description with:\n- Specific tasks: Write a Python class LinearRegression with fit() and predict() methods\n- Procedure: Step 1: Import numpy and matplotlib. Step 2: Create dataset with 100 samples. Step 3: Implement gradient descent algorithm. Step 4: Train the model. Step 5: Plot the regression line and calculate R² score\n- Expected output: Working code that predicts target values with accuracy > 0.85\n- Deliverables: Source code file, output graphs, and performance metrics report"
                }}
            ]
        }}
    ]
}}

Make each experiment description at least 3-4 sentences with specific, actionable tasks. Ensure experiments are:
- Suitable for college students (not too easy, not too advanced)
- Practical and hands-on
- Aligned with the lab objectives and outcomes
- Progressive in difficulty across modules

Return ONLY the JSON, no markdown formatting or extra text.
"""
            
            response = genai_client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            result_text = getattr(response, "text", "") or ""
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(result_text)
            
            # Validate structure
            if not isinstance(parsed, dict) or "modules" not in parsed:
                raise ValueError("Invalid response structure from AI")
            
            return parsed
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return self._create_fallback_manual(subject, lab_objectives, lab_outcomes, prerequisites, num_modules)
        except Exception as e:
            error_msg = str(e)
            # Check for quota errors
            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                raise ValueError(f"Gemini API quota exceeded. Please wait ~30 seconds and try again, or upgrade your API plan. Error: {error_msg[:200]}")
            print(f"Error generating lab manual structure: {e}")
            return self._create_fallback_manual(subject, lab_objectives, lab_outcomes, prerequisites, num_modules)
    
    def _create_fallback_manual(
        self,
        subject: str,
        lab_objectives: List[str],
        lab_outcomes: List[str],
        prerequisites: str,
        num_modules: int
    ) -> Dict:
        """Create a basic fallback structure if AI generation fails"""
        modules = []
        exp_num = 1
        
        # Create more detailed fallback experiments
        module_topics = [
            "Introduction and Basics",
            "Core Concepts and Implementation",
            "Advanced Topics",
            "Practical Applications",
            "Project-Based Learning"
        ]
        
        for mod_num in range(1, num_modules + 1):
            experiments = []
            num_experiments = 2 if mod_num <= 2 else 3
            module_topic = module_topics[min(mod_num - 1, len(module_topics) - 1)]
            
            for i in range(num_experiments):
                obj_idx = min(i, len(lab_objectives) - 1) if lab_objectives else 0
                objective_text = lab_objectives[obj_idx] if lab_objectives else "Practical implementation"
                
                # Create more detailed description
                description = f"""Students will implement a practical solution related to: {objective_text}

Tasks to perform:
1. Analyze the problem requirements and design the solution approach
2. Write code/program to implement the solution
3. Test the implementation with sample data
4. Document the results and observations
5. Submit the source code along with output screenshots and a brief report

Expected deliverables:
- Complete source code file(s)
- Output screenshots demonstrating the working solution
- Brief report explaining the approach and results"""
                
                experiments.append({
                    "experiment_number": exp_num,
                    "title": f"Experiment {exp_num}: Practical Implementation - {objective_text[:50]}",
                    "objective": f"To understand and implement {objective_text.lower()}",
                    "description": description
                })
                exp_num += 1
            
            modules.append({
                "module_number": mod_num,
                "module_title": f"Module {mod_num}: {module_topic}",
                "selection_requirement": "All" if mod_num <= 2 else "Any Two",
                "experiments": experiments
            })
        
        return {
            "subject": subject,
            "course_code": "N/A",
            "prerequisites": prerequisites,
            "lab_objectives": lab_objectives,
            "lab_outcomes": lab_outcomes,
            "modules": modules
        }
