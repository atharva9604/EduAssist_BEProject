# 🚀 EduAssist Backend Startup Guide

## Quick Start Steps:

### 1. Start Backend Server (Terminal 1)
```bash
cd backend
.\venv\Scripts\Activate.ps1
python api/main.py
```
Server runs on: http://localhost:8000

### 2. Start Frontend (Terminal 2)
```bash
npm run dev
```
Frontend runs on: http://localhost:3000

### 3. Test API
Visit: http://localhost:8000/docs

### 4. Test Full System
Visit: http://localhost:3000 → Click "Question Paper" button

## Common Commands:

### Activate Virtual Environment
```bash
.\venv\Scripts\Activate.ps1
```

### Install Packages
```bash
pip install -r requirements.txt
```

### Run Database Setup
```bash
python simple_init.py
```

## Important Files:
- `backend/api/main.py` - FastAPI server
- `backend/agents/` - AI agents
- `backend/database/` - Database models

