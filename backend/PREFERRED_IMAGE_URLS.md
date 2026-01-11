# Preferred Image URL Support

## Overview
Users can now provide their own image URLs for specific slides, especially useful for architecture diagrams and technical content that Unsplash cannot provide accurately.

## How It Works

### 1. Via API Request (Direct)
When calling `/api/generate-ppt` or `/api/generate-ppt-multi`, include `preferred_image_urls`:

```json
{
  "topic": "RNN Architecture",
  "content": "...",
  "subject": "Deep Learning",
  "num_slides": 8,
  "preferred_image_urls": [
    {
      "slide_number": 3,
      "url": "https://example.com/rnn-architecture-diagram.png"
    },
    {
      "slide_number": 5,
      "url": "https://example.com/lstm-diagram.png"
    }
  ]
}
```

### 2. Via Chat Assistant (`/api/assist`)
The chat assistant can extract image URLs from natural language prompts:

**Example prompts:**
- "Create a PPT on RNNs. Use this architecture diagram: https://example.com/rnn.png for slide 3"
- "Generate slides for LSTM. Architecture image: https://example.com/lstm-arch.jpg"
- "PPT on Neural Networks. Preferred architecture diagram URL: https://example.com/nn.png"

The assistant will automatically:
1. Extract URLs from your prompt
2. Identify which slide number they should be applied to (especially architecture slides)
3. Download and insert the images

### 3. Priority System
Images are attached in this priority order:
1. **Preferred Image URL** (user-provided) - Highest priority
2. **Image Query** (Unsplash search) - Fallback if no preferred URL

### 4. Architecture Slide Detection
The system automatically detects architecture/diagram slides (typically slides 2-4) and prioritizes preferred URLs there if provided.

## Technical Details

- **Image Storage**: Preferred images are downloaded to `storage/presentations/images/`
- **Supported Formats**: Any image format supported by Python's `requests` library (JPG, PNG, GIF, etc.)
- **URL Validation**: URLs must start with `http://` or `https://`
- **Error Handling**: If a preferred URL fails to download, the system falls back to Unsplash search (if `image_query` is present)

## Benefits

1. **Accuracy**: Use exact architecture diagrams from textbooks, research papers, or your own sources
2. **Control**: Specify exactly which slides get which images
3. **Flexibility**: Works alongside Unsplash - use preferred URLs for critical slides, Unsplash for others
4. **Natural Language**: Chat assistant understands URLs in prompts automatically











