"""Service for handling meeting transcripts and recordings."""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
import aiohttp
import aiofiles
from fastapi import HTTPException
from pydantic import BaseModel

from app.models import MeetingCompletedData, MeetingFailedData, TranscriptSegment
from meetingbaas_pipecat.utils.logger import logger

# Define where transcript data will be stored
TRANSCRIPT_DIR = Path("data/transcripts")
RECORDING_DIR = Path("data/recordings")


class TranscriptMetadata(BaseModel):
    """Metadata about a stored transcript"""
    bot_id: str
    meeting_id: str
    timestamp: datetime
    duration: Optional[float] = None
    num_speakers: int
    recording_path: Optional[str] = None
    transcript_path: str


class TranscriptService:
    """Service for storing and retrieving meeting transcripts"""
    
    def __init__(self):
        """Initialize the transcript service."""
        # Create data directories if they don't exist
        TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        RECORDING_DIR.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache of transcript metadata
        self._metadata_cache: Dict[str, TranscriptMetadata] = {}
        self._load_existing_transcripts()
    
    def _load_existing_transcripts(self) -> None:
        """Load metadata for existing transcripts."""
        try:
            metadata_file = TRANSCRIPT_DIR / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    data = json.load(f)
                    for meeting_id, meta in data.items():
                        # Convert string timestamps to datetime objects
                        if isinstance(meta.get("timestamp"), str):
                            meta["timestamp"] = datetime.fromisoformat(meta["timestamp"])
                        self._metadata_cache[meeting_id] = TranscriptMetadata(**meta)
                logger.info(f"Loaded metadata for {len(self._metadata_cache)} transcripts")
        except Exception as e:
            logger.error(f"Error loading transcript metadata: {e}")
    
    def _save_metadata(self) -> bool:
        """Save the metadata cache to disk."""
        try:
            metadata_file = TRANSCRIPT_DIR / "metadata.json"
            # Convert metadata objects to dictionaries with ISO format timestamps
            data = {
                meeting_id: {
                    **meta.dict(),
                    "timestamp": meta.timestamp.isoformat()
                }
                for meeting_id, meta in self._metadata_cache.items()
            }
            with open(metadata_file, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving transcript metadata: {e}")
            return False
    
    async def save_meeting_transcript(self, 
                               bot_id: str, 
                               meeting_data: MeetingCompletedData) -> str:
        """
        Save a meeting transcript and download the recording.
        
        Args:
            bot_id: The ID of the bot that participated in the meeting
            meeting_data: The meeting completion data from MeetingBaas
            
        Returns:
            The meeting ID (which can be used to retrieve the transcript later)
        """
        # Generate a unique meeting ID based on timestamp
        meeting_id = f"{bot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save the transcript as JSON
        transcript_path = TRANSCRIPT_DIR / f"{meeting_id}_transcript.json"
        transcript_data = meeting_data.dict()
        
        try:
            async with aiofiles.open(transcript_path, "w") as f:
                await f.write(json.dumps(transcript_data, indent=2))
            
            # Calculate meeting duration if possible
            duration = None
            if meeting_data.transcript and len(meeting_data.transcript) > 0:
                # Try to calculate duration from first and last word timestamps
                first_segment = meeting_data.transcript[0]
                last_segment = meeting_data.transcript[-1]
                if first_segment.words and last_segment.words:
                    start_time = first_segment.words[0].start
                    end_time = last_segment.words[-1].end
                    duration = end_time - start_time
            
            # Save metadata
            metadata = TranscriptMetadata(
                bot_id=bot_id,
                meeting_id=meeting_id,
                timestamp=datetime.now(),
                duration=duration,
                num_speakers=len(meeting_data.speakers),
                transcript_path=str(transcript_path)
            )
            
            # Start downloading the recording in the background
            asyncio.create_task(self._download_recording(meeting_id, meeting_data.mp4, metadata))
            
            # Update metadata cache
            self._metadata_cache[meeting_id] = metadata
            self._save_metadata()
            
            return meeting_id
            
        except Exception as e:
            logger.error(f"Error saving meeting transcript: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save transcript: {str(e)}")
    
    async def _download_recording(self, meeting_id: str, mp4_url: str, metadata: TranscriptMetadata) -> None:
        """
        Download the meeting recording from the provided URL.
        
        Args:
            meeting_id: The meeting ID
            mp4_url: The S3 URL for the recording (expires in 2 hours)
            metadata: The transcript metadata to update with the recording path
        """
        recording_path = RECORDING_DIR / f"{meeting_id}.mp4"
        
        try:
            logger.info(f"Downloading recording for meeting {meeting_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(mp4_url) as response:
                    if response.status == 200:
                        # Stream the file to disk
                        async with aiofiles.open(recording_path, "wb") as f:
                            while True:
                                chunk = await response.content.read(1024 * 1024)  # 1MB chunks
                                if not chunk:
                                    break
                                await f.write(chunk)
                        
                        # Update metadata with recording path
                        metadata.recording_path = str(recording_path)
                        self._metadata_cache[meeting_id] = metadata
                        self._save_metadata()
                        
                        logger.info(f"Successfully downloaded recording for meeting {meeting_id}")
                    else:
                        logger.error(f"Failed to download recording: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error downloading recording for meeting {meeting_id}: {e}")
    
    async def get_transcript(self, meeting_id: str) -> Optional[Dict]:
        """
        Get the transcript data for a meeting.
        
        Args:
            meeting_id: The meeting ID
            
        Returns:
            The transcript data as a dictionary
        """
        metadata = self._metadata_cache.get(meeting_id)
        if not metadata:
            return None
        
        try:
            transcript_path = Path(metadata.transcript_path)
            if not transcript_path.exists():
                logger.error(f"Transcript file not found: {transcript_path}")
                return None
            
            async with aiofiles.open(transcript_path, "r") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error reading transcript file: {e}")
            return None
    
    def get_recording_path(self, meeting_id: str) -> Optional[str]:
        """
        Get the path to the recording file for a meeting.
        
        Args:
            meeting_id: The meeting ID
            
        Returns:
            The path to the recording file, or None if not available
        """
        metadata = self._metadata_cache.get(meeting_id)
        if not metadata or not metadata.recording_path:
            return None
        
        recording_path = Path(metadata.recording_path)
        if not recording_path.exists():
            return None
        
        return str(recording_path)
    
    def list_transcripts(self) -> List[TranscriptMetadata]:
        """
        List all available transcripts.
        
        Returns:
            A list of transcript metadata objects
        """
        return list(self._metadata_cache.values())


# Create a singleton instance
transcript_service = TranscriptService() 