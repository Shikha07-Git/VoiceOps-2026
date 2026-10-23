import os
import wave
import struct
import math

audio_dir = "sample_audio"
os.makedirs(audio_dir, exist_ok=True)

# Generate simple sine wave tones as valid PCM WAV files for batch pipeline testing
def create_tone(filename, duration_sec=1.5, freq=440.0, rate=16000):
    filepath = os.path.join(audio_dir, filename)
    num_samples = int(duration_sec * rate)
    with wave.open(filepath, 'w') as wav:
        wav.setnchannels(1)        # Mono
        wav.setsampwidth(2)        # 16-bit
        wav.setframerate(rate)     # 16kHz
        for i in range(num_samples):
            value = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * freq * (i / rate)))
            data = struct.pack('<h', value)
            wav.writeframesraw(data)
    print(f"Created sample audio: {filepath}")

create_tone("customer_query_01.wav", duration_sec=2.0, freq=440.0)
create_tone("customer_query_02.wav", duration_sec=2.0, freq=554.0)
