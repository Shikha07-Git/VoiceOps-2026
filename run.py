# #!/usr/bin/env python3
# """Submission entrypoint for VoiceOps 2026.

# Accepts a folder of customer audio files, runs the ZentroMart support agent on each,
# and saves the replies (both text transcript and synthesized audio) alongside the
# retrieved document chunk IDs.

# Usage:
#     python run.py --input_dir path/to/audio/ --output_dir path/to/output/
# """
# import argparse
# import json
# import os
# import sys
# from pathlib import Path

# # Ensure project root is in sys.path
# PROJECT_ROOT = Path(__file__).resolve().parent
# sys.path.insert(0, str(PROJECT_ROOT))

# # Fix Windows stdout encoding for Unicode
# if hasattr(sys.stdout, "reconfigure"):
#     sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# from src.agent import SupportAgent
# from src.voice import VoiceHandler


# def process_audio_folder(input_dir: str, output_dir: str):
#     """Batch process audio files through the voice agent pipeline."""
#     in_path = Path(input_dir)
#     out_path = Path(output_dir)
#     out_path.mkdir(parents=True, exist_ok=True)

#     if not in_path.exists():
#         print(f"Error: Input directory '{input_dir}' does not exist.", file=sys.stderr)
#         sys.exit(1)

#     audio_extensions = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
#     audio_files = sorted([f for f in in_path.iterdir() if f.suffix.lower() in audio_extensions])

#     if not audio_files:
#         print(f"No audio files found in '{input_dir}'. Supported formats: {audio_extensions}")
#         return

#     print(f"=== ZentroMart VoiceOps: Processing {len(audio_files)} audio turn(s) ===")
#     voice_handler = VoiceHandler()
#     agent = SupportAgent(conversation_id="batch_eval")

#     summary_records = []

#     for idx, audio_file in enumerate(audio_files, 1):
#         base_name = audio_file.stem
#         out_audio_file = out_path / f"{base_name}_reply.wav"
#         out_json_file = out_path / f"{base_name}_result.json"

#         print(f"[{idx}/{len(audio_files)}] Processing: {audio_file.name}...", flush=True)

#         heard, reply, audio_saved = voice_handler.voice_turn(
#             str(audio_file),
#             agent,
#             output_audio_path=str(out_audio_file)
#         )

#         record = {
#             "input_audio": audio_file.name,
#             "transcription": heard,
#             "agent_reply": reply,
#             "output_audio": out_audio_file.name,
#             "order_id": agent.order_id,
#             "verified": agent.verified,
#             "ticket_id": agent.last_ticket_id
#         }

#         with open(out_json_file, "w", encoding="utf-8") as f:
#             json.dump(record, f, indent=2, ensure_ascii=False)

#         summary_records.append(record)
#         print(f"  Heard: \"{heard}\"")
#         print(f"  Reply: \"{reply[:100]}...\"")
#         print(f"  Saved -> {out_audio_file.name} & {out_json_file.name}\n")

#     summary_file = out_path / "batch_summary.json"
#     with open(summary_file, "w", encoding="utf-8") as f:
#         json.dump({"total_processed": len(audio_files), "records": summary_records}, f, indent=2, ensure_ascii=False)

#     print(f"=== Batch processing completed! Summary saved to {summary_file} ===")


# def main():
#     parser = argparse.ArgumentParser(description="ZentroMart VoiceOps 2026 Batch Runner")
#     parser.add_argument("--input_dir", type=str, default="sample_audio", help="Folder containing customer audio clips (.wav)")
#     parser.add_argument("--output_dir", type=str, default="sample_outputs", help="Folder to save output speech and text results")
#     args = parser.parse_args()

#     process_audio_folder(args.input_dir, args.output_dir)


# if __name__ == "__main__":
#     main()


#!/usr/bin/env python3
"""Submission entrypoint for VoiceOps 2026.

Accepts a folder of customer audio files, runs the ZentroMart support agent on each,
and saves the replies (both text transcript and synthesized audio) alongside the
retrieved document chunk IDs.

Usage:
    python run.py --input_dir path/to/audio/ --output_dir path/to/output/
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows stdout encoding for Unicode
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.agent import SupportAgent
from src.voice import VoiceHandler


def process_audio_folder(input_dir: str, output_dir: str, shared_session: bool = False):
    """Batch process audio files through the voice agent pipeline."""
    in_path = Path(input_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    audio_extensions = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
    audio_files = sorted([f for f in in_path.iterdir() if f.suffix.lower() in audio_extensions])

    if not audio_files:
        print(f"No audio files found in '{input_dir}'. Supported formats: {audio_extensions}")
        return

    print(f"=== ZentroMart VoiceOps: Processing {len(audio_files)} audio turn(s) ===")
    voice_handler = VoiceHandler()  # raises a clear error if Gnani is not configured
    shared_agent = SupportAgent(conversation_id="batch_eval") if shared_session else None

    summary_records = []

    for idx, audio_file in enumerate(audio_files, 1):
        base_name = audio_file.stem
        out_audio_file = out_path / f"{base_name}_reply.wav"
        out_json_file = out_path / f"{base_name}_result.json"

        print(f"[{idx}/{len(audio_files)}] Processing: {audio_file.name}...", flush=True)

        # Each audio file is an independent customer turn unless --shared_session is given
        agent = shared_agent or SupportAgent(conversation_id=base_name)
        error = None
        try:
            heard, reply, audio_saved = voice_handler.voice_turn(
                str(audio_file), agent, output_audio_path=str(out_audio_file)
            )
        except Exception as e:  # one bad file must never stop the batch
            error = f"{type(e).__name__}: {e}"
            heard = ""
            reply = "Sorry, I didn't catch that. Could you please say it again?"
            try:
                voice_handler.synthesize_speech(reply, output_file=str(out_audio_file))
            except Exception as e2:
                error += f" | TTS failed: {e2}"

        record = {
            "input_audio": audio_file.name,
            "transcription": heard,
            "agent_reply": reply,
            "output_audio": out_audio_file.name,
            "retrieved_chunks": agent.last_chunks,
            "cited_sections": agent.last_sources,
            "order_id": agent.order_id,
            "verified": agent.verified,
            "ticket_id": agent.last_ticket_id,
        }
        if error:
            record["error"] = error

        with open(out_json_file, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        summary_records.append(record)
        print(f"  Heard: \"{heard}\"")
        print(f"  Reply: \"{reply[:100]}...\"")
        print(f"  Saved -> {out_audio_file.name} & {out_json_file.name}\n")

    summary_file = out_path / "batch_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({"total_processed": len(audio_files), "records": summary_records}, f, indent=2, ensure_ascii=False)

    print(f"=== Batch processing completed! Summary saved to {summary_file} ===")


def main():
    parser = argparse.ArgumentParser(description="ZentroMart VoiceOps 2026 Batch Runner")
    parser.add_argument("--input_dir", type=str, default="sample_audio", help="Folder containing customer audio clips (.wav)")
    parser.add_argument("--output_dir", type=str, default="sample_outputs", help="Folder to save output speech and text results")
    parser.add_argument("--shared_session", action="store_true",
                        help="Treat all files as one conversation (default: each file is independent)")
    args = parser.parse_args()

    process_audio_folder(args.input_dir, args.output_dir, args.shared_session)


if __name__ == "__main__":
    main()