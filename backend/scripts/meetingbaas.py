import argparse
import asyncio
import os
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any

import aiohttp
import numpy as np
import pytz
from dotenv import load_dotenv
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
from pipecat.frames.frames import LLMMessagesFrame, TTSSpeakFrame, Frame, AudioRawFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.audio.utils import BaseAudioResampler

# from pipecat.services.gladia.stt import GladiaSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.network.websocket_client import (
    WebsocketClientParams,
    WebsocketClientTransport,
)

from config.persona_utils import PersonaManager
from config.prompts import DEFAULT_SYSTEM_PROMPT
from meetingbaas_pipecat.utils.logger import configure_logger

load_dotenv(override=True)

logger = configure_logger()


class SilenceDetectionProcessor(FrameProcessor):
    """
    Custom processor to detect extended silence periods and trigger appropriate responses.
    Specifically designed for executive/CXO personas to maintain meeting flow.
    """

    def __init__(self, persona_name: str = "", silence_threshold_seconds: float = 6.0, task=None):
        super().__init__()
        self.persona_name = persona_name
        self.silence_threshold_seconds = silence_threshold_seconds
        self.last_speech_time = time.time()
        self.silence_triggered = False
        self.conversation_started = False
        self.initial_grace_period = 10.0  # Don't trigger in first 10 seconds
        self.start_time = time.time()
        self.last_silence_trigger_time = 0.0  # Track when we last triggered silence
        self.min_silence_interval = 30.0  # Minimum 30 seconds between silence triggers
        self.task = task  # Store reference to task for buffer flushing
        
        # CXO-appropriate silence responses
        self.cxo_silence_responses = [
            "I'm not hearing anything. Are you on mute?",
            "Let's get back on track. Can you hear me?",
            "We've lost audio. Please check your connection.",
            "Are we still connected? I need to hear from the team.",
            "Time is valuable. Let me know when you're ready to continue.",
            "I'll pause here. Unmute when you're ready to proceed.",
            "We seem to have a technical issue. Please reconnect your audio.",
            "I need to hear your input to move this forward.",
            "Are you there? We have limited time for this discussion."
        ]
        
        # General silence responses for other personas
        self.general_silence_responses = [
            "I can't hear you. Are you there?",
            "Please check if you're muted.",
            "I'm not receiving any audio from you.",
            "Let me know when you're ready to continue.",
            "Are you still there? I don't hear anything."
        ]

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames to detect speech and silence periods."""
        
        # Call the parent class method first (required by pipecat framework)
        await super().process_frame(frame, direction)
        
        current_time = time.time()
        
        # Track speech activity from multiple sources
        speech_detected = False
        
        # Method 1: Check STT transcript frames (most reliable)
        if hasattr(frame, 'text') and frame.text:
            # If we get actual transcribed text, someone is definitely speaking
            if len(frame.text.strip()) > 0:
                speech_detected = True
                logger.debug(f"Speech detected via STT: '{frame.text}'")
        
        # Method 2: Check for user message frames (from aggregator)
        if hasattr(frame, 'messages') and frame.messages:
            # If we get user messages, someone is communicating
            for message in frame.messages:
                if message.get('role') == 'user' and message.get('content', '').strip():
                    speech_detected = True
                    logger.debug(f"User activity detected: '{message.get('content', '')[:50]}...'")
                    break
        
        # Method 3: Check for bot speech frames (TTSSpeakFrame)
        if isinstance(frame, TTSSpeakFrame):
            if frame.text and len(frame.text.strip()) > 0:
                speech_detected = True
                
                # Calculate estimated speech duration to properly reset timer
                # Average speaking rate is about 150-200 words per minute
                word_count = len(frame.text.split())
                estimated_duration = max(2.0, word_count / 2.5)  # At least 2 seconds, ~150 WPM
                
                # Set the last_speech_time to current time + estimated duration
                # This ensures silence detection doesn't trigger until AFTER the bot finishes speaking
                self.last_speech_time = current_time + estimated_duration
                logger.info(f"Bot speech detected: '{frame.text[:50]}...' (estimated {estimated_duration:.1f}s duration)")
                logger.debug(f"Silence timer extended to: {self.last_speech_time:.1f}")
        
        # Method 4: Check audio frames with level detection
        if isinstance(frame, AudioRawFrame):
            if hasattr(frame, 'audio') and frame.audio is not None:
                audio_data = frame.audio
                if len(audio_data) > 0:
                    try:
                        # Calculate basic audio level (RMS)
                        audio_array = np.frombuffer(audio_data, dtype=np.int16)
                        if len(audio_array) > 0:
                            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                            # If audio level is above threshold, consider it speech
                            if rms > 200:  # Lowered threshold from 300 to 200 for better detection
                                speech_detected = True
                                logger.debug(f"User speech detected via audio level: RMS={rms:.2f}")
                            # Occasionally log audio levels for debugging
                            if (current_time % 10) < 0.1:  # Log approximately every 10 seconds
                                logger.debug(f"Current audio RMS level: {rms:.2f}")
                    except Exception as e:
                        # If numpy processing fails, just continue
                        logger.warning(f"Error processing audio frame: {e}")
                        pass
        
        # Update speech tracking
        if speech_detected:
            # Only update last_speech_time if this is NOT a bot speech frame
            # For bot speech frames, we've already calculated the proper end time
            if not isinstance(frame, TTSSpeakFrame):
                self.last_speech_time = current_time
                # Explicitly log when we reset due to user speech
                logger.info("User speech detected - resetting silencer timer and flags")
            # Always reset silence_triggered to false when any speech is detected
            self.silence_triggered = False
            self.conversation_started = True
            logger.debug("Speech activity detected, resetting silence timer")

        # Check for extended silence
        elapsed_since_start = current_time - self.start_time
        silence_duration = current_time - self.last_speech_time
        time_since_last_trigger = current_time - self.last_silence_trigger_time
        
        # Only trigger if:
        # 1. Past initial grace period
        # 2. Conversation has started (someone has spoken at least once)
        # 3. Silence threshold exceeded
        # 4. Haven't already triggered recently
        # 5. Enough time has passed since last silence trigger
        if (elapsed_since_start > self.initial_grace_period and
            self.conversation_started and
            silence_duration > self.silence_threshold_seconds and
            not self.silence_triggered and
            time_since_last_trigger > self.min_silence_interval):
            
            logger.info(f"Extended silence detected: {silence_duration:.1f}s since last speech, {time_since_last_trigger:.1f}s since last trigger")
            self.silence_triggered = True
            self.last_silence_trigger_time = current_time
            await self._trigger_silence_response()

        # Pass the frame through
        await self.push_frame(frame, direction)

    async def _trigger_silence_response(self):
        """Trigger an appropriate silence response based on persona."""
        try:
            # Choose response based on persona type
            if self.persona_name and "cxo" in self.persona_name.lower():
                import random
                response_text = random.choice(self.cxo_silence_responses)
                logger.info(f"CXO silence response triggered: '{response_text}'")
            else:
                import random
                response_text = random.choice(self.general_silence_responses)
                logger.info(f"General silence response triggered: '{response_text}'")
            
            # Add a slight pause at the beginning for clearer notification
            # and speak slightly slower for better comprehension
            response = response_text
            
            # Calculate how long this silence response will take to speak
            word_count = len(response.split())
            estimated_duration = max(3.0, word_count / 2.0)  # Slightly slower than normal rate
            
            # Flush audio buffers if task is available to prevent stuttering
            if self.task:
                try:
                    await flush_audio_buffers(self.task)
                    logger.info("Audio buffers flushed before silence response")
                except Exception as e:
                    logger.warning(f"Could not flush audio buffers: {e}")
            
            # Add a small delay before speaking to allow audio buffers to clear
            await asyncio.sleep(0.5)
            
            # Create and queue the response frame
            silence_frame = TTSSpeakFrame(response)
            await self.push_frame(silence_frame, FrameDirection.DOWNSTREAM)
            
            # Reset the silence timer to AFTER this response finishes speaking
            # This prevents the silence detector from triggering again immediately
            # Use a longer buffer time to prevent stuttering or rapid re-triggering
            self.last_speech_time = time.time() + estimated_duration + 2.0  # Add 2.0s buffer (was 1.0s)
            logger.debug(f"Set last_speech_time to {self.last_speech_time} (now + {estimated_duration + 2.0}s)")
            
            # Allow re-triggering after another full silence period
            async def reset_silence_flag():
                try:
                    await asyncio.sleep(3.0)  # Reduced from 5.0 to 3.0 seconds
                    self.silence_triggered = False
                    logger.info("Silence triggered flag reset after timeout")
                except Exception as e:
                    # Make sure we reset the flag even if there's an error
                    self.silence_triggered = False
                    logger.error(f"Error in reset_silence_flag: {e}")
            
            # Create task with error handling
            try:
                asyncio.create_task(reset_silence_flag())
            except Exception as e:
                # Immediate fallback if task creation fails
                self.silence_triggered = False
                logger.error(f"Failed to create reset_silence_flag task: {e}")
            
        except Exception as e:
            logger.error(f"Error in silence response: {e}")

    def set_task(self, task):
        """Set the task reference for buffer flushing."""
        self.task = task
        logger.debug("Task reference set for silence detector")


# Function tool implementations
async def get_weather(
    function_name, tool_call_id, arguments, llm, context, result_callback
):
    """Get the current weather for a location."""
    location = arguments["location"]
    format = arguments["format"]  # Default to Celsius if not specified
    unit = (
        "m" if format == "celsius" else "u"
    )  # "m" for metric, "u" for imperial in wttr.in

    url = f"https://wttr.in/{location}?format=%t+%C&{unit}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                weather_data = await response.text()
                await result_callback(
                    f"The weather in {location} is currently {weather_data} ({format.capitalize()})."
                )
            else:
                await result_callback(
                    f"Failed to fetch the weather data for {location}."
                )


async def get_time(
    function_name, tool_call_id, arguments, llm, context, result_callback
):
    """Get the current time for a location."""
    location = arguments["location"]

    # Set timezone based on the provided location
    try:
        timezone = pytz.timezone(location)
        current_time = datetime.now(timezone)
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
        await result_callback(f"The current time in {location} is {formatted_time}.")
    except pytz.UnknownTimeZoneError:
        await result_callback(
            f"Invalid location specified. Could not determine time for {location}."
        )


# Helper function to convert speech_rate to speed
def _convert_speech_rate_to_speed(speech_rate):
    """
    Convert from speech_rate format (0.5-2.0) to speed format (-1.0 to 1.0)
    
    speech_rate 0.5 -> speed -1.0 (slowest)
    speech_rate 1.0 -> speed 0 (normal)
    speech_rate 2.0 -> speed 1.0 (fastest)
    
    Return None if speech_rate is outside valid range
    """
    if 0.5 <= speech_rate <= 2.0:
        # Linear conversion from one range to another
        return 2 * ((speech_rate - 0.5) / 1.5) - 1
    return None


async def main(
    meeting_url: str = "",
    persona_name: str = "Meeting Bot",
    entry_message: str = "Hello, I am the meeting bot",
    bot_image: str = "",
    streaming_audio_frequency: str = "16khz",
    websocket_url: str = "",
    enable_tools: bool = True,
    extra_data: Optional[Dict[str, Any]] = None,
    speech_rate: float = 0.85,
    enable_silence_detection: bool = True,
):
    """
    Main function to run the meeting bot with voice capability.
    """
    # Load environment variables
    load_dotenv()

    # Validate WebSocket URL
    if not websocket_url:
        logger.error("Error: WebSocket URL not provided")
        return

    logger.info(f"Using WebSocket URL: {websocket_url}")

    # Extract bot_id from the websocket_url if possible
    # Format is usually: ws://localhost:8766/pipecat/{client_id}
    parts = websocket_url.split("/")
    bot_id = parts[-1] if len(parts) > 3 else "unknown"
    logger.info(f"Using bot ID: {bot_id}")

    # Get persona configuration
    persona_manager = PersonaManager()
    persona = persona_manager.get_persona(persona_name)
    if not persona:
        logger.error(f"Persona '{persona_name}' not found")
        return

    # Load additional content from persona directory
    additional_content = persona.get("additional_content", "")
    
    # Process context_info from extra_data if available
    if extra_data and "context_info" in extra_data:
        context_info = extra_data.get("context_info", "").strip()
        if context_info:
            # Format the context info with a clear heading
            formatted_context = f"# MEETING CONTEXT INFORMATION\n\n{context_info}"
            
            # Prepend to additional_content to give it precedence
            if additional_content:
                additional_content = f"{formatted_context}\n\n{additional_content}"
            else:
                additional_content = formatted_context
                
            logger.info(f"Added context info to bot's knowledge: {context_info[:100]}...")

    # Auto-adjust streaming frequency based on persona's sample rate to prevent buffering
    tts_params = persona.get("tts_params", {})
    persona_sample_rate = tts_params.get("sample_rate", 16000)
    
    # Force 16000 Hz sample rate for CXO persona to fix voice cracking issue
    if persona_name and "cxo" in persona_name.lower():
        persona_sample_rate = 16000
        tts_params["sample_rate"] = 16000
        logger.info(f"Forcing 16kHz sample rate for CXO persona to prevent voice cracking")
        streaming_audio_frequency = "16khz"
    else:
        # For other personas, use auto-adjustment logic
        if persona_sample_rate >= 24000:
            streaming_audio_frequency = "24khz"
            logger.info(f"Auto-adjusted streaming frequency to 24khz based on persona sample rate: {persona_sample_rate}Hz")
        else:
            streaming_audio_frequency = "16khz"
            logger.info(f"Using 16khz streaming frequency for persona sample rate: {persona_sample_rate}Hz")

    # Set sample rate based on streaming_audio_frequency
    output_sample_rate = 24000 if streaming_audio_frequency == "24khz" else 16000
    # Silero VAD only supports 16000 or 8000 Hz
    vad_sample_rate = 16000

    logger.info(
        f"Using audio frequency: {streaming_audio_frequency} (output sample rate: {output_sample_rate}, VAD sample rate: {vad_sample_rate})"
    )

    # Create resampler for VAD if needed
    resampler = None
    if output_sample_rate != vad_sample_rate:
        try:
            resampler = BaseAudioResampler()
            logger.info(f"Created resampler for converting {output_sample_rate}Hz to {vad_sample_rate}Hz")
        except Exception as e:
            logger.warning(f"Failed to create resampler: {e}. This may cause audio issues.")
            # Continue without resampler if creation fails
            resampler = None

    # Set up the WebSocket transport with correct sample rates - use the full WebSocket URL directly
    transport = WebsocketClientTransport(
        uri=websocket_url,
        params=WebsocketClientParams(
            audio_out_sample_rate=output_sample_rate,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                sample_rate=16000,  # Must be either 8000 or 16000
                params=VADParams(
                    threshold=0.5,  # Lowered threshold from 0.6 to 0.5 for better detection
                    min_speech_duration_ms=80,  # Faster response (reduced from 100ms)
                    min_silence_duration_ms=300,  # Shorter silence for responsiveness
                    min_volume=0.4,  # Lower volume threshold from 0.5 to 0.4 for better pickup
                ),
            ),
            vad_audio_passthrough=True,
            serializer=ProtobufFrameSerializer(),
        ),
    )

    # Get voice ID from persona if available, otherwise use env var
    voice_id = persona.get("cartesia_voice_id") or os.getenv("CARTESIA_VOICE_ID")
    logger.info(f"Using voice ID: {voice_id}")
    
    # Get TTS parameters from persona if available
    tts_params = persona.get("tts_params", {})
    
    # For CXO persona, ensure speech rate is appropriate for executive communication
    if persona_name and "cxo" in persona_name.lower():
        # Use a more moderate speech rate for the CXO persona to prevent stuttering
        # 0.85 is good for executive communication - authoritative but clear
        tts_params["speech_rate"] = 0.85
        logger.info("Using moderate speech rate for CXO persona to ensure clarity")
        
    logger.info(f"Using TTS parameters: {tts_params}")

    # Initialize services
    # Use output_sample_rate for TTS to ensure consistency and prevent stuttering
    tts_sample_rate = tts_params.get("sample_rate", output_sample_rate)
    
    # For CXO persona, always force 16000 Hz to fix voice cracking
    if persona_name and "cxo" in persona_name.lower():
        tts_sample_rate = 16000
        output_sample_rate = 16000
        logger.info(f"Forcing consistent 16kHz sample rate for CXO bot to prevent voice cracking")
    else:
        # Always use output_sample_rate to prevent stuttering and maintain audio consistency
        # Override any persona-specific sample rate that might cause conflicts
        tts_sample_rate = output_sample_rate
        
    logger.info(f"Using consistent sample rate: {tts_sample_rate}Hz for both TTS and output")
    
    # Define a custom TTS frame preprocessor to handle special frames
    async def tts_frame_preprocessor(frame):
        """Pre-process TTS frames to handle special cases."""
        # Since we can't use metadata for silence frames, we'll always return the original frame
        return frame

    # Initialize TTS service with better default parameters for clear speech
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id=voice_id,  # Use voice ID from persona
        sample_rate=tts_sample_rate,  # Use consistent sample rate
        speech_rate=tts_params.get("speech_rate", 0.9),  # Slightly slower for clarity
        volume=tts_params.get("volume", 1.05),  # Slightly louder for better audibility
        pitch=tts_params.get("pitch", 1.0),  # Normal pitch
        style=tts_params.get("style", "calm"),  # Calm style for clear communication
        output_format="wav",  # Force WAV format for better compatibility
        language_code=tts_params.get("language_code", "en-US"),  # Use from tts_params or fallback
        ssml_enabled=False,  # Disable SSML to prevent parsing conflicts
        model="sonic-2-2025-03-07",  # Use older model that supports speech rate
        api_version="2024-11-13",  # Use API version that supports experimental controls
        # Note: We're keeping the speech_rate parameter for backward compatibility
        # but according to Cartesia documentation, it's deprecated in favor of
        # the speed control in __experimental_controls
        voice_options={
            "mode": "id",
            "id": voice_id,
            # Add __experimental_controls for speed and emotion as per the 2024-11-13 API documentation
            "__experimental_controls": {
                "speed": tts_params.get("speed") or _convert_speech_rate_to_speed(tts_params.get("speech_rate", 0.9)),
                "emotion": [tts_params.get("style", "calm")]  # Convert style to emotion format in an array
            }
        },
        frame_preprocessor=tts_frame_preprocessor  # Keep the preprocessor for future expansion
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
    )

    # Register function tools if enabled
    if enable_tools:
        logger.info("Registering function tools")

        # Register functions
        llm.register_function("get_weather", get_weather)
        llm.register_function("get_time", get_time)

        # Define function schemas
        weather_function = FunctionSchema(
            name="get_weather",
            description="Get the current weather",
            properties={
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA",
                },
                "format": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The temperature unit to use. Infer this from the users location.",
                },
            },
            required=["location", "format"],
        )

        time_function = FunctionSchema(
            name="get_time",
            description="Get the current time for a specific location",
            properties={
                "location": {
                    "type": "string",
                    "description": "The location for which to retrieve the current time (e.g., 'Asia/Kolkata', 'America/New_York')",
                },
            },
            required=["location"],
        )

        # Create tools schema
        tools = ToolsSchema(standard_tools=[weather_function, time_function])
    else:
        logger.info("Function tools are disabled")
        tools = None

    # Add speech-to-text service
    # Extract language code from persona if available
    language = persona.get("language_code", "en-US")
    logger.info(f"Using language: {language}")

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        encoding="linear16" if streaming_audio_frequency == "16khz" else "linear24",
        sample_rate=output_sample_rate,
        language=language,  # Use language from persona
    )
    # stt = GladiaSTTService(
    #     api_key=os.getenv("GLADIA_API_KEY"),
    #     encoding="linear16" if streaming_audio_frequency == "16khz" else "linear24",
    #     sample_rate=output_sample_rate,
    #     language=language,  # Use language from persona
    # )

    # Make sure we're setting a valid bot name
    bot_name = persona_name or "Bot"
    logger.info(f"Using bot name: {bot_name}")

    # Create a more comprehensive system prompt
    system_content = persona["prompt"]

    # Add additional context if available
    if additional_content:
        system_content += f"\n\nYou are {persona_name}\n\n{DEFAULT_SYSTEM_PROMPT}\n\n"
        system_content += "You have the following additional context. USE IT TO INFORM YOUR RESPONSES:\n\n"
        system_content += additional_content
        
    # Add special instructions to ensure concise and clean speech output
    system_content += "\n\nIMPORTANT SPEECH INSTRUCTIONS:\n"
    
    # Check if this is the CXO persona and add executive-specific speech patterns
    if persona_name and "cxo" in persona_name.lower():
        system_content += "1. SPEAK LIKE A C-SUITE EXECUTIVE. Use decisive, authoritative language that demonstrates leadership.\n"
        system_content += "2. Use executive shorthand and business terminology (ROI, KPIs, EBITDA, etc.) when appropriate.\n"
        system_content += "3. BE EXTREMELY BRIEF AND TO THE POINT. Executives value brevity - keep all responses under 3 sentences.\n"
        system_content += "4. Maintain executive presence by focusing ONLY on strategic priorities rather than details.\n"
        system_content += "5. Ask short, penetrating questions that drive accountability.\n"
        system_content += "6. NEVER say phrases like 'How can I assist you' or 'I'm here to help'—these sound like a chatbot, not an executive.\n"
        system_content += "7. EVERYTHING YOU SAY WILL BE SPOKEN OUT LOUD, so communicate naturally but concisely.\n"
        
        # Add specific communication patterns from sample conversations
        system_content += "\n\nUSE THESE EXECUTIVE COMMUNICATION PATTERNS:\n"
        system_content += "1. Begin with direct framing: 'Let me be direct.' 'This is unacceptable.' 'This requires immediate action.'\n"
        system_content += "2. Ask focused business questions: 'What are the key drivers?' 'Who's accountable?'\n"
        system_content += "3. Give specific timelines: 'I need that analysis by Thursday.'\n"
        system_content += "4. Structure responses briefly: 'First, assess impact. Second, identify solutions.'\n"
        system_content += "5. End with accountability: 'Who owns this?' 'When will it be done?'\n"
        system_content += "6. Use concise business language: 'P&L impact' 'competitive position' 'synergy targets'\n"
        system_content += "7. Be decisive: 'Here's what we'll do:' followed by 1-2 concrete actions.\n"
        system_content += "8. Frame issues strategically but briefly.\n"
        system_content += "9. CRITICAL: Keep all responses under 15 seconds of speaking time - be ruthlessly concise.\n"
        system_content += "10. NEVER use filler words or phrases like 'I believe', 'I think', or 'perhaps'.\n"
        system_content += "11. Use short, declarative sentences with active voice.\n"
        system_content += "12. Limit responses to 2-3 sentences maximum.\n"
        
        # Add context-awareness and conversation tracking instructions for CXO
        system_content += "\n\nCONTEXT AWARENESS AND CONVERSATION MANAGEMENT:\n"
        system_content += "1. MAINTAIN FULL MEMORY of the conversation to ensure continuity and context-aware responses.\n"
        system_content += "2. PROACTIVELY ASK RELEVANT QUESTIONS based on the meeting context - be specific, not generic.\n"
        system_content += "3. TRACK ACCOUNTABLE PARTIES mentioned during the conversation and follow up on them.\n" 
        system_content += "4. REFER TO METRICS and KPIs discussed earlier in the conversation.\n"
        system_content += "5. Show executive presence by staying LASER-FOCUSED ON THE MEETING OBJECTIVE at all times.\n"
        system_content += "6. IF YOU DON'T KNOW specific details from the meeting context, ASK pointed questions rather than making assumptions.\n"
        system_content += "7. CRITICAL: Always respond directly to what was just said rather than bringing up unrelated topics.\n"
        system_content += "8. If someone mentions new information, INCORPORATE IT into your mental model of the meeting.\n"
    else:
        # Standard instructions for other personas
        system_content += "1. BE EXTREMELY CONCISE. Keep your first response to 1-2 short sentences. Subsequent responses should be brief and to the point.\n"
        system_content += "2. NEVER use special characters like *, #, -, or markdown formatting in your responses, as they will be spoken literally.\n"
        system_content += "3. Avoid excessive punctuation, bullet points, or numbered lists.\n"
        system_content += "4. Do not say 'I am here to help' or similar intro phrases - get straight to the content.\n"
        system_content += "5. EVERYTHING YOU SAY WILL BE SPOKEN OUT LOUD, so communicate naturally as in a real conversation.\n"

    # Set up messages
    messages = [
        {
            "role": "system",
            "content": system_content,
        },
    ]

    # Create the context object - with or without tools
    if enable_tools and tools:
        context = OpenAILLMContext(messages, tools)
    else:
        context = OpenAILLMContext(messages)

    # Get the context aggregator pair using the LLM's method
    # This handles properly setting up the context aggregators
    aggregator_pair = llm.create_context_aggregator(context)

    # Get the user and assistant aggregators from the pair
    user_aggregator = aggregator_pair.user()
    assistant_aggregator = aggregator_pair.assistant()

    # Create pipeline components list
    pipeline_components = [transport.input()]
    
    # Add silence detection if enabled
    if enable_silence_detection:
        silence_detector = SilenceDetectionProcessor(
            persona_name=persona_name,
            silence_threshold_seconds=15.0  # Reduced from 20 to 15 seconds for quicker response
        )
        pipeline_components.append(silence_detector)
        
        logger.info(f"Silence detection enabled: 15-second threshold for {persona_name}")
        if persona_name and "cxo" in persona_name.lower():
            logger.info("Using CXO-style silence responses for executive presence")
    else:
        logger.info("Silence detection disabled")

    # Add remaining pipeline components
    pipeline_components.extend([
        stt,  # Add speech-to-text service
        user_aggregator,  # Process user input and update context
        llm,
        tts,
        transport.output(),
        assistant_aggregator,  # Store LLM responses in context
    ])

    # Create pipeline using the dynamic components list
    pipeline = Pipeline(pipeline_components)

    # Check if we have extra_data with initial_speech for the bot to speak
    extra_data = extra_data or {}
    initial_speech = extra_data.get("initial_speech", entry_message)
    
    # Debug logging to track frontend input
    logger.info(f"Extra data received: {extra_data}")
    logger.info(f"Initial speech from frontend: '{initial_speech}'")
    logger.info(f"Entry message fallback: '{entry_message}'")

    # Create and run task
    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))
    runner = PipelineRunner()

    # Set task reference in silence detector if enabled
    if enable_silence_detection:
        for component in pipeline_components:
            if isinstance(component, SilenceDetectionProcessor):
                component.set_task(task)
                logger.info("Connected task to silence detector for buffer management")
                break

    # Handle the initial greeting if needed
    if initial_speech:
        logger.info("Bot will speak first with an introduction")
        
        # Use the exact initial speech from frontend without LLM modification
        # Only enhance with knowledge base/context info if available
        final_initial_speech = initial_speech
        
        # Only enhance if there's substantial additional context AND the user wants enhancement
        # Keep this very minimal to preserve the exact frontend message
        if additional_content and len(additional_content.strip()) > 200:  # Only for substantial context
            # Only add very brief context if the original message is very generic
            if (len(initial_speech.strip()) < 50 and 
                any(word in initial_speech.lower() for word in ["hello", "hi", "greetings", "meeting"])):
                
                if persona_name and "cxo" in persona_name.lower():
                    # For CXO, only add if message doesn't already have executive tone
                    if not any(word in initial_speech.lower() for word in ["strategic", "priority", "results", "team"]):
                        final_initial_speech = initial_speech + " Let's focus on our strategic priorities."
                # For other personas, don't add anything to preserve exact frontend message
        
        logger.info(f"Using exact initial speech: '{final_initial_speech}'")

        # Queue the initial message to be spoken directly (bypassing LLM to avoid modification)
        async def queue_initial_message():
            await asyncio.sleep(2)  # Small delay to ensure transport is ready
            # Use TTSSpeakFrame to speak directly without LLM processing
            await task.queue_frames([TTSSpeakFrame(final_initial_speech)])
            logger.info("Initial greeting message queued for direct speech")

        # Create a task to queue the initial message
        asyncio.create_task(queue_initial_message())

    # Run the pipeline
    await runner.run(task)


async def flush_audio_buffers(task):
    """
    Helper function to flush audio buffers before sending important notifications.
    This helps prevent stuttering by ensuring all pending audio is processed.
    """
    try:
        # Create a small silent frame to flush buffers
        # This is an engineering technique to clear any pending audio
        silent_frame = AudioRawFrame(
            audio=b'\x00' * 1000,  # 1000 bytes of silence
            sample_rate=16000,
            num_channels=1
        )
        
        # Send the silent frame downstream to flush any pending audio
        logger.debug("Flushing audio buffers before important notification")
        await task.queue_frames([silent_frame])
        
        # Small pause to allow buffers to clear
        await asyncio.sleep(0.3)
        
        logger.debug("Audio buffers flushed")
    except Exception as e:
        logger.error(f"Error flushing audio buffers: {e}")
        # Continue even if flush fails


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run a MeetingBaas bot")
    parser.add_argument("--meeting-url", help="URL of the meeting to join")
    parser.add_argument(
        "--persona-name", default="Meeting Bot", help="Name to display for the bot"
    )
    parser.add_argument(
        "--entry-message",
        default="Hello, I am the meeting bot",
        help="Message to display in chat when joining",
    )
    parser.add_argument(
        "--initial-speech",
        default="",
        help="Message to speak when joining (if different from entry message)",
    )
    parser.add_argument("--bot-image", default="", help="URL for bot avatar")
    parser.add_argument(
        "--streaming-audio-frequency",
        default="16khz",
        choices=["16khz", "24khz"],
        help="Audio frequency for streaming (16khz or 24khz)",
    )
    parser.add_argument(
        "--websocket-url", help="Full WebSocket URL to connect to, including any path"
    )
    parser.add_argument(
        "--enable-tools",
        action="store_true",
        help="Enable function tools like weather and time",
    )
    parser.add_argument(
        "--speech-rate",
        type=float,
        default=0.85,
        help="Rate of speech (0.5 to 2.0, where 1.0 is normal speed)",
    )
    parser.add_argument(
        "--enable-silence-detection",
        action="store_true",
        default=True,
        help="Enable silence detection (enabled by default)",
    )
    parser.add_argument(
        "--disable-silence-detection",
        action="store_true",
        help="Disable silence detection",
    )

    args = parser.parse_args()
    
    # Handle silence detection arguments
    enable_silence_detection = args.enable_silence_detection and not args.disable_silence_detection
    
    # Create extra_data dictionary if initial-speech is provided
    extra_data = {}
    if args.initial_speech:
        extra_data["initial_speech"] = args.initial_speech

    # Run the bot
    asyncio.run(
        main(
            meeting_url=args.meeting_url,
            persona_name=args.persona_name,
            entry_message=args.entry_message,
            bot_image=args.bot_image,
            streaming_audio_frequency=args.streaming_audio_frequency,
            websocket_url=args.websocket_url,
            enable_tools=args.enable_tools,
            extra_data=extra_data,
            enable_silence_detection=enable_silence_detection,
            # Only pass speech_rate if the user specified it on the command line
            # (otherwise it will use the default in the function definition)
            **({"speech_rate": args.speech_rate} if args.speech_rate != 0.85 else {})
        )
    )
