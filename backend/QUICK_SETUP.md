# Quick Setup Guide

## Step 1: Get Groq API Key (2 minutes)

1. Go to: https://console.groq.com/
2. Sign up/Login (free)
3. Click "API Keys" → "Create API Key"
4. Copy the key (starts with `gsk_...`)

## Step 2: Create `.env` file

Create a file named `.env` in the `backend/` folder with this content:

```env
GROQ_API_KEY=gsk_your_actual_key_here
```

**That's it!** The system will use Gemini by default (if it's set in system env), and Groq when you request it.

## Step 3: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Step 4: Test

Restart your backend server and try generating a PPT with "use groq" in the content field!



