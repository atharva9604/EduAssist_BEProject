# Direct Image Upload Feature

## Overview
Users can now directly upload images in the chat prompt, and the PPT agent will automatically use them in the presentation!

## How It Works

### Frontend (Chat Interface)
1. **Select Images**: Click "📷 Select Images" button
2. **Upload Multiple**: Select one or more image files (JPG, PNG, GIF, WebP)
3. **Mention Slide Numbers**: In your prompt, mention which slide should use the image
4. **Send**: Click "Ask Copilot" - images are automatically attached

### Backend Processing
1. **Image Storage**: Uploaded images are saved to `storage/presentations/images/uploads/`
2. **Slide Mapping**: System extracts slide numbers from your prompt and maps images to slides
3. **Priority**: Uploaded images take highest priority over URLs or Unsplash searches

## Usage Examples

### Example 1: Single Image
```
Prompt: "Make a PPT on RNNs, 6 slides, subject Deep Learning. Use this image on slide 3 title Architecture"

Steps:
1. Click "📷 Select Images"
2. Select your RNN architecture diagram image
3. Type the prompt above
4. Click "Ask Copilot"
```

### Example 2: Multiple Images
```
Prompt: "Create PPT on Neural Networks, 8 slides. Use first image on slide 2 Architecture, second image on slide 4 Applications"

Steps:
1. Click "📷 Select Images"
2. Select multiple images (Architecture diagram, Applications screenshot)
3. Type the prompt above
4. Click "Ask Copilot"
```

### Example 3: Without Mentioning Slide Numbers
```
Prompt: "Generate PPT on LSTM, 5 slides"

Steps:
1. Upload 1-2 images
2. Type prompt
3. System automatically assigns to architecture slides (typically slides 2-4)
```

## Image Mapping Logic

1. **Explicit Slide Numbers**: If you mention "slide 3", images are mapped to that slide
2. **Sequential Assignment**: If multiple images without explicit slides, assigned sequentially starting from slide 2
3. **Architecture Priority**: Images default to architecture slides (slides 2-4) if no specific slide mentioned

## Supported Formats

- ✅ JPEG/JPG
- ✅ PNG
- ✅ GIF
- ✅ WebP

## File Size Recommendations

- **Optimal**: Under 2MB per image
- **Maximum**: 10MB per image (may be slower)
- **Best Practice**: Compress images before uploading for faster processing

## Technical Details

### API Endpoints
- **Legacy JSON**: Still supported for backward compatibility
  ```json
  POST /api/assist
  {
    "prompt": "Make PPT on RNNs..."
  }
  ```

- **Multipart/Form-Data**: New format with image uploads
  ```
  POST /api/assist
  Content-Type: multipart/form-data
  
  prompt: "Make PPT on RNNs..."
  images: [file1, file2, ...]
  ```

### Image Storage
- **Location**: `storage/presentations/images/uploads/`
- **Naming**: Unique UUID-based filenames
- **Cleanup**: Images are kept for PPT generation, can be cleaned up manually

## Benefits

1. **No URL Hassle**: Upload directly without needing image URLs
2. **Full Control**: Use your own diagrams, screenshots, or images
3. **Easy Workflow**: Select images → Type prompt → Done!
4. **Multiple Images**: Upload several images at once

## Tips

- 💡 **Be Specific**: Mention slide numbers for best results
- 💡 **Image Quality**: Use high-quality images for better PPT output
- 💡 **File Names**: Descriptive filenames help you identify images
- 💡 **Architecture Slides**: Images work best on architecture/diagram slides

## Troubleshooting

**Images not appearing?**
- Check backend console for error messages
- Verify image format is supported
- Ensure slide number is mentioned in prompt

**Wrong slide?**
- Be explicit: "use this image on slide 3"
- Check prompt for slide number mentions

**Upload fails?**
- Check file size (should be under 10MB)
- Verify image format (JPG, PNG, GIF, WebP)
- Check backend logs for errors











