#!/bin/bash
# This script demonstrates how to create a persona with a custom format

# Basic usage with standard format
echo "Creating a standard persona..."
python config/create_persona.py coding_guru --name "Coding Guru" --prompt "You are a wise and experienced coding mentor." --entry-message "Ready to debug some code?" --non-interactive

# Create a persona with minimal format (no characteristics or voice sections)
echo "Creating a minimal persona..."
python config/create_persona.py minimal_bot --name "Minimal Bot" --prompt "A simple bot with minimal configuration." --entry-message "Hi, I'm minimal." --non-interactive --format minimal --no-characteristics --no-voice

# Create a persona with custom sections
echo "Creating a custom persona..."
python config/create_persona.py custom_persona --name "Custom Persona" --prompt "A persona with completely custom sections." --entry-message "Hello from a custom format!" --non-interactive --format custom --sections "Abilities,Personality,Background,Settings"

echo "Done! Check the config/personas directory to see the created personas." 