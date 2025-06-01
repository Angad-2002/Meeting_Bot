import asyncio
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import aiohttp
import markdown
from dotenv import load_dotenv
from loguru import logger

from config.prompts import (
    DEFAULT_CHARACTERISTICS,
    DEFAULT_ENTRY_MESSAGE,
    DEFAULT_VOICE_CHARACTERISTICS,
    PERSONA_INTERACTION_INSTRUCTIONS,
)

# Load environment variables from .env file
load_dotenv()


class PersonaManager:
    def __init__(self, personas_dir: Optional[Path] = None):
        """Initialize PersonaManager with optional custom personas directory"""
        self.personas_dir = personas_dir or Path(__file__).parent / "personas"
        self.md = markdown.Markdown(extensions=["meta"])
        self.personas = self.load_personas()

    def parse_readme(self, content: str) -> Dict:
        """Parse README.md content to extract persona information with flexible format support"""
        # Reset markdown instance for new content
        self.md.reset()
        html = self.md.convert(content)

        # Split content by sections (supports both ## and ## headers)
        sections = {}
        current_section = "main"
        lines = content.split("\n")
        
        for line in lines:
            if line.startswith("# "):
                # This is the title
                sections["title"] = line.replace("# ", "").strip()
                continue
            elif line.startswith("## "):
                # This is a section header
                current_section = line.replace("## ", "").strip().lower()
                sections[current_section] = []
                continue
            
            # Add line to current section
            if current_section not in sections:
                sections[current_section] = []
            sections[current_section].append(line)
        
        # Process sections into a cohesive structure
        name = sections.get("title", "Unnamed Persona")
        
        # Get prompt (main content after title, before first section)
        prompt = "\n".join(sections.get("main", [])).strip()
        
        # Extract metadata from any section that might contain it
        metadata = {
            "image": "",
            "entry_message": DEFAULT_ENTRY_MESSAGE,
            "cartesia_voice_id": "",
            "gender": "",
            "relevant_links": [],
        }
        
        # YAML-like nested dict for TTS parameters
        tts_params = {}
        inside_tts_params = False
        tts_indentation = 0

        # Look for metadata in a dedicated metadata section first
        if "metadata" in sections:
            for line in sections["metadata"]:
                if line.strip() and line.startswith("- "):
                    try:
                        key_value = line[2:].split(": ", 1)
                        if len(key_value) == 2:
                            key, value = key_value
                            if key == "relevant_links":
                                # Split by spaces instead of commas for URLs
                                metadata[key] = [
                                    url for url in value.strip().split() if url
                                ]
                            else:
                                metadata[key] = value.strip()
                    except ValueError:
                        continue
        
        # Also check for alternative section names that might contain metadata
        alternative_metadata_sections = ["info", "details", "configuration", "settings", "properties"]
        for section_name in alternative_metadata_sections:
            if section_name in sections:
                for i, line in enumerate(sections[section_name]):
                    if line.strip() and (line.startswith("- ") or ":" in line):
                        try:
                            # Process tts_params as a nested structure
                            # Check if this is the start of tts_params section
                            if "tts_params:" in line:
                                inside_tts_params = True
                                # Get the indentation level of the tts_params line
                                tts_indentation = len(line) - len(line.lstrip())
                                continue
                                
                            # If we're inside tts_params section, process nested params
                            if inside_tts_params:
                                # Check indentation to determine if we're still in tts_params
                                current_indent = len(line) - len(line.lstrip())
                                if current_indent <= tts_indentation:
                                    inside_tts_params = False  # Back to parent level
                                
                                # Process a tts_param if still in the section
                                if inside_tts_params and line.strip():
                                    # Strip any leading dash
                                    param_line = line.strip()
                                    if param_line.startswith("- "):
                                        param_line = param_line[2:]
                                        
                                    # Extract key-value
                                    if ":" in param_line:
                                        param_key, param_value = param_line.split(":", 1)
                                        param_key = param_key.strip()
                                        param_value = param_value.strip()
                                        
                                        # Convert value types appropriately
                                        if param_value.lower() in ('true', 'yes'):
                                            param_value = True
                                        elif param_value.lower() in ('false', 'no'):
                                            param_value = False
                                        elif param_value.replace('.', '', 1).isdigit():
                                            # Convert to float or int
                                            if '.' in param_value:
                                                param_value = float(param_value)
                                            else:
                                                param_value = int(param_value)
                                                
                                        tts_params[param_key] = param_value
                                continue

                            # Handle different formats like "- key: value" or just "key: value"
                            if line.startswith("- "):
                                key_value = line[2:].split(": ", 1)
                            else:
                                key_value = line.split(": ", 1)
                                
                            if len(key_value) == 2:
                                key, value = key_value
                                key = key.strip().lower()
                                
                                # Map common alternative keys to our standard keys
                                key_mapping = {
                                    "picture": "image", 
                                    "avatar": "image",
                                    "greeting": "entry_message",
                                    "message": "entry_message",
                                    "voice": "cartesia_voice_id",
                                    "voice_id": "cartesia_voice_id",
                                    "links": "relevant_links",
                                    "references": "relevant_links",
                                    "urls": "relevant_links"
                                }
                                
                                if key in key_mapping:
                                    key = key_mapping[key]
                                    
                                if key in metadata:
                                    if key == "relevant_links":
                                        # Handle different formats for links
                                        if "," in value:
                                            metadata[key] = [url.strip() for url in value.strip().split(",") if url.strip()]
                                        else:
                                            metadata[key] = [url for url in value.strip().split() if url]
                                    else:
                                        metadata[key] = value.strip()
                        except ValueError:
                            continue
        
        # Extract any characteristics found
        characteristics = []
        tone_characteristics = []
        
        # Look for characteristics in different possible sections
        character_sections = ["characteristics", "traits", "personality", "character"]
        voice_sections = ["voice", "tone", "speech", "speaking style"]
        
        for section_type, section_names, target_list in [
            ("character", character_sections, characteristics),
            ("voice", voice_sections, tone_characteristics)
        ]:
            for section_name in section_names:
                if section_name in sections:
                    for line in sections[section_name]:
                        if line.strip() and line.startswith("- "):
                            trait = line[2:].strip()
                            if trait and trait not in target_list:
                                target_list.append(trait)
        
        # Build the final persona object
        persona = {
            "name": name,
            "prompt": prompt,
            "image": metadata.get("image", ""),
            "entry_message": metadata.get("entry_message", DEFAULT_ENTRY_MESSAGE),
            "cartesia_voice_id": metadata.get("cartesia_voice_id", ""),
            "gender": metadata.get("gender", ""),
            "relevant_links": metadata.get("relevant_links", []),
        }
        
        # Add tts_params if found
        if tts_params:
            persona["tts_params"] = tts_params
        
        # Add characteristics and tone if found
        if characteristics:
            persona["characteristics"] = characteristics
        if tone_characteristics:
            persona["tone_of_voice"] = tone_characteristics
            
        return persona

    def load_additional_content(self, persona_dir: Path) -> str:
        """Load additional markdown content from persona directory"""
        additional_content = []

        # Skip these files
        skip_files = {"README.md", ".DS_Store"}

        try:
            for file_path in persona_dir.glob("*.md"):
                if file_path.name not in skip_files:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            additional_content.append(
                                f"# Content from {file_path.name}\n\n{content}"
                            )
        except Exception as e:
            logger.error(f"Error loading additional content from {persona_dir}: {e}")

        return "\n\n".join(additional_content)

    def load_personas(self) -> Dict:
        """Load personas from directory structure"""
        personas = {}
        try:
            for persona_dir in self.personas_dir.iterdir():
                if not persona_dir.is_dir():
                    continue

                readme_file = persona_dir / "README.md"
                if not readme_file.exists():
                    logger.warning(
                        f"Skipping persona without README: {persona_dir.name}"
                    )
                    continue

                with open(readme_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    persona_data = self.parse_readme(content)

                    # Load additional content
                    additional_content = self.load_additional_content(persona_dir)
                    if additional_content:
                        persona_data["additional_content"] = additional_content

                    personas[persona_dir.name] = persona_data

            return personas
        except Exception as e:
            logger.error(f"Failed to load personas: {e}")
            raise

    def save_persona(self, key: str, persona: Dict) -> bool:
        """Save a single persona's data while preserving existing format if possible"""
        try:
            persona_dir = self.personas_dir / key
            persona_dir.mkdir(exist_ok=True)
            
            # Initialize with default format if no existing file
            existing_format = {
                "has_characteristics": True,
                "has_voice": True,
                "metadata_section_name": "Metadata",
                "characteristics_section_name": "Characteristics",
                "voice_section_name": "Voice",
                "metadata_format": "- key: value"
            }
            
            # Read existing README if it exists to preserve format and metadata
            readme_file = persona_dir / "README.md"
            existing_metadata = {}
            
            if readme_file.exists():
                with open(readme_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    # Detect if it has characteristics and voice sections
                    existing_format["has_characteristics"] = "## Characteristics" in content or any(
                        f"## {name}" in content for name in ["Traits", "Personality", "Character"]
                    )
                    existing_format["has_voice"] = "## Voice" in content or any(
                        f"## {name}" in content for name in ["Tone", "Speech", "Speaking Style"]
                    )
                    
                    # Detect metadata section name
                    metadata_matches = [
                        section for section in ["Metadata", "Info", "Details", "Configuration", "Settings", "Properties"]
                        if f"## {section}" in content
                    ]
                    if metadata_matches:
                        existing_format["metadata_section_name"] = metadata_matches[0]
                        
                    # Detect characteristics section name
                    char_matches = [
                        section for section in ["Characteristics", "Traits", "Personality", "Character"]
                        if f"## {section}" in content
                    ]
                    if char_matches:
                        existing_format["characteristics_section_name"] = char_matches[0]
                        
                    # Detect voice section name
                    voice_matches = [
                        section for section in ["Voice", "Tone", "Speech", "Speaking Style"]
                        if f"## {section}" in content
                    ]
                    if voice_matches:
                        existing_format["voice_section_name"] = voice_matches[0]
                    
                    # Detect metadata format (dash or no dash)
                    if "- image:" in content:
                        existing_format["metadata_format"] = "- key: value"
                    elif "image:" in content:
                        existing_format["metadata_format"] = "key: value"
                        
                    # Get existing persona data
                    existing_persona = self.parse_readme(content)
                    # Preserve all existing metadata fields
                    existing_metadata = {
                        "image": existing_persona.get("image", ""),
                        "entry_message": existing_persona.get(
                            "entry_message", DEFAULT_ENTRY_MESSAGE
                        ),
                        "cartesia_voice_id": existing_persona.get(
                            "cartesia_voice_id", ""
                        ),
                        "gender": existing_persona.get("gender", ""),
                        "relevant_links": existing_persona.get("relevant_links", []),
                    }

            # Merge existing metadata with new data, preferring new data when available
            metadata = {
                "image": persona.get("image", existing_metadata.get("image", "")),
                "entry_message": persona.get(
                    "entry_message",
                    existing_metadata.get("entry_message", DEFAULT_ENTRY_MESSAGE),
                ),
                "cartesia_voice_id": persona.get(
                    "cartesia_voice_id", existing_metadata.get("cartesia_voice_id", "")
                ),
                "gender": persona.get(
                    "gender",
                    existing_metadata.get("gender", random.choice(["MALE", "FEMALE"])),
                ),
                "relevant_links": persona.get(
                    "relevant_links", existing_metadata.get("relevant_links", [])
                ),
            }

            # Get characteristics and voice traits
            characteristics = persona.get("characteristics", DEFAULT_CHARACTERISTICS)
            voice_traits = persona.get("tone_of_voice", DEFAULT_VOICE_CHARACTERISTICS)
            
            # Format characteristics and voice characteristics as bullet points
            formatted_characteristics = "\n".join(f"- {char}" for char in characteristics)
            formatted_voice_traits = "\n".join(f"- {trait}" for trait in voice_traits)
            
            # Format metadata according to detected format
            if existing_format["metadata_format"] == "- key: value":
                formatted_metadata = "\n".join([
                    f"- image: {metadata['image']}",
                    f"- entry_message: {metadata['entry_message']}",
                    f"- cartesia_voice_id: {metadata['cartesia_voice_id']}",
                    f"- gender: {metadata['gender']}",
                    f"- relevant_links: {' '.join(metadata['relevant_links'])}"
                ])
            else:
                formatted_metadata = "\n".join([
                    f"image: {metadata['image']}",
                    f"entry_message: {metadata['entry_message']}",
                    f"cartesia_voice_id: {metadata['cartesia_voice_id']}",
                    f"gender: {metadata['gender']}",
                    f"relevant_links: {' '.join(metadata['relevant_links'])}"
                ])
            
            # Build the README content preserving format
            readme_content = f"# {persona['name']}\n\n{persona['prompt']}"
            
            # Add characteristics section if it exists in original
            if existing_format["has_characteristics"]:
                readme_content += f"\n\n## {existing_format['characteristics_section_name']}\n{formatted_characteristics}"
            
            # Add voice section if it exists in original
            if existing_format["has_voice"]:
                voice_intro = f"{persona['name']} speaks with:" if "speaks with" not in formatted_voice_traits else ""
                if voice_intro:
                    readme_content += f"\n\n## {existing_format['voice_section_name']}\n{voice_intro}\n{formatted_voice_traits}"
                else:
                    readme_content += f"\n\n## {existing_format['voice_section_name']}\n{formatted_voice_traits}"
            
            # Add metadata section
            readme_content += f"\n\n## {existing_format['metadata_section_name']}\n{formatted_metadata}\n"

            with open(readme_file, "w", encoding="utf-8") as f:
                f.write(readme_content)

            return True
        except Exception as e:
            logger.error(f"Failed to save persona {key}: {e}")
            return False

    def save_personas(self) -> bool:
        """Save all personas to their respective README files"""
        success = True
        for key, persona in self.personas.items():
            if not self.save_persona(key, persona):
                success = False
                logger.error(f"Failed to save persona {key}")
        return success

    def list_personas(self) -> List[str]:
        """Returns a sorted list of available persona names"""
        return sorted(self.personas.keys())

    def get_persona(self, name: Optional[str] = None) -> Dict:
        """Get a persona by name or return a random one"""
        if name:
            # Convert to folder name format
            folder_name = name.lower().replace(" ", "_")

            # First try exact folder match
            if folder_name in self.personas:
                persona = self.personas[folder_name].copy()
                logger.info(f"Using specified persona folder: {folder_name}")
            else:
                # Try to find the closest match among folder names
                words = set(name.lower().split())
                closest_match = None
                max_overlap = 0

                for persona_key in self.personas.keys():
                    persona_words = set(persona_key.split("_"))
                    overlap = len(words & persona_words)
                    if overlap > max_overlap:
                        max_overlap = overlap
                        closest_match = persona_key

                if closest_match and max_overlap >= 1:  # At least 1 word matches
                    persona = self.personas[closest_match].copy()
                    logger.warning(
                        f"Using closest matching persona folder: {closest_match} (from: {name})"
                    )
                else:
                    raise KeyError(
                        f"Persona '{name}' not found. Valid options: {', '.join(self.personas.keys())}"
                    )
        else:
            persona = random.choice(list(self.personas.values())).copy()
            logger.info(f"Randomly selected persona: {persona['name']}")

        # Only set default image if needed for display purposes
        if not persona.get("image"):
            persona["image"] = ""  # Empty string instead of default URL

        persona["prompt"] = persona["prompt"] + PERSONA_INTERACTION_INSTRUCTIONS
        # Add the path to the persona's directory using the normalized name
        persona_key = (
            name.lower().replace(" ", "_")
            if name
            else persona["name"].lower().replace(" ", "_")
        )
        persona["path"] = os.path.join(self.personas_dir, persona_key)
        return persona

    def get_persona_by_name(self, name: str) -> Dict:
        """Get a specific persona by display name"""
        for persona in self.personas.values():
            if persona["name"] == name:
                return persona.copy()
        raise KeyError(
            f"Persona '{name}' not found. Valid options: {', '.join(p['name'] for p in self.personas.values())}"
        )

    def update_persona_image(self, key: str, image_path: Union[str, Path]) -> bool:
        """Update image path/URL for a specific persona"""
        if key in self.personas:
            self.personas[key]["image"] = str(image_path)
            return self.save_persona(key, self.personas[key])
        logger.error(f"Persona key '{key}' not found")
        return False

    def get_image_urls(self) -> Dict[str, str]:
        """Get mapping of persona keys to their image URLs"""
        return {key: persona.get("image", "") for key, persona in self.personas.items()}

    def needs_image_upload(self, key: str, domain: str = "uploadthing.com") -> bool:
        """Check if a persona needs image upload"""
        if key not in self.personas:
            return False
        current_url = self.personas[key].get("image", "")
        return not (current_url and domain in current_url)


# Create global instance for easy access
persona_manager = PersonaManager()
