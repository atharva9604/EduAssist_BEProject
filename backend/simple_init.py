import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import SQLAlchemy
from sqlalchemy import create_engine, text

# Use the working connection
DATABASE_URL = "postgresql://postgres:J%40iparmar17@localhost:5433/eduassist_db"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
        
        # Import models directly
        from database.models.base import Base
        from database.models.user import User
        from database.models.document import Document
        from database.models.question import Question
        from database.models.question_paper import QuestionPaper
        from database.models.agent_task import AgentTask
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
except Exception as e:
    print(f"❌ Error: {e}")