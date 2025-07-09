# ChefBud Voice 🍳

**Voice-interactive cooking assistant that responds to speech commands.**  
Cook hands-free - just speak to navigate through recipes without touching your device.

## ✨ Features

- 🎤 **Voice Navigation**: Speak to advance through recipe steps
- 🏃‍♂️ **Fast Setup**: From clone to cooking in 30 seconds
- 🧠 **Smart Understanding**: GPT-4o powered speech recognition
- 🔊 **Instant Audio**: Browser-native text-to-speech with zero latency
- 📱 **Progressive Web App**: Works on any device with a browser

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key

### Setup
```bash
# Clone and navigate
git clone https://github.com/your-org/chefbud-voice.git
cd chefbud-voice

# Create conda environment
conda create -n chefu python=3.11 -y
conda activate chefu

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Add your OpenAI API key

# Start the server
uvicorn backend.app.main:app --reload
```

### Usage
1. Open http://localhost:8000 in your browser
2. Allow microphone access when prompted
3. Start speaking to interact with recipes!

## 🛠 Tech Stack

- **Backend**: FastAPI + WebSocket streaming
- **AI**: GPT-4o Realtime API for speech recognition
- **Audio**: Browser SpeechSynthesis API (zero backend latency)
- **Frontend**: Progressive Web App with offline support
- **Architecture**: Clean domain-driven design for easy scaling

## 📖 Development

```bash
# Activate environment
conda activate chefu

# Run with auto-reload
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest backend/tests/
```

## 🐳 Docker

```bash
docker build -t chefbud-voice .
docker run -p 8000:8000 chefbud-voice
```

---

*Built for hands-free cooking experiences. See `docs/` for architecture details and sprint planning.*