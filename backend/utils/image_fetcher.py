import os
import uuid
import re
from pathlib import Path
from typing import Optional

import requests


class ImageFetcher:
    """Fetches images for slides. Uses Unsplash if UNSPLASH_ACCESS_KEY is set, otherwise skips."""

    def __init__(self, storage_dir: str = "storage/presentations/images"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")

    def fetch_image(self, query: str) -> Optional[str]:
        """Return local path to an image for the query, or None if unavailable."""
        if not query or not query.strip():
            return None
        if not self.unsplash_key:
            # No API key; skip fetching
            return None

        url = "https://api.unsplash.com/photos/random"
        params = {"query": query, "orientation": "landscape"}
        headers = {"Authorization": f"Client-ID {self.unsplash_key}"}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            img_url = data.get("urls", {}).get("regular") or data.get("urls", {}).get("full")
            if not img_url:
                return None
            return self._download_image(img_url, query)
        except Exception:
            return None

    def _download_image(self, img_url: str, query: str) -> Optional[str]:
        try:
            # Use headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(img_url, timeout=15, headers=headers, allow_redirects=True)
            resp.raise_for_status()
            
            # Check if response is actually an image
            content_type = resp.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                print(f"⚠ Warning: URL does not return an image (content-type: {content_type})")
                print(f"   URL: {img_url[:100]}...")
                # Still try to save it, might be an image with wrong content-type
            
            # Determine file extension from content-type or URL
            ext = ".jpg"
            if 'png' in content_type or img_url.lower().endswith('.png'):
                ext = ".png"
            elif 'gif' in content_type or img_url.lower().endswith('.gif'):
                ext = ".gif"
            elif 'webp' in content_type or img_url.lower().endswith('.webp'):
                ext = ".webp"
            
            fname = f"{uuid.uuid4().hex}_{self._safe_name(query)}{ext}"
            fpath = self.storage_dir / fname
            with open(fpath, "wb") as f:
                f.write(resp.content)
            print(f"✓ Image saved: {fpath}")
            return str(fpath)
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error downloading image: {e}")
            return None
        except Exception as e:
            print(f"❌ Error saving image: {e}")
            return None

    def download_from_url(self, img_url: str, identifier: str = "preferred") -> Optional[str]:
        """Download an image from a direct URL and return local path."""
        if not img_url or not img_url.strip():
            return None
        try:
            # Validate URL format
            img_url = img_url.strip()
            if not (img_url.startswith("http://") or img_url.startswith("https://")):
                print(f"⚠ Invalid URL format: {img_url}")
                return None
            
            # Handle Google Drive/share URLs - convert to direct image URL if possible
            img_url = self._convert_google_drive_url(img_url)
            
            print(f"📥 Downloading image from: {img_url[:80]}...")
            return self._download_image(img_url, identifier)
        except Exception as e:
            print(f"❌ Error downloading image from URL {img_url}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _convert_google_drive_url(self, url: str) -> str:
        """Convert Google Drive/share URLs to direct image URLs if possible."""
        # Google Drive file ID pattern
        if "drive.google.com" in url or "docs.google.com" in url:
            # Extract file ID
            file_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
            if file_id_match:
                file_id = file_id_match.group(1)
                # Convert to direct image URL (for images)
                return f"https://drive.google.com/uc?export=view&id={file_id}"
        
        # Google Photos/share links - try to follow redirect and get direct URL
        if "photos.app.goo.gl" in url or "share.google" in url or "photos.google.com" in url:
            print(f"⚠ Google share link detected: {url}")
            print(f"   Attempting to resolve to direct image URL...")
            try:
                # Follow redirects to get the actual image URL
                resp = requests.get(url, allow_redirects=True, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                final_url = resp.url
                
                # If it's a Google Photos page, try to extract image URL
                if "photos.google.com" in final_url:
                    # Try to find image source in the page
                    # Google Photos pages have images with specific patterns
                    # This is a best-effort attempt
                    print(f"   Resolved to: {final_url}")
                    print(f"   ⚠ Google Photos page detected - may need direct image URL")
                    print(f"   💡 Tip: Right-click image → 'Copy image address' for direct URL")
                    return url  # Return original, let download attempt fail gracefully
                else:
                    # If redirect leads to a direct image, use it
                    if any(final_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        print(f"   ✓ Resolved to direct image: {final_url}")
                        return final_url
                    return final_url
            except Exception as e:
                print(f"   ❌ Could not resolve Google share link: {e}")
                print(f"   💡 Please use 'Copy image address' (right-click) instead of share link")
                return url
        
        return url

    def _safe_name(self, text: str) -> str:
        return "".join(c for c in text.lower().replace(" ", "_") if c.isalnum() or c in ("_", "-"))[:40]
