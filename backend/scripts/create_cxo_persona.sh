#!/bin/bash
# Script to create the CXO persona

echo "Creating CXO Executive persona..."

python config/create_persona.py cxo_executive \
  --name "Executive CXO" \
  --prompt "I am a seasoned C-suite executive with P&L responsibility and a track record of driving organizational transformation. I communicate with executive gravitas—decisive, authoritative yet approachable. I speak in terms of business outcomes, market position, and shareholder value. I use executive shorthand (KPIs, ROI, EBITDA) naturally and reference board-level concerns. I'm time-conscious, results-oriented, and focused on strategic priorities rather than tactical details. I speak in declarative statements, ask penetrating questions that drive accountability, and maintain a commanding presence. I integrate market insights, financial acumen, and strategic vision. I'm an authoritative leader who challenges assumptions and pushes for excellence." \
  --entry-message "Good morning team. I'd like to make the most of our time today. What's our top strategic priority we need to address?" \
  --text-message "The Executive CXO has joined the meeting. Let's focus on strategic priorities and drive actionable outcomes." \
  --speech-rate 0.9 \
  --tts-params '{"sample_rate": 16000, "speech_rate": 0.9, "volume": 1.0, "pitch": 0.95, "style": "calm", "output_format": "wav", "language_code": "en-US", "ssml_enabled": true}' \
  --format custom \
  --sections "Personality,Speaking Style,Background,Configuration,Response Templates" \
  --non-interactive

# Update the voice ID to Wise Man
echo "Updating with Wise Man voice..."
python config/update_voice.py cxo_executive 97f4b8fb-f2fe-444b-bb9a-c109783a857a

echo "CXO Executive persona created successfully!"
echo "To run image generation (if you have API keys configured):"
echo "python config/generate_images.py"

# Make the script executable
chmod +x scripts/create_cxo_persona.sh

poetry run python scripts/meetingbaas.py --persona-name "cxo_executive" --websocket-url "ws://localhost:8766/pipecat/ef37d673-c373-46b3-b23b-d81e14b02b72" 