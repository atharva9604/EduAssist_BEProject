
import sys
from pathlib import Path

# Get backend directory (parent of database folder)
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database.connection import engine, Base, SessionLocal
from database.models import (
    User, Document, Presentation, QuestionPaper, Question,
    CalendarEvent, Task, SimpleTodo, Subject, ContinuousAssessment,
    LabManual, FDP, Lecture, Certification, CurrentProject, ResearchProposal,
    Teacher, DepartmentSemester, AttendanceClass, AttendanceSubject,
    AttendanceStudent, AttendanceSession, AttendanceRecord
)
import json
from datetime import datetime

def create_tables():
    """Step 1: Create all database tables"""
    print("📦 Step 1: Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!\n")

def create_default_user():
    """Step 2: Create default user if it doesn't exist"""
    db = SessionLocal()
    try:
        default_user = db.query(User).filter(User.uid == "default").first()
        if not default_user:
            print("📦 Step 2: Creating default user...")
            default_user = User(
                uid="default",
                name="Default Teacher",
                email="default@eduassist.com",
                role="teacher",
                department_id="",
                subjects=[]
            )
            db.add(default_user)
            db.commit()
            print("✅ Default user created!\n")
        else:
            print("📦 Step 2: Default user already exists, skipping...\n")
    except Exception as e:
        db.rollback()
        print(f"⚠️  Error creating default user: {e}\n")
    finally:
        db.close()

def migrate_data():
    """Step 3: Migrate existing JSON data to database"""
    db = SessionLocal()
    
    # Migrate events
    print("📦 Step 3a: Migrating events from JSON...")
    events_path = backend_dir / "storage" / "calendar" / "events.json"
    if events_path.exists():
        with open(events_path, "r", encoding="utf-8") as f:
            events = json.load(f)
        
        existing = db.query(CalendarEvent).count()
        if existing == 0 and events:
            migrated = 0
            for event_data in events:
                try:
                    start_dt = datetime.fromisoformat(event_data["start"].replace("Z", ""))
                    end_dt = datetime.fromisoformat(event_data["end"].replace("Z", ""))
                    event = CalendarEvent(
                        user_id="default",
                        title=event_data.get("title", "Untitled"),
                        start=start_dt,
                        end=end_dt,
                        location=event_data.get("location"),
                        description=event_data.get("description"),
                        all_day=event_data.get("allDay", False)
                    )
                    db.add(event)
                    migrated += 1
                except Exception as e:
                    print(f"  ⚠️  Skipped event: {e}")
            db.commit()
            print(f"✅ Migrated {migrated} events\n")
        else:
            print(f"⚠️  Skipped (already have {existing} events or file empty)\n")
    else:
        print("⚠️  No events.json found, skipping\n")
    
    # Migrate tasks
    print("📦 Step 3b: Migrating tasks from JSON...")
    tasks_path = backend_dir / "storage" / "calendar" / "tasks.json"
    if tasks_path.exists():
        with open(tasks_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        
        existing = db.query(Task).count()
        if existing == 0 and tasks:
            migrated = 0
            for task_data in tasks:
                try:
                    due_date = datetime.fromisoformat(task_data["due_date"]).date()
                    task = Task(
                        user_id="default",
                        title=task_data.get("title", "Untitled"),
                        due_date=due_date,
                        done=task_data.get("done", False)
                    )
                    db.add(task)
                    migrated += 1
                except Exception as e:
                    print(f"  ⚠️  Skipped task: {e}")
            db.commit()
            print(f"✅ Migrated {migrated} tasks\n")
        else:
            print(f"⚠️  Skipped (already have {existing} tasks or file empty)\n")
    else:
        print("⚠️  No tasks.json found, skipping\n")
    
    db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Database Setup - One-Time Script")
    print("=" * 50)
    print()
    
    create_tables()
    create_default_user()
    migrate_data()
    
    print("=" * 50)
    print("✅ Setup complete! Now run: python api/main.py")
    print("=" * 50)