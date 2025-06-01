"""API routes for the Speaking Meeting Bot application."""

import asyncio
import uuid
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.models import (
    BotRequest,
    JoinResponse,
    LeaveBotRequest,
    PersonaImageRequest,
    PersonaImageResponse,
    Persona,
    PersonaCreate,
    PersonaUpdate,
    MeetingWebhookEvent,
    MeetingCompletedData,
    MeetingFailedData,
    MeetingStatusData,
)
from app.services.image_service import image_service
from app.services.transcript_service import transcript_service
from config.persona_utils import persona_manager
from core.connection import MEETING_DETAILS, PIPECAT_PROCESSES, registry
from core.process import start_pipecat_process, terminate_process_gracefully
from core.router import router as message_router

# Import from the app module (will be defined in __init__.py)
from meetingbaas_pipecat.utils.logger import logger
from scripts.meetingbaas_api import create_meeting_bot, leave_meeting_bot
from utils.ngrok import (
    LOCAL_DEV_MODE,
    determine_websocket_url,
    log_ngrok_status,
    release_ngrok_url,
    update_ngrok_client_id,
)

router = APIRouter()

# Persona Management Routes
@router.get("/personas", response_model=List[Persona])
async def list_personas():
    """List all available personas."""
    try:
        personas = []
        for name, data in persona_manager.personas.items():
            persona = Persona(
                id=name,
                name=data.get("name", name),
                description=data.get("description", ""),
                personality=data.get("personality", ""),
                knowledge_base=data.get("knowledge_base", ""),
                image=data.get("image", ""),
            )
            personas.append(persona)
        return personas
    except Exception as e:
        logger.error(f"Error listing personas: {e}")
        raise HTTPException(status_code=500, detail="Failed to list personas")

@router.get("/personas/{persona_id}", response_model=Persona)
async def get_persona(persona_id: str):
    """Get a specific persona by ID."""
    try:
        if persona_id not in persona_manager.personas:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        data = persona_manager.personas[persona_id]
        return Persona(
            id=persona_id,
            name=data.get("name", persona_id),
            description=data.get("description", ""),
            personality=data.get("personality", ""),
            knowledge_base=data.get("knowledge_base", ""),
            image=data.get("image", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persona: {e}")
        raise HTTPException(status_code=500, detail="Failed to get persona")

@router.post("/personas", response_model=Persona, status_code=status.HTTP_201_CREATED)
async def create_persona(persona: PersonaCreate):
    """Create a new persona."""
    try:
        persona_id = str(uuid.uuid4())
        persona_data = persona.dict()
        persona_manager.personas[persona_id] = persona_data
        return Persona(id=persona_id, **persona_data)
    except Exception as e:
        logger.error(f"Error creating persona: {e}")
        raise HTTPException(status_code=500, detail="Failed to create persona")

@router.put("/personas/{persona_id}", response_model=Persona)
async def update_persona(persona_id: str, persona: PersonaUpdate):
    """Update an existing persona."""
    try:
        if persona_id not in persona_manager.personas:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        persona_data = persona.dict()
        persona_manager.personas[persona_id].update(persona_data)
        return Persona(id=persona_id, **persona_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating persona: {e}")
        raise HTTPException(status_code=500, detail="Failed to update persona")

@router.delete("/personas/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(persona_id: str):
    """Delete a persona."""
    try:
        if persona_id not in persona_manager.personas:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        del persona_manager.personas[persona_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting persona: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete persona")

@router.post(
    "/bots",
    tags=["bots"],
    response_model=JoinResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Bot successfully created and joined the meeting"},
        400: {"description": "Bad request - Missing required fields or invalid data"},
        500: {
            "description": "Server error - Failed to create bot through MeetingBaas API"
        },
    },
)
async def join_meeting(request: BotRequest, client_request: Request):
    """
    Create and deploy a speaking bot in a meeting.

    Launches an AI-powered bot that joins a video meeting through MeetingBaas
    and processes audio using Pipecat's voice AI framework.
    """
    # Validate required parameters
    if not request.meeting_url:
        return JSONResponse(
            content={"message": "Meeting URL is required", "status": "error"},
            status_code=400,
        )

    # Get API key from request state (set by middleware)
    api_key = client_request.state.api_key

    # Get webhook URL from request or .env file
    webhook_url = request.webhook_url
    if not webhook_url:
        # Try to get webhook URL from environment variables
        import os
        from dotenv import load_dotenv
        
        # Load .env file if it exists
        load_dotenv()
        
        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url:
            logger.info(f"Using webhook URL from .env file: {webhook_url}")

    # Log local dev mode status
    if LOCAL_DEV_MODE:
        logger.info("🔍 Running in LOCAL_DEV_MODE - will prioritize ngrok URLs")
    else:
        logger.info("🔍 Running in standard mode")

    # Determine WebSocket URL (works in all cases now)
    websocket_url, temp_client_id = determine_websocket_url(None, client_request)

    logger.info(f"Starting bot for meeting {request.meeting_url}")
    logger.info(f"WebSocket URL: {websocket_url}")
    logger.info(f"Bot name: {request.bot_name}")

    # INTERNAL PARAMETER: Set a fixed value for streaming_audio_frequency
    # This is not exposed in the API and is always "16khz"
    streaming_audio_frequency = "16khz"
    logger.info(f"Using fixed streaming audio frequency: {streaming_audio_frequency}")

    # Set the converter sample rate based on our fixed streaming_audio_frequency
    from core.converter import converter

    sample_rate = 16000  # Always 16000 Hz for 16khz audio
    converter.set_sample_rate(sample_rate)
    logger.info(
        f"Set audio sample rate to {sample_rate} Hz for {streaming_audio_frequency}"
    )

    # Generate a unique client ID for this bot
    bot_client_id = str(uuid.uuid4())

    # If we're in local dev mode and we have a temp client ID, update the mapping
    if LOCAL_DEV_MODE and temp_client_id:
        update_ngrok_client_id(temp_client_id, bot_client_id)
        log_ngrok_status()

    # Select the persona - use provided one or pick a random one
    if request.personas and len(request.personas) > 0:
        persona_name = request.personas[0]
        logger.info(f"Using specified persona: {persona_name}")
    else:
        # Use the bot_name as the persona name if no personas are specified
        persona_name = request.bot_name
        logger.info(f"Using bot_name as persona: {persona_name}")

        # If the persona doesn't exist, try to use a random one
        if persona_name not in persona_manager.personas:
            import random

            available_personas = list(persona_manager.personas.keys())
            if available_personas:
                persona_name = random.choice(available_personas)
                logger.info(f"Persona not found, using random persona: {persona_name}")
            else:
                # Fallback to baas_onboarder if we somehow can't get the personas list
                persona_name = "baas_onboarder"
                logger.warning(
                    "No personas found, using fallback persona: baas_onboarder"
                )

    # Get the persona data
    persona = persona_manager.get_persona(persona_name)

    # Store meeting details for when the WebSocket connects
    # Also store streaming_audio_frequency, entry_message and text_message
    MEETING_DETAILS[bot_client_id] = (
        request.meeting_url,
        persona_name,
        None,  # MeetingBaas bot ID will be set after creation
        request.enable_tools,
        streaming_audio_frequency,
        request.entry_message,  # Store entry_message in MEETING_DETAILS
        request.text_message,  # Store text_message in MEETING_DETAILS
    )

    # Get image from persona if not specified in request
    bot_image = request.bot_image
    if not bot_image and persona.get("image"):
        # Ensure the image is a string
        try:
            # Convert to string no matter what type it is
            bot_image = str(persona.get("image"))
            logger.info(f"Using persona image: {bot_image}")
        except Exception as e:
            logger.error(f"Error converting persona image to string: {e}")
            bot_image = None

    # Ensure the bot_image is definitely a string or None
    if bot_image is not None:
        try:
            bot_image_str = str(bot_image)
            logger.info(f"Final bot image URL: {bot_image_str}")
        except Exception as e:
            logger.error(f"Failed to convert bot image to string: {e}")
            bot_image_str = None
    else:
        bot_image_str = None

    # Prepare extra data with context_info if provided
    extra_data = request.extra or {}
    if request.context_info:
        extra_data["context_info"] = request.context_info
        logger.info(f"Added context info to bot: {request.context_info[:100]}...")

    # Create bot directly through MeetingBaas API
    meetingbaas_bot_id = create_meeting_bot(
        meeting_url=request.meeting_url,
        websocket_url=websocket_url,
        bot_id=bot_client_id,
        persona_name=persona.get("name", persona_name),  # Use persona display name
        api_key=api_key,
        bot_image=bot_image_str,  # Use the pre-stringified value
        entry_message=request.entry_message,
        text_message=request.text_message,  # Add text message for chat
        extra=extra_data,
        streaming_audio_frequency=streaming_audio_frequency,
        webhook_url=webhook_url,  # Pass the webhook URL
    )

    if meetingbaas_bot_id:
        # Update the meetingbaas_bot_id in MEETING_DETAILS
        MEETING_DETAILS[bot_client_id] = (
            request.meeting_url,
            persona_name,
            meetingbaas_bot_id,
            request.enable_tools,
            streaming_audio_frequency,
            request.entry_message,  # Keep the entry_message
            request.text_message,  # Keep the text_message
        )

        # Log the client_id for internal reference
        logger.info(f"Bot created with MeetingBaas bot_id: {meetingbaas_bot_id}")
        logger.info(f"Internal client_id for WebSocket connections: {bot_client_id}")

        # Return only the bot_id in the response
        return JoinResponse(bot_id=meetingbaas_bot_id)
    else:
        return JSONResponse(
            content={
                "message": "Failed to create bot through MeetingBaas API",
                "status": "error",
            },
            status_code=500,
        )


@router.delete(
    "/bots/{bot_id}",
    tags=["bots"],
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Bot successfully removed from meeting"},
        400: {"description": "Bad request - Missing required fields or identifiers"},
        404: {"description": "Bot not found - No bot with the specified ID"},
        500: {
            "description": "Server error - Failed to remove bot from MeetingBaas API"
        },
    },
)
async def leave_bot(
    bot_id: str,
    request: LeaveBotRequest,
    client_request: Request,
):
    """
    Remove a bot from a meeting by its ID.

    This will:
    1. Call the MeetingBaas API to make the bot leave
    2. Close WebSocket connections if they exist
    3. Terminate the associated Pipecat process
    """
    logger.info(f"Removing bot with ID: {bot_id}")
    # Get API key from request state (set by middleware)
    api_key = client_request.state.api_key

    # Verify we have the bot_id
    if not bot_id and not request.bot_id:
        return JSONResponse(
            content={
                "message": "Bot ID is required",
                "status": "error",
            },
            status_code=400,
        )

    # Use the path parameter bot_id if provided, otherwise use request.bot_id
    meetingbaas_bot_id = bot_id or request.bot_id
    client_id = None

    # Look through MEETING_DETAILS to find the client ID for this bot ID
    for cid, details in MEETING_DETAILS.items():
        # Check if the stored meetingbaas_bot_id matches
        if len(details) >= 3 and details[2] == meetingbaas_bot_id:
            client_id = cid
            logger.info(f"Found client ID {client_id} for bot ID {meetingbaas_bot_id}")
            break

    if not client_id:
        logger.warning(f"No client ID found for bot ID {meetingbaas_bot_id}")

    success = True

    # 1. Call MeetingBaas API to make the bot leave
    if meetingbaas_bot_id:
        logger.info(f"Removing bot with ID: {meetingbaas_bot_id} from MeetingBaas API")
        result = leave_meeting_bot(
            bot_id=meetingbaas_bot_id,
            api_key=api_key,
        )
        if not result:
            success = False
            logger.error(
                f"Failed to remove bot {meetingbaas_bot_id} from MeetingBaas API"
            )
    else:
        logger.warning("No MeetingBaas bot ID or API key found, skipping API call")

    # 2. Close WebSocket connections if they exist
    if client_id:
        # Mark the client as closing to prevent further messages
        message_router.mark_closing(client_id)

        # Close Pipecat WebSocket first
        if client_id in registry.pipecat_connections:
            try:
                await registry.disconnect(client_id, is_pipecat=True)
                logger.info(f"Closed Pipecat WebSocket for client {client_id}")
            except Exception as e:
                success = False
                logger.error(f"Error closing Pipecat WebSocket: {e}")

        # Then close client WebSocket if it exists
        if client_id in registry.active_connections:
            try:
                await registry.disconnect(client_id, is_pipecat=False)
                logger.info(f"Closed client WebSocket for client {client_id}")
            except Exception as e:
                success = False
                logger.error(f"Error closing client WebSocket: {e}")

        # Add a small delay to allow for clean disconnection
        await asyncio.sleep(0.5)

    # 3. Terminate the Pipecat process after WebSockets are closed
    if client_id and client_id in PIPECAT_PROCESSES:
        process = PIPECAT_PROCESSES[client_id]
        if process and process.poll() is None:  # If process is still running
            try:
                if terminate_process_gracefully(process, timeout=3.0):
                    logger.info(
                        f"Gracefully terminated Pipecat process for client {client_id}"
                    )
                else:
                    logger.warning(
                        f"Had to forcefully kill Pipecat process for client {client_id}"
                    )
            except Exception as e:
                success = False
                logger.error(f"Error terminating Pipecat process: {e}")

        # Remove from our storage
        PIPECAT_PROCESSES.pop(client_id, None)

        # Clean up meeting details
        if client_id in MEETING_DETAILS:
            MEETING_DETAILS.pop(client_id, None)

        # Release ngrok URL if in local dev mode
        if LOCAL_DEV_MODE and client_id:
            release_ngrok_url(client_id)
            log_ngrok_status()
    else:
        logger.warning(f"No Pipecat process found for client {client_id}")

    return {
        "message": "Bot removal request processed",
        "status": "success" if success else "partial",
        "bot_id": meetingbaas_bot_id,
    }

@router.post(
    "/bots/{bot_id}/stop",
    tags=["bots"],
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Bot successfully removed from meeting"},
        400: {"description": "Bad request - Missing required fields or identifiers"},
        404: {"description": "Bot not found - No bot with the specified ID"},
        500: {
            "description": "Server error - Failed to remove bot from MeetingBaas API"
        },
    },
)
async def stop_bot(
    bot_id: str,
    client_request: Request,
):
    """
    Remove a bot from a meeting by its ID using POST method.
    This is an alias for the DELETE /bots/{bot_id} endpoint for frontend compatibility.
    """
    logger.info(f"Stopping bot with ID (POST method): {bot_id}")
    
    # Create an empty request body since the DELETE endpoint expects one
    request = LeaveBotRequest()
    
    # Call the existing leave_bot function
    return await leave_bot(bot_id, request, client_request)

@router.post(
    "/personas/generate-image",
    tags=["personas"],
    response_model=PersonaImageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Image successfully generated"},
        400: {"description": "Invalid request data"},
    },
)
def generate_persona_image(request: PersonaImageRequest) -> PersonaImageResponse:
    """Generate an image for a persona using Replicate."""
    try:
        # Build the prompt from available fields
        # Build the prompt using a more concise approach
        name = request.name
        prompt = f"A detailed professional portrait of a single person named {name}"

        if request.gender:
            prompt += f". {request.gender.capitalize()}"

        if request.description:
            cleaned_desc = request.description.strip().rstrip(".")
            prompt += f". Who {cleaned_desc}"

        if request.characteristics and len(request.characteristics) > 0:
            traits = ", ".join(request.characteristics)
            prompt += f". With features like {traits}"

        # Add standard quality guidelines
        prompt += ". High quality, single person, only face and shoulders, centered, neutral background, avoid borders."

        # Generate the image
        image_response = image_service.generate_persona_image(
            name=name, prompt=prompt, style="realistic", size=(512, 512)
        )

        return PersonaImageResponse(
            name=name,
            image_url=image_response,
            generated_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        if isinstance(e, ValueError):
            # ValueError typically indicates invalid input
            status_code = status.HTTP_400_BAD_REQUEST
        elif "connection" in str(e).lower() or "timeout" in str(e).lower():
            # Network errors should be 503 Service Unavailable
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            # Default to internal server error
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=status_code, detail=str(e))

@router.get(
    "/bots",
    tags=["bots"],
    response_model=List[Dict[str, Any]],
    responses={
        200: {"description": "List of active bots"},
        500: {"description": "Server error - Failed to list bots"},
    },
)
async def list_bots():
    """
    Get a list of all active bots.
    
    Returns a list of bots with their details including:
    - bot_id: The MeetingBaas bot ID
    - name: The bot's name
    - meeting_url: The URL of the meeting the bot is in
    - personas: List of persona IDs assigned to the bot
    """
    try:
        bots = []
        for client_id, details in MEETING_DETAILS.items():
            if len(details) >= 3:  # Ensure we have all required details
                meeting_url, persona_name, meetingbaas_bot_id = details[:3]
                if meetingbaas_bot_id:  # Only include bots that have been created
                    bots.append({
                        "id": meetingbaas_bot_id,
                        "name": persona_name,
                        "meeting_url": meeting_url,
                        "personas": [persona_name],  # Currently only one persona per bot
                    })
        return bots
    except Exception as e:
        logger.error(f"Error listing bots: {e}")
        raise HTTPException(status_code=500, detail="Failed to list bots")

@router.get(
    "/active-bots",
    tags=["bots"],
    response_model=List[Dict[str, Any]],
    responses={
        200: {"description": "List of active bots"},
        500: {"description": "Server error - Failed to list active bots"},
    },
)
async def list_active_bots():
    """
    Get a list of all active bots with additional details.
    
    Returns a list of active bots with their details including:
    - id: The MeetingBaas bot ID
    - name: The bot's name
    - meeting_url: The URL of the meeting the bot is in
    - personas: List of persona IDs assigned to the bot
    - status: The current status of the bot
    - start_time: When the bot was started
    """
    try:
        bots = []
        for client_id, details in MEETING_DETAILS.items():
            if len(details) >= 3:  # Ensure we have all required details
                meeting_url, persona_name, meetingbaas_bot_id = details[:3]
                if meetingbaas_bot_id:  # Only include bots that have been created
                    # Try to get the persona details
                    persona_details = {}
                    if persona_name in persona_manager.personas:
                        persona_details = persona_manager.personas[persona_name]
                    
                    bots.append({
                        "id": meetingbaas_bot_id,
                        "name": persona_name,
                        "meeting_url": meeting_url,
                        "personas": [persona_name],  # Currently only one persona per bot
                        "status": "active",  # Since it's in MEETING_DETAILS, it's active
                        "start_time": datetime.utcnow().isoformat(),  # Approximate time
                        "persona": {
                            "id": persona_name,
                            "name": persona_details.get("name", persona_name),
                            "description": persona_details.get("description", ""),
                            "image": persona_details.get("image", ""),
                        }
                    })
        return bots
    except Exception as e:
        logger.error(f"Error listing active bots: {e}")
        raise HTTPException(status_code=500, detail="Failed to list active bots")

@router.post(
    "/webhooks/meetingbaas",
    tags=["webhooks"],
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Webhook data processed successfully"},
        400: {"description": "Bad request - Invalid webhook data format"},
        500: {"description": "Server error - Failed to process webhook data"},
    },
)
async def meetingbaas_webhook(webhook_event: MeetingWebhookEvent):
    """
    Webhook endpoint for MeetingBaas to send meeting events.
    
    This endpoint receives event data when a meeting is completed, failed, or has a status change.
    For completed meetings, it saves the transcript and initiates download of the recording.
    """
    try:
        logger.info(f"Received MeetingBaas webhook event: {webhook_event.event}")
        
        if webhook_event.event == "complete":
            # Parse the completed meeting data
            meeting_data = MeetingCompletedData(**webhook_event.data)
            bot_id = meeting_data.bot_id
            
            # Save the transcript and recording
            meeting_id = await transcript_service.save_meeting_transcript(bot_id, meeting_data)
            
            logger.info(f"Meeting completed webhook processed. Meeting ID: {meeting_id}")
            return {
                "status": "success",
                "message": "Meeting transcript saved",
                "meeting_id": meeting_id,
            }
            
        elif webhook_event.event == "failed":
            # Parse the failed meeting data
            failed_data = MeetingFailedData(**webhook_event.data)
            logger.error(f"Meeting failed: {failed_data.error}")
            
            return {
                "status": "error",
                "message": "Meeting failed",
                "error": failed_data.error,
            }
            
        elif webhook_event.event == "bot.status_change":
            # Parse the status change data
            status_data = MeetingStatusData(**webhook_event.data)
            logger.info(f"Bot status changed: {status_data.status}")
            
            return {
                "status": "success",
                "message": "Bot status change recorded",
            }
            
        else:
            logger.warning(f"Unknown webhook event: {webhook_event.event}")
            return {
                "status": "error",
                "message": f"Unknown webhook event: {webhook_event.event}",
            }
            
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}",
        )

# Add transcript management endpoints

@router.get(
    "/transcripts",
    tags=["transcripts"],
    response_model=List[Dict[str, Any]],
    responses={
        200: {"description": "List of all available meeting transcripts"},
        500: {"description": "Server error - Failed to list transcripts"},
    },
)
async def list_transcripts():
    """
    List all available meeting transcripts.
    
    Returns a list of transcript metadata including meeting ID, bot ID, timestamp,
    duration, and number of speakers.
    """
    try:
        transcripts = transcript_service.list_transcripts()
        
        # Convert to serializable format
        result = []
        for t in transcripts:
            result.append({
                "meeting_id": t.meeting_id,
                "bot_id": t.bot_id,
                "timestamp": t.timestamp.isoformat(),
                "duration": t.duration,
                "num_speakers": t.num_speakers,
                "has_recording": t.recording_path is not None,
            })
            
        return result
        
    except Exception as e:
        logger.error(f"Error listing transcripts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list transcripts: {str(e)}",
        )

@router.get(
    "/transcripts/{meeting_id}",
    tags=["transcripts"],
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Transcript data for the specified meeting"},
        404: {"description": "Meeting transcript not found"},
        500: {"description": "Server error - Failed to retrieve transcript"},
    },
)
async def get_transcript(meeting_id: str):
    """
    Get the transcript data for a specific meeting.
    
    Returns the full transcript including speaker segments and word-level timing.
    """
    try:
        transcript_data = await transcript_service.get_transcript(meeting_id)
        
        if not transcript_data:
            raise HTTPException(
                status_code=404,
                detail=f"Transcript not found for meeting ID: {meeting_id}",
            )
            
        return transcript_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving transcript: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve transcript: {str(e)}",
        )

@router.get(
    "/transcripts/{meeting_id}/download",
    tags=["transcripts"],
    response_class=StreamingResponse,
    responses={
        200: {"description": "Transcript file download"},
        404: {"description": "Meeting transcript not found"},
        500: {"description": "Server error - Failed to download transcript"},
    },
)
async def download_transcript(meeting_id: str):
    """
    Download the transcript for a specific meeting as a JSON file.
    """
    try:
        transcript_data = await transcript_service.get_transcript(meeting_id)
        
        if not transcript_data:
            raise HTTPException(
                status_code=404,
                detail=f"Transcript not found for meeting ID: {meeting_id}",
            )
            
        # Convert to JSON string
        json_data = json.dumps(transcript_data, indent=2)
        
        # Create a byte stream
        stream = BytesIO(json_data.encode())
        
        # Return as a downloadable JSON file
        return StreamingResponse(
            stream, 
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=transcript_{meeting_id}.json"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading transcript: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download transcript: {str(e)}",
        )

@router.get(
    "/transcripts/{meeting_id}/recording",
    tags=["transcripts"],
    response_class=StreamingResponse,
    responses={
        200: {"description": "Meeting recording download"},
        404: {"description": "Meeting recording not found"},
        500: {"description": "Server error - Failed to download recording"},
    },
)
async def download_recording(meeting_id: str):
    """
    Download the recording for a specific meeting as an MP4 file.
    """
    try:
        recording_path = transcript_service.get_recording_path(meeting_id)
        
        if not recording_path:
            raise HTTPException(
                status_code=404,
                detail=f"Recording not found for meeting ID: {meeting_id}",
            )
            
        # Open the file for streaming
        file_path = Path(recording_path)
        
        def iterfile():
            with open(file_path, "rb") as f:
                while chunk := f.read(1024 * 1024):  # 1MB chunks
                    yield chunk
            
        # Return as a downloadable MP4 file
        return StreamingResponse(
            iterfile(), 
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"attachment; filename=recording_{meeting_id}.mp4"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading recording: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download recording: {str(e)}",
        )
