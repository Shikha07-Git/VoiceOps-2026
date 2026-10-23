# import sys
# sys.path.insert(0, '.')
# from src.voice import VoiceHandler
# vh = VoiceHandler()
# print('Gnani active:', vh.has_gnani)

import sys
sys.path.insert(0, ".")

from src.voice import VoiceHandler

vh = VoiceHandler()
print("Gnani active:", vh.has_gnani)

if vh.has_gnani:
    try:
        audio_path = "sample_audio/customer_query_01.wav"
        transcript = vh.transcribe_audio(audio_path)
        print("Transcription:", repr(transcript))
    except Exception as e:
        print("STT ERROR:", type(e).__name__, str(e))