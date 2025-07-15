from faster_whisper import WhisperModel

# Modelni oldindan yuklab olish
model = WhisperModel("base", compute_type="int8")

async def transcribe_audio(audio_path: str) -> str:
    segments, info = model.transcribe(audio_path, beam_size=5)
    text = ""
    for segment in segments:
        text += segment.text + " "
    return text.strip()