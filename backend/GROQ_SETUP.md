# Groq LLaMA Setup Instructions

This guide explains how to set up Groq LLaMA integration for the PPT Generator.

## What is Groq?

Groq provides fast inference for LLaMA models. The PPT Generator can now use **Groq LLaMA 3 70B** for faster content generation, especially useful for:
- Long PPT generation
- Bulk topic expansion
- Research-heavy slides

## Setup Steps

### 1. Get Your Groq API Key

1. Go to [https://console.groq.com/](https://console.groq.com/)
2. Sign up or log in to your account
3. Navigate to **API Keys** section
4. Click **"Create API Key"**
5. Copy your API key (it starts with `gsk_...`)

### 2. Add API Key to Environment Variables

#### Option A: Using `.env` file (Recommended)

1. Create or edit `.env` file in the `backend/` directory
2. Add the following line:

```env
GROQ_API_KEY=gsk_your_actual_api_key_here
```

**Important:** Replace `gsk_your_actual_api_key_here` with your actual Groq API key.

#### Option B: Using System Environment Variables

**Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY="gsk_your_actual_api_key_here"
```

**Windows (Command Prompt):**
```cmd
set GROQ_API_KEY=gsk_your_actual_api_key_here
```

**Linux/Mac:**
```bash
export GROQ_API_KEY="gsk_your_actual_api_key_here"
```

### 3. Install Dependencies

Make sure you've installed the Groq package:

```bash
cd backend
pip install -r requirements.txt
```

Or install Groq directly:

```bash
pip install groq==0.4.1
```

### 4. Verify Setup

The system will automatically detect if Groq is available. If `GROQ_API_KEY` is set, you can use Groq LLaMA.

## How to Use Groq LLaMA

### Method 1: Auto-Detection (Automatic)

The system automatically detects when you want to use Groq based on keywords in your input:

**Keywords that trigger Groq:**
- "use llama"
- "use groq"
- "switch to groq"
- "switch to llama"
- "fast mode"
- "use llama model"
- "groq model"
- "llama model"
- "llama3"
- "llama 3"
- "groq llama"

**Example:**
```
Topic: "Machine Learning"
Subject: "Computer Science"
Content: "use groq for fast generation"
```

### Method 2: Explicit API Parameter

You can explicitly specify the model in API requests:

**Single Topic PPT:**
```json
{
  "topic": "Photosynthesis",
  "content": "",
  "subject": "Biology",
  "num_slides": 10,
  "model_type": "groq_llama"
}
```

**Multi-Topic PPT:**
```json
{
  "topics": ["Topic 1", "Topic 2"],
  "subject": "Science",
  "num_slides": 15,
  "model_type": "groq_llama"
}
```

### Method 3: Legacy `use_groq` Parameter

For backward compatibility, you can also use:

```json
{
  "topic": "Photosynthesis",
  "content": "",
  "subject": "Biology",
  "use_groq": true
}
```

## Model Comparison

| Feature | Gemini (Default) | Groq LLaMA 3 70B |
|---------|------------------|------------------|
| Speed | Moderate | **Very Fast** |
| Quality | High | High |
| Best For | General use | Bulk generation, long PPTs |
| API Cost | Google pricing | Free tier available |

## Troubleshooting

### Error: "GROQ_API_KEY not set"

**Solution:** Make sure you've added `GROQ_API_KEY` to your `.env` file or environment variables.

### Error: "Groq API error"

**Possible causes:**
1. Invalid API key - Check that your API key is correct
2. Rate limit exceeded - Groq has rate limits on free tier
3. Network issue - Check your internet connection

**Solution:**
- Verify your API key at [Groq Console](https://console.groq.com/)
- Wait a few minutes if rate limited
- Check Groq service status

### Model Not Switching

If the model doesn't switch to Groq even with keywords:

1. Check that `GROQ_API_KEY` is set correctly
2. Verify the keyword is in your input (case-insensitive)
3. Try using explicit `model_type: "groq_llama"` parameter

## Default Behavior

- **Default Model:** Gemini (`gemini-pro-latest`)
- **Auto-Detection:** Enabled (detects keywords in user input)
- **Fallback:** If Groq is unavailable, automatically falls back to Gemini

## Notes

- Both models produce high-quality educational content
- Groq is faster but requires a separate API key
- You can use either model or both - the system handles switching automatically
- The API key is stored securely in environment variables, never in code

## Support

If you encounter issues:
1. Check this documentation
2. Verify your API keys are set correctly
3. Check the backend logs for detailed error messages
4. Ensure all dependencies are installed (`pip install -r requirements.txt`)



