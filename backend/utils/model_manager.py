"""
Model Manager for switching between Gemini and Groq LLaMA models
"""
import os
import json
import time
from typing import Optional, Literal
from dotenv import load_dotenv
import requests

load_dotenv()

# Model types
ModelType = Literal["gemini", "groq_llama"]

class ModelManager:
    """Manages AI model switching between Gemini and Groq LLaMA"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self._gemini_model = None
        self._groq_client = None
        
    def _init_gemini(self):
        """Initialize Gemini model"""
        if not self.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment variables")
        
        if self._gemini_model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            self._gemini_model = genai.GenerativeModel('gemini-pro-latest')
        
        return self._gemini_model
    
    def _init_groq(self):
        """Initialize Groq LLaMA client"""
        if not self.groq_api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment variables")
        
        if self._groq_client is None:
            from groq import Groq
            self._groq_client = Groq(api_key=self.groq_api_key)
        
        return self._groq_client
    
    def detect_model_preference(self, user_input: str, default: ModelType = "gemini") -> ModelType:
        """
        Detect which model to use based on user input
        
        Looks for keywords like "use llama", "use groq", "fast mode", etc.
        """
        if not user_input:
            return default
        
        user_lower = user_input.lower()
        
        # Check for Groq/LLaMA keywords
        groq_keywords = [
            "use llama", "use groq", "switch to groq", "switch to llama",
            "fast mode", "use llama model", "groq model", "llama model",
            "llama3", "llama 3", "groq llama"
        ]
        
        for keyword in groq_keywords:
            if keyword in user_lower:
                return "groq_llama"
        
        # Check for Gemini keywords (explicit)
        gemini_keywords = [
            "use gemini", "switch to gemini", "gemini model"
        ]
        
        for keyword in gemini_keywords:
            if keyword in user_lower:
                return "gemini"
        
        return default
    
    def generate_content(self, prompt: str, model_type: ModelType = "gemini") -> str:
        """
        Generate content using the specified model
        
        Args:
            prompt: The prompt to send to the model
            model_type: "gemini" or "groq_llama"
        
        Returns:
            Generated text content
        """
        if model_type == "groq_llama":
            return self._generate_with_groq(prompt)
        else:
            # If Gemini requested but not available, fallback to Groq if present
            if not self.gemini_api_key and self.groq_api_key:
                return self._generate_with_groq(prompt)
            return self._generate_with_gemini(prompt)
    
    def _generate_with_gemini(self, prompt: str) -> str:
        """Generate content using Gemini"""
        model = self._init_gemini()
        response = model.generate_content(prompt)
        return response.text or ""
    
    def _generate_with_groq(self, prompt: str, max_retries: int = 3) -> str:
        """Generate content using Groq LLaMA via direct HTTP (avoid client proxies bug)
        
        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retry attempts for rate limit errors
        
        Returns:
            Generated text content
        
        Raises:
            RuntimeError: If API call fails after retries or for non-rate-limit errors
        """
        if not self.groq_api_key:
            raise RuntimeError("GROQ_API_KEY not set")

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            # Updated to currently supported Groq model
            # See https://console.groq.com/docs/deprecations
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert academic content generator. Generate detailed, faculty-ready educational content."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2048,  # stay within safe limits
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=60)
                
                # Handle rate limit errors (429) with retry
                if resp.status_code == 429:
                    error_data = {}
                    try:
                        error_data = resp.json()
                    except:
                        error_text = resp.text
                    
                    # Extract wait time from error response
                    wait_time = 1.0  # Default wait time in seconds
                    retry_after = None
                    
                    # Try to extract retry-after header
                    if "Retry-After" in resp.headers:
                        try:
                            retry_after = float(resp.headers["Retry-After"])
                            wait_time = retry_after
                        except:
                            pass
                    
                    # Try to extract wait time from error message
                    if not retry_after and error_data:
                        error_message = error_data.get("message", "")
                        if "try again in" in error_message.lower():
                            # Extract time from message like "try again in 994.999999ms"
                            import re
                            time_match = re.search(r"try again in ([\d.]+)\s*(ms|s|seconds?)", error_message.lower())
                            if time_match:
                                time_value = float(time_match.group(1))
                                time_unit = time_match.group(2)
                                if "ms" in time_unit:
                                    wait_time = time_value / 1000.0
                                else:
                                    wait_time = time_value
                    
                    # Calculate exponential backoff: wait_time * (2^attempt)
                    actual_wait = wait_time * (2 ** attempt)
                    # Cap at 60 seconds
                    actual_wait = min(actual_wait, 60.0)
                    
                    if attempt < max_retries - 1:
                        print(f"⚠️ Groq API rate limit reached. Waiting {actual_wait:.1f} seconds before retry {attempt + 1}/{max_retries}...")
                        time.sleep(actual_wait)
                        continue
                    else:
                        # Last attempt failed, raise with helpful message
                        error_msg = f"Groq API rate limit exceeded after {max_retries} retries. "
                        if retry_after:
                            error_msg += f"Please try again in {retry_after:.0f} seconds. "
                        else:
                            error_msg += "Please wait a moment and try again. "
                        error_msg += "Consider upgrading your Groq plan at https://console.groq.com/settings/billing for higher limits."
                        raise RuntimeError(error_msg)
                
                # Handle other HTTP errors
                if not resp.ok:
                    error_text = resp.text
                    try:
                        error_data = resp.json()
                        error_detail = error_data.get("message", error_data.get("error", {}).get("message", error_text))
                    except:
                        error_detail = error_text
                    
                    raise RuntimeError(f"Groq API error {resp.status_code}: {error_detail}")
                
                # Success - parse and return response
                data = resp.json()
                return data["choices"][0]["message"]["content"]
                
            except RuntimeError:
                # Re-raise RuntimeError (rate limit or API errors)
                raise
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = 2.0 * (2 ** attempt)  # Exponential backoff for timeouts
                    print(f"⚠️ Groq API timeout. Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError("Groq API request timed out after multiple retries. Please try again.")
            except Exception as e:
                # For other exceptions, try once more or raise
                if attempt < max_retries - 1:
                    wait_time = 1.0 * (2 ** attempt)
                    print(f"⚠️ Groq API error: {str(e)}. Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    last_error = e
                    continue
                else:
                    raise RuntimeError(f"Groq API error: {str(e)}")
        
        # Should not reach here, but just in case
        if last_error:
            raise RuntimeError(f"Groq API error after {max_retries} attempts: {str(last_error)}")
        raise RuntimeError("Groq API request failed for unknown reason")
    
    def is_model_available(self, model_type: ModelType) -> bool:
        """Check if a model is available (API key exists)"""
        if model_type == "groq_llama":
            return bool(self.groq_api_key)
        else:
            return bool(self.gemini_api_key)


