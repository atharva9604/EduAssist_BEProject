# 🚀 How to Start Backend Server

## Quick Start (3 Steps)

### **Step 1: Open PowerShell/Terminal**

Press `Win + X` → Select "Windows PowerShell" or "Terminal"

---

### **Step 2: Navigate to Backend Folder**

```powershell
cd C:\Users\Admin\EduAssist_BEProject\backend
```

---

### **Step 3: Install Dependencies (First Time Only)**

```powershell
pip install -r requirements.txt
```

**Wait for installation to complete** (may take 1-2 minutes)

---

### **Step 4: Start the Server**

```powershell
python api/main.py
```

---

## ✅ Success!

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Backend is now running on:** http://localhost:8000

**Keep this terminal window open!**

---

## 🧪 Test It

Open browser and visit:
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## 🐛 Troubleshooting

### **Error: `pip: command not found`**
- Install Python from: https://www.python.org/downloads/
- Make sure to check "Add Python to PATH" during installation

### **Error: `ModuleNotFoundError: No module named 'fastapi'`**
```powershell
pip install -r requirements.txt
```

### **Error: `GEMINI_API_KEY not set`**
- The backend needs either Gemini or Groq API key
- Create `backend/.env` file with:
  ```env
  GROQ_API_KEY=gsk_your_key_here
  ```
- Or set `GEMINI_API_KEY` in system environment variables

### **Error: `Port 8000 already in use`**
```powershell
# Find and kill the process
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F
```

### **Error: `python: command not found`**
- Try: `python3 api/main.py`
- Or: `py api/main.py`

---

## 📝 Complete Command Sequence

Copy and paste these commands one by one:

```powershell
# Navigate to backend
cd C:\Users\Admin\EduAssist_BEProject\backend

# Install dependencies (first time only)
pip install -r requirements.txt

# Start server
python api/main.py
```

---

## 🎯 Next Steps

Once backend is running:
1. **Keep this terminal open**
2. Open **another terminal** for frontend
3. Start frontend with: `npm run dev` (from project root)

---

## 💡 Pro Tip

If you want to run backend in background or use a different port:

```powershell
# Custom port (default is 8000)
python api/main.py --port 8001
```






