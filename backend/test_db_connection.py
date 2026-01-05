from database.connection import engine, SessionLocal
from sqlalchemy import text

def test_connection():
    try:
        # Test 1: Check if we can connect
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()
            print(f"✅ Database connected successfully!")
            print(f"PostgreSQL version: {version[0]}")
        
        # Test 2: Check if database exists
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()
            print(f"✅ Connected to database: {db_name[0]}")
        
        # Test 3: Check if we can create a session
        db = SessionLocal()
        print("✅ Database session created successfully!")
        db.close()
        
        print("\n🎉 All tests passed! Ready to create tables.")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL service is running")
        print("2. Verify database 'eduassist_db' exists in pgAdmin")
        print("3. Check password in connection string (J%40iparmar17)")
        print("4. Make sure you can connect to server in pgAdmin")
        return False

if __name__ == "__main__":
    test_connection()