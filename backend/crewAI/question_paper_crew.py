from crewai import Crew
from agents.document_processor_agent import document_processor_agent, create_document_processing_task

class QuestionPaperCrew:
    def __init__(self):
        self.crew = None
    
    def process_document(self, file_path: str, file_type: str) -> str:
        """Process a single document and return extracted text"""
        task = create_document_processing_task(file_path, file_type)
        
        self.crew = Crew(
            agents=[document_processor_agent],
            tasks=[task],
            verbose=True
        )
        
        result = self.crew.kickoff()
        return result