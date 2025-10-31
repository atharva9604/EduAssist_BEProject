#!/usr/bin/env python3
"""
Test script for API endpoints
"""

import requests
import json

def test_api():
    """Test the API endpoints"""
    base_url = "http://localhost:8000"
    
    print("Testing API endpoints...")
    
    # Test root endpoint
    try:
        response = requests.get(f"{base_url}/")
        print(f"Root endpoint: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Root endpoint error: {e}")
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health endpoint: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Health endpoint error: {e}")
    
    # Test PPT generation endpoint
    try:
        data = {
            "topic": "Photosynthesis",
            "num_slides": 6
        }
        response = requests.post(
            f"{base_url}/api/generate-ppt",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        print(f"PPT generation endpoint: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success', False)}")
            if result.get('success'):
                print(f"File: {result.get('presentation', {}).get('filename', 'Unknown')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"PPT generation error: {e}")

if __name__ == "__main__":
    test_api()

