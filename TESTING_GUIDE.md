# 🧪 Complete Testing Guide - Start Backend & Frontend

## Prerequisites Check

Before starting, make sure you have:
- ✅ Python 3.8+ installed
- ✅ Node.js and npm installed
- ✅ Groq API key (optional but recommended)

---

## Step-by-Step Instructions

### **STEP 1: Install/Update Backend Dependencies**

Open **Terminal 1** (PowerShell or Command Prompt):

```powershell
# Navigate to project root
cd C:\Users\Admin\EduAssist_BEProject

# Go to backend folder
cd backend

# Install/update dependencies (including new Groq package)
pip install -r requirements.txt
```

**Expected Output:**
```
Successfully installed groq-0.4.1 ...
```

---

### **STEP 2: Set Up Environment Variables (Optional but Recommended)**

Create `backend/.env` file:

**Option A: Using PowerShell**
```powershell
cd backend
New-Item -Path .env -ItemType File -Force
notepad .env
```

**Option B: Using File Explorer**
1. Navigate to `C:\Users\Admin\EduAssist_BEProject\backend\`
2. Create new file named `.env`
3. Open with Notepad

**Add this content to `.env`:**
```env
# Groq API Key (get from https://console.groq.com/)
GROQ_API_KEY=gsk_your_key_here

# Gemini API Key (if you have it, otherwise it uses system env)
# GEMINI_API_KEY=your_gemini_key_here
```

**Save and close the file.**

---

### **STEP 3: Start Backend Server**

In **Terminal 1** (same PowerShell window):

```powershell
# Make sure you're in backend folder
cd C:\Users\Admin\EduAssist_BEProject\backend

# Activate virtual environment (if you have one)
# If you don't have venv, skip this step
.\venv\Scripts\Activate.ps1

# Start the FastAPI server
python api/main.py
```

**Expected Output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**✅ Backend is running on:** http://localhost:8000

**Keep this terminal window open!**

---

### **STEP 4: Install Frontend Dependencies (First Time Only)**

Open **Terminal 2** (New PowerShell window):

```powershell
# Navigate to project root
cd C:\Users\Admin\EduAssist_BEProject

# Install npm packages (only needed first time or after package.json changes)
npm install
```

**Expected Output:**
```
added 500+ packages
```

---

### **STEP 5: Start Frontend Server**

In **Terminal 2** (same window):

```powershell
# Make sure you're in project root
cd C:\Users\Admin\EduAssist_BEProject

# Start Next.js development server
npm run dev
```

**Expected Output:**
```
  ▲ Next.js 15.5.3
  - Local:        http://localhost:3000
  - Ready in 2.3s
```

**✅ Frontend is running on:** http://localhost:3000

**Keep this terminal window open!**

---

## 🎯 Testing the Improvements

### **Test 1: Basic PPT Generation**

1. Open browser: http://localhost:3000
2. Navigate to **PPT Generator** page (or `/ppt-generator`)
3. Fill in the form:
   - **Topics:** `Machine Learning`
   - **Subject:** `Computer Science`
   - **Content:** Leave empty (or add "use groq" to test Groq)
   - **Slide count:** `10`
4. Click **"Generate PPT"**
5. Wait for generation (may take 30-60 seconds)
6. Click **"Download"** to get the PPT file

**✅ Check:**
- Open the downloaded PPT
- Each content slide should have **8-12 detailed bullet points** (not 3-5)
- Content should be detailed with definitions and examples

---

### **Test 2: Speaker Notes**

1. Open the generated PPT in PowerPoint
2. Go to **View** → **Notes Page** (or click Notes pane at bottom)
3. Scroll through slides

**✅ Check:**
- Each slide should have **speaker notes** in the Notes section
- Notes should explain what to teach, examples to give, questions to ask

---

### **Test 3: Groq LLaMA (Fast Mode)**

1. In PPT Generator form:
   - **Topics:** `Deep Learning`
   - **Subject:** `AI`
   - **Content:** `use groq for fast generation`
   - **Slide count:** `12`
2. Click **"Generate PPT"**

**✅ Check:**
- Generation should be **faster** than Gemini
- Quality should be similar or better
- Check backend terminal for any Groq-related messages

---

### **Test 4: Multi-Topic PPT**

1. In PPT Generator form:
   - **Topics:** (one per line)
     ```
     Neural Networks
     Convolutional Neural Networks
     Recurrent Neural Networks
     ```
   - **Subject:** `Deep Learning`
   - **Slide count:** `15`
2. Click **"Generate PPT"**

**✅ Check:**
- Should generate multiple slides per topic
- Each topic should have detailed content
- Speaker notes should be present

---

### **Test 5: API Testing (Optional)**

1. Open browser: http://localhost:8000/docs
2. This opens **FastAPI Swagger UI**
3. Find **`POST /api/generate-ppt`**
4. Click **"Try it out"**
5. Fill in the JSON:
   ```json
   {
     "topic": "Photosynthesis",
     "content": "",
     "subject": "Biology",
     "num_slides": 8,
     "model_type": "groq_llama"
   }
   ```
6. Click **"Execute"**

**✅ Check:**
- Should return success response
- Check the generated PPT file

---

## 🐛 Troubleshooting

### **Backend won't start**

**Error:** `ModuleNotFoundError: No module named 'groq'`
```powershell
# Solution: Install dependencies
cd backend
pip install -r requirements.txt
```

**Error:** `GEMINI_API_KEY not set`
- The system needs either Gemini or Groq API key
- Add `GROQ_API_KEY` to `backend/.env` file
- Or set `GEMINI_API_KEY` in system environment variables

**Error:** `Port 8000 already in use`
```powershell
# Solution: Kill the process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F
```

---

### **Frontend won't start**

**Error:** `Port 3000 already in use`
```powershell
# Solution: Kill the process using port 3000
netstat -ano | findstr :3000
taskkill /PID <PID_NUMBER> /F
```

**Error:** `npm: command not found`
- Install Node.js from: https://nodejs.org/

---

### **PPT Generation fails**

**Error:** `Groq API error`
- Check that `GROQ_API_KEY` is correct in `.env` file
- Verify API key at https://console.groq.com/
- System will fallback to Gemini automatically

**Error:** `Still getting 3-5 bullet points`
- Make sure backend server was restarted after code changes
- Check backend terminal for any errors
- Try generating a new PPT

---

## 📊 Quick Reference

### **Terminal Commands Summary**

**Backend (Terminal 1):**
```powershell
cd C:\Users\Admin\EduAssist_BEProject\backend
pip install -r requirements.txt
python api/main.py
```

**Frontend (Terminal 2):**
```powershell
cd C:\Users\Admin\EduAssist_BEProject
npm install  # First time only
npm run dev
```

### **URLs**

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## ✅ Success Checklist

After following all steps, you should have:

- ✅ Backend running on port 8000
- ✅ Frontend running on port 3000
- ✅ Can generate PPTs with 8-12 bullet points per slide
- ✅ Speaker notes visible in PowerPoint Notes section
- ✅ Option to use Groq for faster generation
- ✅ Better academic content quality

---

## 🎉 You're Ready!

Both servers are running. Open http://localhost:3000 and start testing the improved PPT generator!

**Remember:**
- Keep both terminal windows open while testing
- Backend must be running for PPT generation to work
- Check PowerPoint Notes section to see speaker notes






