# Custom Slides and Slide Structure Guide

## Overview
The PPT generator now supports two powerful features:
1. **Custom Slide Content**: Provide your own bullet points and images for specific slides
2. **Slide Structure**: Define slide titles/structure, and the AI generates content accordingly

## Feature 1: Custom Slide Content

### Use Case
When you want to provide exact content for a specific slide (e.g., architecture diagram with specific points).

### Via API (Direct)
```json
{
  "topic": "RNN Architecture",
  "content": "...",
  "subject": "Deep Learning",
  "num_slides": 8,
  "custom_slides": [
    {
      "slide_number": 3,
      "title": "RNN Architecture",
      "content": [
        "RNN processes input one step at a time, maintaining a hidden state",
        "Hidden state captures context from previous inputs",
        "Formula: h_t = f(W_h * h_{t-1} + W_x * x_t + b)",
        "Can handle inputs of variable length",
        "Limitation: struggles with long-term dependencies due to vanishing gradients"
      ],
      "image_url": "https://example.com/rnn-architecture-diagram.png",
      "speaker_notes": "Explain the RNN architecture step by step. Show how the hidden state flows through time."
    }
  ]
}
```

### Via Chat Assistant (Natural Language)
**Example prompts:**
- "Create PPT on RNNs. For slide 3, title 'Architecture', add these points: RNN processes input one step at a time, Hidden state captures context, Formula: h_t = f(...), image: https://example.com/rnn.png"
- "Generate slides for LSTM. Slide 2 title 'LSTM Architecture', content: [list your bullet points], image URL: https://example.com/lstm.jpg"

**How it works:**
- The chat assistant extracts slide number, title, content, and image URL from your prompt
- That specific slide uses your exact content
- Other slides are generated automatically by the AI

## Feature 2: Slide Structure

### Use Case
When you want to control the slide titles/structure but let AI generate the content.

### Via API (Direct)
```json
{
  "topic": "RNN",
  "content": "...",
  "subject": "Deep Learning",
  "num_slides": 6,
  "slide_structure": [
    {"slide_number": 1, "title": "Introduction to RNNs"},
    {"slide_number": 2, "title": "RNN Architecture"},
    {"slide_number": 3, "title": "Types of RNNs"},
    {"slide_number": 4, "title": "Applications"},
    {"slide_number": 5, "title": "Advantages and Limitations"},
    {"slide_number": 6, "title": "Summary"}
  ]
}
```

### Via Chat Assistant (Natural Language)
**Example prompts:**
- "Create 4 slides on RNN: slide 1 title Introduction, slide 2 title Architecture, slide 3 title Applications, slide 4 title Summary"
- "Generate PPT on Neural Networks. Structure: Slide 1 - Intro, Slide 2 - Architecture, Slide 3 - Types, Slide 4 - Applications"

**How it works:**
- The chat assistant extracts the slide structure from your prompt
- AI generates content for each slide following your specified titles
- Content is still AI-generated but follows your structure

## Combined Usage

You can combine both features:

```json
{
  "topic": "RNN",
  "num_slides": 6,
  "slide_structure": [
    {"slide_number": 1, "title": "Introduction"},
    {"slide_number": 2, "title": "Architecture"},
    {"slide_number": 3, "title": "Types"},
    {"slide_number": 4, "title": "Applications"}
  ],
  "custom_slides": [
    {
      "slide_number": 2,
      "title": "Architecture",
      "content": ["Your custom points here"],
      "image_url": "https://example.com/arch.png"
    }
  ]
}
```

**Chat Example:**
"Create 6 slides on RNN: slide 1 Intro, slide 2 Architecture (use these points: [list], image: [url]), slide 3 Types, slide 4 Applications"

## Priority System

1. **Custom Slide Content** (highest priority) - If you provide custom content for a slide, it uses your exact content
2. **Slide Structure** - If you provide structure, AI uses your titles but generates content
3. **Auto-generated** - If neither is provided, AI generates everything automatically

## Technical Details

- **Slide Numbers**: 1-based (slide 1 is the title slide)
- **Content Format**: Array of strings (bullet points)
- **Image URLs**: Must be valid HTTP/HTTPS URLs
- **Speaker Notes**: Optional, but recommended for custom slides
- **Validation**: Invalid slide numbers are ignored

## Benefits

1. **Precision**: Use exact architecture diagrams and content from textbooks/papers
2. **Control**: Define structure while leveraging AI for content generation
3. **Flexibility**: Mix custom slides with AI-generated slides
4. **Natural Language**: Chat assistant understands your instructions automatically

## Examples

### Example 1: Custom Architecture Slide
```
User: "Create PPT on RNN. Slide 3 title Architecture, add: RNN processes sequentially, Hidden state persists, Formula h_t = f(...), image: https://example.com/rnn.png"
Result: Slide 3 uses your exact content and image, other slides are AI-generated
```

### Example 2: Defined Structure
```
User: "Generate 5 slides on LSTM: slide 1 Intro, slide 2 Architecture, slide 3 Gates, slide 4 Applications, slide 5 Summary"
Result: All slides follow your structure, content is AI-generated
```

### Example 3: Mixed Approach
```
User: "PPT on Neural Networks. Structure: Intro, Architecture, Types, Applications. For Architecture slide, use image: https://example.com/nn.png"
Result: Structure follows your titles, Architecture slide gets your image, content is AI-generated
```











