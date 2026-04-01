# Voice Agent Extension

Enables **spoken mock interviews** for realistic verbal practice.

## Flow

1. **User speaks** → STT (Whisper / AssemblyAI / Deepgram)
2. **Transcript** → Orchestrator `/ask_question` → next question
3. **Question text** → TTS (ElevenLabs / OpenAI TTS / Google) → audio to user
4. **Memory & evaluation** use same flows as text mode

## Suggested Stack

| Component | Options |
|-----------|---------|
| STT | OpenAI Whisper, AssemblyAI, Deepgram |
| TTS | ElevenLabs, OpenAI TTS, Google Cloud TTS |
| Real-time | WebSockets or streaming for low-latency turns |

## Getting Started

1. Implement a thin adapter around your chosen STT/TTS APIs.
2. Call the Orchestrator’s `/ask_question` with user transcripts.
3. Convert the returned question text to speech and play it back.
4. Optionally add a simple web UI (e.g., Streamlit) with record/play buttons.
