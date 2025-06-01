#!/usr/bin/env python3
"""
Test script for the MeetingBaas webhook functionality.
This script simulates a webhook event from MeetingBaas.
"""

import sys
import json
import argparse
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def get_api_key():
    """Get the MeetingBaas API key from environment variables"""
    api_key = os.getenv("MEETING_BAAS_API_KEY")
    if not api_key:
        print("Error: MEETING_BAAS_API_KEY not found in .env file")
        sys.exit(1)
    return api_key

def get_webhook_url():
    """Get the webhook URL from environment variables or use localhost"""
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        # Default to localhost if no webhook URL is provided
        webhook_url = "http://localhost:8766/webhooks/meetingbaas"
    return webhook_url

def create_sample_transcript():
    """Create a sample transcript for testing"""
    return [
        {
            "speaker": "Meeting Bot",
            "words": [
                {"start": 0.0, "end": 0.5, "word": "Hello"},
                {"start": 0.6, "end": 1.0, "word": "everyone"},
                {"start": 1.1, "end": 1.5, "word": "welcome"},
                {"start": 1.6, "end": 2.0, "word": "to"},
                {"start": 2.1, "end": 2.5, "word": "the"},
                {"start": 2.6, "end": 3.0, "word": "meeting"}
            ]
        },
        {
            "speaker": "User",
            "words": [
                {"start": 4.0, "end": 4.5, "word": "Thanks"},
                {"start": 4.6, "end": 5.0, "word": "for"},
                {"start": 5.1, "end": 5.5, "word": "joining"},
                {"start": 5.6, "end": 6.0, "word": "us"},
                {"start": 6.1, "end": 6.5, "word": "today"}
            ]
        },
        {
            "speaker": "Meeting Bot",
            "words": [
                {"start": 7.0, "end": 7.5, "word": "Happy"},
                {"start": 7.6, "end": 8.0, "word": "to"},
                {"start": 8.1, "end": 8.5, "word": "be"},
                {"start": 8.6, "end": 9.0, "word": "here"}
            ]
        }
    ]

def send_complete_event(bot_id, webhook_url, api_key):
    """Send a 'complete' event to the webhook endpoint"""
    
    # Create a sample payload for a 'complete' event
    payload = {
        "event": "complete",
        "data": {
            "bot_id": bot_id,
            "mp4": "https://example.com/test-recording.mp4",
            "speakers": ["Meeting Bot", "User"],
            "transcript": create_sample_transcript()
        }
    }
    
    # Send the request
    headers = {
        "Content-Type": "application/json",
        "x-meeting-baas-api-key": api_key
    }
    
    print(f"Sending 'complete' event to {webhook_url} for bot {bot_id}")
    try:
        response = requests.post(webhook_url, json=payload, headers=headers)
        print(f"Response status code: {response.status_code}")
        print(f"Response body: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending webhook: {e}")
        return False

def send_failed_event(bot_id, webhook_url, api_key, error_message="Test error message"):
    """Send a 'failed' event to the webhook endpoint"""
    
    # Create a sample payload for a 'failed' event
    payload = {
        "event": "failed",
        "data": {
            "bot_id": bot_id,
            "error": error_message
        }
    }
    
    # Send the request
    headers = {
        "Content-Type": "application/json",
        "x-meeting-baas-api-key": api_key
    }
    
    print(f"Sending 'failed' event to {webhook_url} for bot {bot_id}")
    try:
        response = requests.post(webhook_url, json=payload, headers=headers)
        print(f"Response status code: {response.status_code}")
        print(f"Response body: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending webhook: {e}")
        return False

def send_status_change_event(bot_id, webhook_url, api_key, status="connected"):
    """Send a 'bot.status_change' event to the webhook endpoint"""
    
    # Create a sample payload for a 'bot.status_change' event
    payload = {
        "event": "bot.status_change",
        "data": {
            "bot_id": bot_id,
            "status": {
                "connection": status,
                "timestamp": "2023-05-01T12:00:00Z"
            }
        }
    }
    
    # Send the request
    headers = {
        "Content-Type": "application/json",
        "x-meeting-baas-api-key": api_key
    }
    
    print(f"Sending 'bot.status_change' event to {webhook_url} for bot {bot_id}")
    try:
        response = requests.post(webhook_url, json=payload, headers=headers)
        print(f"Response status code: {response.status_code}")
        print(f"Response body: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending webhook: {e}")
        return False

def main():
    """Main function"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test MeetingBaas webhook functionality")
    parser.add_argument(
        "--bot-id", 
        required=True, 
        help="Bot ID to use in the webhook event"
    )
    parser.add_argument(
        "--event", 
        choices=["complete", "failed", "status_change"],
        default="complete",
        help="Type of event to send"
    )
    parser.add_argument(
        "--webhook-url", 
        help="URL to send the webhook to (defaults to WEBHOOK_URL env var or localhost)"
    )
    parser.add_argument(
        "--api-key", 
        help="MeetingBaas API key (defaults to MEETING_BAAS_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    # Get the API key
    api_key = args.api_key or get_api_key()
    
    # Get the webhook URL
    webhook_url = args.webhook_url or get_webhook_url()
    
    # Send the appropriate event
    if args.event == "complete":
        success = send_complete_event(args.bot_id, webhook_url, api_key)
    elif args.event == "failed":
        success = send_failed_event(args.bot_id, webhook_url, api_key)
    elif args.event == "status_change":
        success = send_status_change_event(args.bot_id, webhook_url, api_key)
    
    if success:
        print("Webhook sent successfully!")
        print("You can now check the /transcripts endpoint to see if it was processed.")
    else:
        print("Failed to send webhook.")

if __name__ == "__main__":
    main() 