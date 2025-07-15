from faster_whisper import WhisperModel

# Modelni bir marta yuklab olamiz
model = WhisperModel("medium", device="cpu", compute_type="int8")

async def transcribe_audio(audio_path):
    try:
        segments, _ = model.transcribe(audio_path, beam_size=5)
        text = ""
        for segment in segments:
            text += segment.text + " "
        return text.strip()
    except Exception as e:
        return f"❌ Xatolik yuz berdi: {str(e)}"
