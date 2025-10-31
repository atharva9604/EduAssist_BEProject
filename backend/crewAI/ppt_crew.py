from crewai import Crew
from agents.ppt_generator_agent import ppt_generator_agent, create_ppt_generation_task
from agents.document_processor_agent import document_processor_agent, create_document_processing_task
from utils.ppt_creator import PPTCreator
import json
from typing import Dict, Optional

class PPTCrew:
    """CrewAI crew for orchestrating PowerPoint presentation generation"""
    
    def __init__(self, storage_dir: str = "storage/presentations"):
        self.crew = None
        self.ppt_creator = PPTCreator(storage_dir)
    
    def generate_presentation_from_topic(self, topic: str, content: str = "", num_slides: int = 8) -> Dict:
        """Generate a presentation from a topic and optional content"""
        try:
            # Create PPT generation task
            task = create_ppt_generation_task(topic, content, num_slides)
            
            # Create crew with PPT generator agent
            self.crew = Crew(
                agents=[ppt_generator_agent],
                tasks=[task],
                verbose=True
            )
            
            # Execute the task
            result = self.crew.kickoff()
            
            # Parse the result
            try:
                if isinstance(result, str):
                    content_data = json.loads(result)
                else:
                    content_data = result
            except (json.JSONDecodeError, TypeError):
                # If result is not JSON, create a basic structure
                content_data = {
                    "presentation_title": topic,
                    "presentation_subtitle": "Educational Presentation",
                    "slides": [
                        {
                            "slide_number": 1,
                            "slide_type": "title",
                            "title": topic,
                            "content": ["Introduction to the topic"],
                            "visual_suggestion": "Title slide with topic image"
                        }
                    ]
                }
            
            # Create the PowerPoint file
            file_path = self.ppt_creator.create_presentation(content_data)
            
            # Get presentation info
            presentation_info = self.ppt_creator.get_presentation_info(file_path)
            
            return {
                "success": True,
                "content_data": content_data,
                "file_path": file_path,
                "presentation_info": presentation_info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content_data": None,
                "file_path": None
            }
    
    def generate_presentation_from_document(self, file_path: str, file_type: str, topic: str, num_slides: int = 8) -> Dict:
        """Generate a presentation from an uploaded document"""
        try:
            # First, process the document to extract content
            doc_task = create_document_processing_task(file_path, file_type)
            
            doc_crew = Crew(
                agents=[document_processor_agent],
                tasks=[doc_task],
                verbose=True
            )
            
            # Extract content from document
            extracted_content = doc_crew.kickoff()
            
            # Generate presentation from extracted content
            return self.generate_presentation_from_topic(topic, str(extracted_content), num_slides)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing document: {str(e)}",
                "content_data": None,
                "file_path": None
            }
    
    def generate_presentation_from_syllabus(self, syllabus_content: str, topic: str, num_slides: int = 8) -> Dict:
        """Generate a presentation from syllabus content"""
        try:
            # Filter syllabus content for the specific topic
            filtered_content = self._filter_content_for_topic(syllabus_content, topic)
            
            # Generate presentation
            return self.generate_presentation_from_topic(topic, filtered_content, num_slides)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing syllabus: {str(e)}",
                "content_data": None,
                "file_path": None
            }
    
    def _filter_content_for_topic(self, syllabus_content: str, topic: str) -> str:
        """Filter syllabus content to find relevant sections for the topic"""
        # Simple keyword-based filtering
        # In a more advanced implementation, this could use semantic search
        lines = syllabus_content.split('\n')
        relevant_lines = []
        
        topic_keywords = topic.lower().split()
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in topic_keywords):
                relevant_lines.append(line)
            elif len(relevant_lines) > 0 and len(line.strip()) > 0:
                # Include context lines after finding relevant content
                relevant_lines.append(line)
                if len(relevant_lines) > 20:  # Limit context
                    break
        
        return '\n'.join(relevant_lines) if relevant_lines else syllabus_content[:2000]
    
    def list_presentations(self) -> list:
        """List all generated presentations"""
        return self.ppt_creator.list_presentations()
    
    def get_presentation_info(self, file_path: str) -> Dict:
        """Get information about a specific presentation"""
        return self.ppt_creator.get_presentation_info(file_path)

