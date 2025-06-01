import argparse
import asyncio
import os
import random
import subprocess
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from loguru import logger

from config.persona_utils import (
    PersonaManager,
)
from config.prompts import DEFAULT_CHARACTERISTICS as PROMPTS_CHARACTERISTICS
from config.prompts import (
    DEFAULT_ENTRY_MESSAGE,
    DEFAULT_TEXT_MESSAGE,
    DEFAULT_SYSTEM_PROMPT,
    IS_ANIMAL,
    SKIN_TONES,
)
from config.prompts import (
    DEFAULT_VOICE_CHARACTERISTICS as PROMPTS_VOICE_CHARACTERISTICS,
)
from config.voice_utils import VoiceUtils, get_language_input
from meetingbaas_pipecat.utils.logger import configure_logger

# Load environment variables
load_dotenv()
REPLICATE_KEY = os.getenv("REPLICATE_KEY")
UTFS_KEY = os.getenv("UTFS_KEY")
APP_ID = os.getenv("APP_ID")

logger = configure_logger()


def create_persona_structure(
    key: str,
    name: Optional[str] = None,
    prompt: Optional[str] = None,
    entry_message: Optional[str] = None,
    text_message: Optional[str] = None,
    speech_rate: Optional[float] = None,
    tts_params: Optional[str] = None,
    characteristics: Optional[list] = None,
    tone_of_voice: Optional[list] = None,
    skin_tone: Optional[str] = None,
    gender: Optional[str] = None,
    relevant_links: Optional[list] = None,
) -> Dict:
    """Create a persona dictionary with provided or default values"""
    # If no skin tone provided, randomly select one (unless it's an animal)
    if not skin_tone and not IS_ANIMAL:
        skin_tone = random.choice(SKIN_TONES)
        logger.info(f"Randomly selected skin tone: {skin_tone}")

    if not gender:
        gender = random.choice(["MALE", "FEMALE", "NON-BINARY"])
        logger.info(f"Randomly selected gender: {gender}")

    # Process TTS params if provided
    tts_params_dict = None
    if tts_params:
        try:
            import json
            tts_params_dict = json.loads(tts_params)
            logger.info(f"Parsed TTS parameters: {tts_params_dict}")
        except Exception as e:
            logger.error(f"Failed to parse TTS parameters JSON: {e}")

    return {
        "name": name or key.replace("_", " ").title(),
        "prompt": prompt or DEFAULT_SYSTEM_PROMPT,
        "entry_message": entry_message or DEFAULT_ENTRY_MESSAGE,
        "text_message": text_message or DEFAULT_TEXT_MESSAGE,
        "speech_rate": speech_rate or 1.0,
        "tts_params": tts_params_dict,
        "characteristics": characteristics or PROMPTS_CHARACTERISTICS,
        "tone_of_voice": tone_of_voice or PROMPTS_VOICE_CHARACTERISTICS,
        "skin_tone": skin_tone,
        "gender": gender,
        "relevant_links": relevant_links or [],
        "image": "",  # Will be populated by image generation
    }


def generate_persona_image(
    persona_key: str, replicate_key: str, utfs_key: str, app_id: str
):
    """Generate and upload image for the persona"""
    try:
        cmd = [
            "python",
            "config/generate_images.py",
            "--replicate-key",
            replicate_key,
            "--utfs-key",
            utfs_key,
            "--app-id",
            app_id,
        ]

        subprocess.run(cmd, check=True)
        logger.success(f"Generated and uploaded image for {persona_key}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate image: {e}")
        raise


async def create_persona_cli():
    parser = argparse.ArgumentParser(
        description="""Interactive persona creation tool for the meeting bot.
        
The persona key should be in snake_case format (e.g., tech_expert, friendly_interviewer).
If not provided via command line, you will be prompted to enter it.""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Make key optional
    parser.add_argument(
        "key",
        nargs="?",  # Makes the positional argument optional
        help="Unique identifier for the persona (e.g., tech_expert, friendly_interviewer)",
    )
    parser.add_argument("--name", help="Display name for the persona")
    parser.add_argument("--prompt", help="Main prompt/description")
    parser.add_argument("--entry-message", help="Entry message when joining (spoken)")
    parser.add_argument("--text-message", help="Text message to post in chat when joining")
    parser.add_argument("--speech-rate", type=float, help="Speaking rate (0.5-2.0)")
    parser.add_argument("--tts-params", help="JSON string of TTS parameters")
    parser.add_argument(
        "--blank", action="store_true", help="Create with minimal values"
    )
    parser.add_argument("--replicate-key", help="Override Replicate API key from .env")
    parser.add_argument("--utfs-key", help="Override UTFS API key from .env")
    parser.add_argument("--app-id", help="Override UTFS App ID from .env")
    parser.add_argument(
        "--non-interactive", action="store_true", help="Skip interactive prompts"
    )
    # Add new format options
    parser.add_argument(
        "--format", help="Persona README format: standard, minimal, or custom",
        choices=["standard", "minimal", "custom"],
        default="standard"
    )
    parser.add_argument(
        "--sections", help="Custom sections for README (comma-separated)",
        default="Characteristics,Voice,Metadata"
    )
    parser.add_argument(
        "--no-characteristics", action="store_true", 
        help="Don't include characteristics section"
    )
    parser.add_argument(
        "--no-voice", action="store_true", 
        help="Don't include voice section"
    )

    args = parser.parse_args()

    # Initialize PersonaManager
    persona_manager = PersonaManager()

    try:
        # If no key provided, prompt for it
        if not args.key:
            print("\n=== Persona Key Creation ===")
            print("Format: use_underscores_like_this")
            print("Examples:")
            print("  • tech_expert")
            print("  • friendly_interviewer")
            print("  • sales_specialist")

            while True:
                key = input("\n🔑 Persona key: ").strip().lower()
                if key:
                    if " " in key:
                        print("Please use underscores instead of spaces")
                        continue
                    if key in persona_manager.personas:
                        print(f"Warning: Persona '{key}' already exists.")
                        choice = input(
                            "Press Enter to overwrite or any key to choose another name > "
                        )
                        if choice.strip():
                            continue
                    args.key = key
                    break
                print("Key cannot be empty")

        if args.blank or args.non_interactive:
            persona_data = create_persona_structure(args.key)
        else:
            # System prompt
            print("\n=== System Prompt ===")
            print("This is the core of your persona's behavior.")
            print("Press Enter twice to finish.")
            print("\nCurrent default:")
            print("-" * 50)
            print(f"{DEFAULT_SYSTEM_PROMPT}")
            print("-" * 50)

            prompt_lines = []
            while True:
                line = input()
                if not line and prompt_lines and not prompt_lines[-1]:
                    break
                prompt_lines.append(line)
            prompt = (
                args.prompt or "\n".join(prompt_lines[:-1]) or DEFAULT_SYSTEM_PROMPT
            )

            # Name
            print("\n=== Display Name ===")
            default_name = args.key.replace("_", " ").title()
            name = (
                args.name
                or input(f"💭 Enter display name (default: {default_name}): ").strip()
            )
            if not name:
                name = default_name

            # Entry message
            print("\n=== Entry Message ===")
            print(f"Default: {DEFAULT_ENTRY_MESSAGE}")
            entry_message = (
                args.entry_message
                or input("💬 Enter message: ").strip()
                or DEFAULT_ENTRY_MESSAGE
            )

            # Text message
            print("\n=== Text Message ===")
            print(f"Default: {DEFAULT_TEXT_MESSAGE}")
            text_message = (
                args.text_message
                or input("💬 Enter text message: ").strip()
                or DEFAULT_TEXT_MESSAGE
            )

            # Characteristics
            print("\n=== Characteristics ===")
            print("Current defaults:")
            for char in PROMPTS_CHARACTERISTICS:
                print(f"  • {char}")
            print("\nEnter new characteristics (empty line to finish):")

            characteristics = []
            while True:
                char = input("✨ > ").strip()
                if not char:
                    break
                characteristics.append(char)
            if not characteristics:
                characteristics = PROMPTS_CHARACTERISTICS

            # Tone of voice
            print("\n=== Tone of Voice ===")
            print("Current defaults:")
            for tone in PROMPTS_VOICE_CHARACTERISTICS:
                print(f"  • {tone}")
            print("\nEnter new voice characteristics (empty line to finish):")

            tone_of_voice = []
            while True:
                tone = input("🗣️ > ").strip()
                if not tone:
                    break
                tone_of_voice.append(tone)
            if not tone_of_voice:
                tone_of_voice = PROMPTS_VOICE_CHARACTERISTICS

            # Skin tone
            print("\n=== Skin Tone ===")
            print("Current defaults:")
            for skin_tone in SKIN_TONES:
                print(f"  • {skin_tone}")
            print("\nEnter skin tone (empty for random):")

            skin_tone = input("👩‍🦰 > ").strip()

            # Gender selection
            print("\n=== Gender ===")
            print("Options: MALE, FEMALE, NON-BINARY")
            print("Press Enter for random selection")
            gender = input("🧑 > ").strip().upper()
            if gender and gender not in ["MALE", "FEMALE", "NON-BINARY"]:
                print("Invalid gender, using random selection")
                gender = None

            # Relevant links
            print("\n=== Relevant Links ===")
            print("Enter links one per line (empty line to finish)")
            relevant_links = []
            while True:
                link = input("🔗 > ").strip()
                if not link:
                    break
                relevant_links.append(link)
                
            # If format is custom, ask for sections unless --non-interactive
            if args.format == "custom" and not args.non_interactive:
                print("\n=== README Format ===")
                print("You can customize the sections in the README file.")
                print("Enter section names (comma-separated), or press Enter for default:")
                print("Default: Characteristics,Voice,Metadata")
                
                sections_input = input("> ").strip()
                if sections_input:
                    args.sections = sections_input
            
            # Create persona data structure
            persona_data = create_persona_structure(
                args.key,
                name=name,
                prompt=prompt,
                entry_message=entry_message,
                text_message=text_message,
                speech_rate=args.speech_rate,
                tts_params=args.tts_params,
                characteristics=characteristics,
                tone_of_voice=tone_of_voice,
                skin_tone=skin_tone,
                gender=gender,
                relevant_links=relevant_links,
            )
            
            # Set format preferences
            persona_data["format"] = {
                "style": args.format,
                "sections": args.sections.split(",") if args.sections else ["Characteristics", "Voice", "Metadata"],
                "include_characteristics": not args.no_characteristics,
                "include_voice": not args.no_voice
            }

        # Save the persona data
        persona_manager.personas[args.key] = persona_data
        if not persona_manager.save_persona(args.key, persona_data):
            logger.error(f"Failed to save persona data for {args.key}")
            return 1

        # Generate image if available
        replicate_key = args.replicate_key or REPLICATE_KEY
        utfs_key = args.utfs_key or UTFS_KEY
        app_id = args.app_id or APP_ID

        if all([replicate_key, utfs_key, app_id]):
            try:
                logger.info("Starting image generation...")
                generate_persona_image(args.key, replicate_key, utfs_key, app_id)
            except Exception as e:
                logger.warning(f"Image generation failed: {e}")
                logger.info(
                    "You can still use this persona, but no image will be displayed."
                )
        else:
            logger.info(
                "Image generation skipped - missing keys in .env file or overrides."
            )

        logger.success(f"Successfully created persona: {args.key}")
        print(f"\n✅ Persona '{args.key}' created successfully!")
        return 0

    except Exception as e:
        logger.error(f"Error creating persona: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(create_persona_cli()))
