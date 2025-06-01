# Personas

This directory contains the persona definitions for the Speaking Meeting Bot. Each persona is defined in its own subdirectory with a README.md file and optionally additional content files.

## Creating a Persona

You can create a new persona using the persona creation tool:

```bash
python config/create_persona.py my_persona_name
```

This will guide you through an interactive process to create your persona. You can also use command-line parameters for non-interactive creation:

```bash
python config/create_persona.py my_persona_name --name "My Persona" --prompt "Description..." --entry-message "Hello!" --non-interactive
```

## Persona README Format

Personas can be defined with flexible README formats. The system now supports three primary format styles:

### 1. Standard Format (Default)

```markdown
# Persona Name

Persona description goes here...

## Characteristics
- Trait 1
- Trait 2
- Trait 3

## Voice
Persona Name speaks with:
- Voice trait 1
- Voice trait 2

## Metadata
- image: https://example.com/image.png
- entry_message: Hello, I'm a persona!
- cartesia_voice_id: voice-id-here
- gender: MALE
- relevant_links: https://link1.com https://link2.com
```

### 2. Minimal Format

```markdown
# Persona Name

Persona description goes here...

## Metadata
- image: https://example.com/image.png
- entry_message: Hello, I'm a minimal persona!
- cartesia_voice_id: voice-id-here
- gender: FEMALE
- relevant_links: 
```

### 3. Custom Format

You can use custom section names and organization:

```markdown
# Persona Name

Persona description goes here...

## Personality
- Trait 1
- Trait 2

## Speech Patterns
- Voice trait 1
- Voice trait 2

## Background
Additional information about the persona...

## Configuration
- image: https://example.com/image.png
- entry_message: Hello from a custom format!
- cartesia_voice_id: voice-id-here
- gender: NON-BINARY
- relevant_links: https://link1.com https://link2.com
```

## Flexible Section Names

The system recognizes these alternative section names:

### For Characteristics
- Characteristics
- Traits
- Personality
- Character

### For Voice
- Voice
- Tone
- Speech
- Speaking Style

### For Metadata
- Metadata
- Info
- Details
- Configuration
- Settings
- Properties

## Format Specification via Command Line

When creating a persona, you can specify the format using these options:

```bash
# Standard format
python config/create_persona.py standard_persona --format standard

# Minimal format (no characteristics or voice sections)
python config/create_persona.py minimal_persona --format minimal

# Custom format with specified sections
python config/create_persona.py custom_persona --format custom --sections "Abilities,Personality,Background,Settings"

# Exclude specific sections
python config/create_persona.py no_voice_persona --no-voice
python config/create_persona.py bare_persona --no-characteristics --no-voice
```

## Key/Value Format in Metadata

Metadata can be specified with or without dashes:

```markdown
# With dashes
- image: https://example.com/image.png
- entry_message: Hello!

# Without dashes
image: https://example.com/image.png
entry_message: Hello!
```

## Alternative Key Names

The system recognizes these alternative key names in metadata:

- `image`, `picture`, `avatar` → image URL
- `entry_message`, `greeting`, `message` → entry message text
- `cartesia_voice_id`, `voice`, `voice_id` → voice ID
- `relevant_links`, `links`, `references`, `urls` → relevant links

## Sample Script

A sample script for creating personas with different formats is provided in `scripts/create_custom_persona.sh`. 