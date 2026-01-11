# ✅ Fixed: Backend Startup Issue

## Problem Solved
The backend was requiring `GEMINI_API_KEY` at startup. Now it works with **either** Gemini **or** Groq API key.

---

## Quick Fix: Add API Key

### Option 1: Use Groq (Recommended - Faster & Free)

1. **Get Groq API Key:**
   - Go to: https://console.groq.com/
   - Sign up (free)
   - Create API key
   - Copy the key (starts with `gsk_...`)

2. **Create `.env` file:**
   - Navigate to: `C:\Users\Admin\EduAssist_BEProject\backend\`
   - Create new file named `.env`
   - Add this line:
     ```env
     GROQ_API_KEY=gsk_your_actual_key_here
     ```

3. **Start backend:**
   ```powershell
   cd C:\Users\Admin\EduAssist_BEProject\backend
   python api/main.py
   ```

---

### Option 2: Use Gemini

1. **Get Gemini API Key:**
   - Go to: https://makersuite.google.com/app/apikey
   - Sign in with Google
   - Create API key
   - Copy the key

2. **Create `.env` file:**
   - Navigate to: `C:\Users\Admin\EduAssist_BEProject\backend\`
   - Create new file named `.env`
   - Add this line:
     ```env
     GEMINI_API_KEY=your_gemini_key_here
     ```

3. **Start backend:**
   ```powershell
   cd C:\Users\Admin\EduAssist_BEProject\backend
   python api/main.py
   ```

---

## ✅ Success!

You should now see:
```
✓ Groq API configured
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 📝 Note

- **PPT Generator** works with either API key
- **Question Paper Generator** requires Gemini API key (for now)
- You can have both keys in `.env` file if you want

---

## 🚀 Next Steps

Once backend starts successfully:
1. Keep terminal open
2. Open another terminal for frontend
3. Run: `npm run dev` (from project root)






