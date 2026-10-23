# """Step 4: Voice Pipeline Integration (Gnani STT & TTS).

# Wraps the Step 3 agent with Gnani's speech models (gnani-vachana):
# - Normalizes text for speech (spoken numbers, explicit years in dates, currency).
# - Transcribes customer audio clips using Gnani STT (en-IN).
# - Synthesizes agent spoken replies using Gnani TTS (timbre-v2.5 / timbre-v3.0, Kaveri voice).
# """
# import os
# import re
# from pathlib import Path
# from typing import Dict, Tuple, Optional

# from .config import GNANI_API_KEY
# from .agent import SupportAgent


# def normalize_text_for_speech(text: str) -> str:
#     """Prepare text for clear text-to-speech pronunciation.

#     - Replaces currency symbols like ₹500 with '500 rupees'.
#     - Breaks long numeric order IDs (e.g. 89782837) into spaced digit groups.
#     - Ensures years in dates are explicit (e.g. 2026).
#     """
#     # 1. Currency normalization
#     normalized = re.sub(r"₹\s*(\d+)", r"\1 rupees", text)

#     # 2. Break 8-digit order IDs into spaced groups (e.g. 8978 2837)
#     normalized = re.sub(r"\b(\d{4})(\d{4})\b", r"\1 \2", normalized)

#     # 3. Format citations: strip raw [SECTION-ID] tags from spoken output
#     normalized = re.sub(r"Sources:\s*\[.*?\]", "", normalized, flags=re.IGNORECASE)

#     # 4. Clean extra whitespace
#     normalized = re.sub(r"\s+", " ", normalized).strip()
#     return normalized


# class VoiceHandler:
#     """Manages Gnani STT and TTS speech operations."""

#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or GNANI_API_KEY
#         self.has_gnani = False
#         self.stt_client = None
#         self.tts_client = None

#         if self.api_key:
#             os.environ["GNANI_API_KEY"] = self.api_key
#             try:
#                 from gnani.stt import GnaniSTTClient
#                 from gnani.tts import GnaniTTSClient
#                 self.stt_client = GnaniSTTClient()
#                 self.tts_client = GnaniTTSClient()
#                 self.has_gnani = True
#                 print("[Voice] Gnani STT and TTS clients initialized successfully.")
#             except ImportError:
#                 print("[Voice] Note: 'gnani-vachana' SDK not installed. Running in mock voice mode.")
#             except Exception as e:
#                 print(f"[Voice] Note: Could not initialize Gnani client ({e}). Running in mock mode.")
#         else:
#             print("[Voice] Note: GNANI_API_KEY not configured. Speech functions will use mock synthesis.")

#     def transcribe_audio(self, audio_path: str, language_code: str = "en-IN") -> str:
#         """Transcribe audio file into text using Gnani STT."""
#         if self.has_gnani and self.stt_client:
#             res = self.stt_client.transcribe(
#                 audio_path,
#                 language_code=language_code
#             )

#             print("RAW GNANI RESPONSE:", repr(res))
#             return str(res.get("transcript") or "").strip()
        
#         # Fallback simulation if running offline test
#         print(f"[Voice:STT] Transcribing {audio_path} (Simulation mode)")
#         return "Hello, I need some help with an order."

#     def synthesize_speech(
#         self,
#         text: str,
#         output_file: str,
#         voice: str = "Kaveri",
#         model: str = "timbre-v2.5",
#         language: str = "en-IN"
#     ) -> str:
#         """Synthesize text into speech audio using Gnani TTS."""
#         spoken_text = normalize_text_for_speech(text)
#         Path(output_file).parent.mkdir(parents=True, exist_ok=True)

#         if self.has_gnani and self.tts_client:
#             self.tts_client.synthesize(
#                 spoken_text,
#                 voice=voice,
#                 model=model,
#                 language=language,
#                 output_file=output_file
#             )
#             return output_file

#         # Fallback simulation: write empty / placeholder wav header
#         with open(output_file, "wb") as f:
#             # Minimal 44-byte standard PCM WAV header
#             f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
#         print(f"[Voice:TTS] Saved synthesized audio to {output_file} (Simulation)")
#         return output_file

#     def voice_turn(
#         self,
#         audio_path: str,
#         agent: SupportAgent,
#         output_audio_path: str = "reply.wav"
#     ) -> Tuple[str, str, str]:
#         """Perform a single voice turn: STT -> Agent -> TTS."""
#         heard = self.transcribe_audio(audio_path)
#         if not heard.strip():
#             reply = "Sorry, I didn't catch that. Could you please say it again?"
#         else:
#             reply = agent.respond(heard)

#         audio_out = self.synthesize_speech(reply, output_file=output_audio_path)
#         return heard, reply, audio_out


"""Step 4: Voice Pipeline Integration (Gnani STT & TTS).

Wraps the Step 3 agent with Gnani's speech models (gnani-vachana):
- Normalizes text for speech (spoken numbers, explicit years in dates, currency).
- Transcribes customer audio clips using Gnani STT (en-IN).
- Synthesizes agent spoken replies using Gnani TTS (timbre-v2.5 / timbre-v3.0, Kaveri voice).
"""
import os
import re
from pathlib import Path
from typing import Dict, Tuple, Optional

from .config import GNANI_API_KEY

REFERENCE_YEAR = 2026  # fixed reference date: 20 October 2026
from .agent import SupportAgent


def normalize_text_for_speech(text: str) -> str:
    """Prepare text for clear text-to-speech pronunciation.

    - Replaces currency symbols like ₹500 with '500 rupees'.
    - Breaks long numeric order IDs (e.g. 89782837) into spaced digit groups.
    - Ensures years in dates are explicit (e.g. 24 October -> 24 October 2026).
    - Removes markdown markers (**bold**, #) so they are not read aloud.
    """
    # 1. Currency normalization
    normalized = re.sub(r"₹\s*(\d+)", r"\1 rupees", text)

    # 2. Break 8-digit order IDs into spaced groups (e.g. 8978 2837)
    normalized = re.sub(r"\b(\d{4})(\d{4})\b", r"\1 \2", normalized)

    # 3. Format citations: strip raw [SECTION-ID] tags from spoken output
    normalized = re.sub(r"Sources:\s*\[.*?\]", "", normalized, flags=re.IGNORECASE)

    # 4. Plain text for the voice: drop markdown markers
    normalized = normalized.replace("**", "").replace("__", "")
    normalized = re.sub(r"^\s*[*#]+\s*", "", normalized, flags=re.M)

    # 5. Make the year explicit in dates such as "24 October" -> "24 October 2026"
    months = "January|February|March|April|May|June|July|August|September|October|November|December"
    normalized = re.sub(
        rf"\b(\d{{1,2}})(st|nd|rd|th)?\s+({months})\b(?!\s*,?\s*\d{{4}})",
        lambda m: f"{m.group(1)}{m.group(2) or ''} {m.group(3)} {REFERENCE_YEAR}",
        normalized,
    )

    # 6. Clean extra whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


class VoiceHandler:
    """Manages Gnani STT and TTS speech operations."""

    def __init__(self, api_key: Optional[str] = None, allow_mock: Optional[bool] = None):
        # Mock mode is only for offline unit tests (VOICEOPS_ALLOW_MOCK=1). It never counts as a Gnani result.
        if allow_mock is None:
            allow_mock = os.environ.get("VOICEOPS_ALLOW_MOCK") == "1"
        self.allow_mock = allow_mock
        self.api_key = api_key or GNANI_API_KEY
        self.has_gnani = False
        self.stt_client = None
        self.tts_client = None

        if self.api_key:
            os.environ["GNANI_API_KEY"] = self.api_key
            try:
                from gnani.stt import GnaniSTTClient
                from gnani.tts import GnaniTTSClient
                self.stt_client = GnaniSTTClient()
                self.tts_client = GnaniTTSClient()
                self.has_gnani = True
                print("[Voice] Gnani STT and TTS clients initialized successfully.")
            except ImportError:
                print("[Voice] Note: 'gnani-vachana' SDK not installed. Running in mock voice mode.")
            except Exception as e:
                print(f"[Voice] Note: Could not initialize Gnani client ({e}). Running in mock mode.")
        else:
            print("[Voice] Note: GNANI_API_KEY not configured.")

        if not self.has_gnani and not self.allow_mock:
            raise RuntimeError(
                "Gnani STT/TTS is not available. Set GNANI_API_KEY in .env and run `pip install gnani-vachana`. "
                "(For offline unit tests only, set VOICEOPS_ALLOW_MOCK=1.)"
            )

    def transcribe_audio(self, audio_path: str, language_code: str = "en-IN") -> str:
        """Transcribe audio file into text using Gnani STT."""
        if self.has_gnani and self.stt_client:
            res = self.stt_client.transcribe(audio_path, language_code=language_code)
            return res.get("transcript", "").strip()
        
        # Fallback simulation if running offline test
        print(f"[Voice:STT] Transcribing {audio_path} (Simulation mode)")
        return "Hello, I need some help with an order."

    def synthesize_speech(
        self,
        text: str,
        output_file: str,
        voice: str = "Kaveri",
        model: str = "timbre-v2.5",
        language: str = "en-IN"
    ) -> str:
        """Synthesize text into speech audio using Gnani TTS."""
        spoken_text = normalize_text_for_speech(text)
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        if self.has_gnani and self.tts_client:
            self.tts_client.synthesize(
                spoken_text,
                voice=voice,
                model=model,
                language=language,
                output_file=output_file
            )
            return output_file

        # Fallback simulation: write empty / placeholder wav header
        with open(output_file, "wb") as f:
            # Minimal 44-byte standard PCM WAV header
            f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        print(f"[Voice:TTS] Saved synthesized audio to {output_file} (Simulation)")
        return output_file

    def voice_turn(
        self,
        audio_path: str,
        agent: SupportAgent,
        output_audio_path: str = "reply.wav"
    ) -> Tuple[str, str, str]:
        """Perform a single voice turn: STT -> Agent -> TTS."""
        heard = self.transcribe_audio(audio_path)
        if not heard.strip():
            reply = "Sorry, I didn't catch that. Could you please say it again?"
        else:
            reply = agent.respond(heard)

        audio_out = self.synthesize_speech(reply, output_file=output_audio_path)
        return heard, reply, audio_out