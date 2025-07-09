# chefu

**30 seconds → voice‑interactive recipe**.  
Speak to advance; never touch a screen while cooking.

## Quick Start

```bash
git clone https://github.com/your‑org/chefbud‑voice.git
cd chefbud‑voice
cp .env.example .env           # add your OpenAI key
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
