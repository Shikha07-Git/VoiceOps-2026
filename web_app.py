# #!/usr/bin/env python3
# """Interactive Web Dashboard for ZentroMart VoiceOps 2026.
 
# Provides a modern browser UI to test the VoiceOps agent:
# - Record live audio via microphone or upload .wav files.
# - Visual chat interface with audio playback of agent's voice replies.
# - Agent Brain Inspector: shows caller verification badge, order state,
#   retrieved [SECTION-ID] policy chunks, and escalation tickets.
# - Zero extra dependencies (uses Python standard library http.server).
 
# Usage:
#     python web_app.py
#     Open http://localhost:8080 in your web browser.
# """
# import http.server
# import json
# import os
# import sys
# import urllib.parse
# from pathlib import Path
 
# # Add project root to sys.path
# PROJECT_ROOT = Path(__file__).resolve().parent
# sys.path.insert(0, str(PROJECT_ROOT))
 
# # Ensure UTF-8
# if hasattr(sys.stdout, "reconfigure"):
#     sys.stdout.reconfigure(encoding="utf-8", errors="replace")
 
# from src.agent import SupportAgent
# from src.voice import VoiceHandler, normalize_text_for_speech
 
# PORT = 8080
# active_agent = SupportAgent(conversation_id="web_session")
# voice_handler = VoiceHandler(allow_mock=True)  # UI stays usable without a key; the console warns when Gnani is off
 
# HTML_PAGE = """<!DOCTYPE html>
# <html lang="en">
# <head>
#   <meta charset="UTF-8">
#   <meta name="viewport" content="width=device-width, initial-scale=1.0">
#   <title>ZentroMart VoiceOps 2026 — AI Voice Support Agent</title>
 
#   <style>
#     :root {
#       --bg: #0b0f19;
#       --card-bg: #111827;
#       --border: #1f2937;
#       --accent: #3b82f6;
#       --accent-hover: #2563eb;
#       --success: #10b981;
#       --warning: #f59e0b;
#       --danger: #ef4444;
#       --text: #f3f4f6;
#       --text-muted: #9ca3af;
#     }
#     * { box-sizing: border-box; margin: 0; padding: 0; }
#     body {
#       font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif;
#       background-color: var(--bg);
#       color: var(--text);
#       display: flex;
#       flex-direction: column;
#       height: 100vh;
#       overflow: hidden;
#     }
#     header {
#       background: #0f172a;
#       border-bottom: 1px solid var(--border);
#       padding: 14px 24px;
#       display: flex;
#       justify-content: space-between;
#       align-items: center;
#     }
#     .brand {
#       display: flex;
#       align-items: center;
#       gap: 12px;
#     }
#     .brand-logo {
#       background: linear-gradient(135deg, #3b82f6, #8b5cf6);
#       color: white;
#       font-weight: 700;
#       padding: 6px 12px;
#       border-radius: 8px;
#       font-size: 16px;
#     }
#     .brand-title {
#       font-size: 17px;
#       font-weight: 600;
#       color: #fff;
#     }
#     .brand-sub {
#       font-size: 12px;
#       color: var(--text-muted);
#     }
#     .header-badges {
#       display: flex;
#       gap: 8px;
#     }
#     .badge {
#       font-size: 11px;
#       padding: 4px 10px;
#       border-radius: 20px;
#       font-weight: 600;
#       letter-spacing: 0.3px;
#       text-transform: uppercase;
#     }
#     .badge-primary { background: #1e3a8a; color: #93c5fd; }
#     .badge-success { background: #064e3b; color: #6ee7b7; }
#     .badge-warning { background: #78350f; color: #fde68a; }
 
#     .main-container {
#       display: flex;
#       flex: 1;
#       overflow: hidden;
#     }
#     .chat-pane {
#       flex: 1.4;
#       display: flex;
#       flex-direction: column;
#       border-right: 1px solid var(--border);
#       background: #0d1322;
#     }
#     .chat-history {
#       flex: 1;
#       padding: 24px;
#       overflow-y: auto;
#       display: flex;
#       flex-direction: column;
#       gap: 16px;
#     }
#     .message {
#       white-space: pre-wrap;
#       max-width: 80%;
#       padding: 14px 18px;
#       border-radius: 14px;
#       font-size: 14px;
#       line-height: 1.5;
#     }
#     .message.customer {
#       align-self: flex-end;
#       background: #2563eb;
#       color: #fff;
#       border-bottom-right-radius: 4px;
#     }
#     .message.assistant {
#       align-self: flex-start;
#       background: var(--card-bg);
#       border: 1px solid var(--border);
#       color: var(--text);
#       border-bottom-left-radius: 4px;
#     }
#     .chat-controls {
#       padding: 16px 24px;
#       background: #0f172a;
#       border-top: 1px solid var(--border);
#       display: flex;
#       gap: 12px;
#       align-items: center;
#     }
#     .chat-input {
#       flex: 1;
#       background: #1e293b;
#       border: 1px solid #334155;
#       color: #fff;
#       padding: 12px 16px;
#       border-radius: 10px;
#       font-size: 14px;
#       outline: none;
#     }
#     .chat-input:focus { border-color: var(--accent); }
#     .btn {
#       background: var(--accent);
#       color: #fff;
#       border: none;
#       padding: 12px 20px;
#       border-radius: 10px;
#       font-size: 14px;
#       font-weight: 600;
#       cursor: pointer;
#       display: flex;
#       align-items: center;
#       gap: 8px;
#       transition: background 0.15s;
#     }
#     .btn:hover { background: var(--accent-hover); }
#     .btn-mic {
#       background: #ef4444;
#     }
#     .btn-mic.recording {
#       animation: pulse 1s infinite alternate;
#     }
#     @keyframes pulse {
#       from { transform: scale(1); }
#       to { transform: scale(1.08); background: #dc2626; }
#     }
 
#     .inspector-pane {
#       flex: 1;
#       padding: 24px;
#       overflow-y: auto;
#       background: #0b0f19;
#       display: flex;
#       flex-direction: column;
#       gap: 20px;
#     }
#     .card {
#       background: var(--card-bg);
#       border: 1px solid var(--border);
#       border-radius: 12px;
#       padding: 16px;
#     }
#     .card-title {
#       font-size: 12px;
#       font-weight: 700;
#       color: var(--text-muted);
#       text-transform: uppercase;
#       letter-spacing: 0.5px;
#       margin-bottom: 12px;
#       display: flex;
#       align-items: center;
#       gap: 8px;
#     }
#     .status-row {
#       display: flex;
#       justify-content: space-between;
#       margin-bottom: 8px;
#       font-size: 13px;
#     }
#     .status-label { color: var(--text-muted); }
#     .status-val { font-weight: 600; font-family: 'JetBrains Mono', monospace; }
#     .chunk-pill {
#       display: inline-block;
#       background: #1e293b;
#       border: 1px solid #334155;
#       padding: 4px 8px;
#       border-radius: 6px;
#       font-size: 12px;
#       font-family: 'JetBrains Mono', monospace;
#       color: #93c5fd;
#       margin-right: 6px;
#       margin-bottom: 6px;
#     }
#     pre {
#       font-family: 'JetBrains Mono', monospace;
#       font-size: 12px;
#       background: #0a0e17;
#       padding: 10px;
#       border-radius: 8px;
#       overflow-x: auto;
#       color: #a5b4fc;
#     }
#   </style>
# </head>
# <body>
 
#   <header>
#     <div class="brand">
#       <div class="brand-logo">ZM</div>
#       <div>
#         <div class="brand-title">ZentroMart VoiceOps 2026</div>
#         <div class="brand-sub">Grounded Customer Support Voice AI · IITG × Gnani.ai</div>
#       </div>
#     </div>
#     <div class="header-badges">
#       <span class="badge badge-primary">Ref Date: 20 Oct 2026</span>
#       <span class="badge badge-success">Gemini 3.5 Flash Lite</span>
#       <span class="badge badge-warning">Gnani Timbre v2.5</span>
#     </div>
#   </header>
 
#   <div class="main-container">
#     <div class="chat-pane">
#       <div class="chat-history" id="chatHistory">
#         <div class="message assistant">
#           Hello! I am your <strong>ZentroMart AI assistant</strong>. How can I help you today? If you have an inquiry regarding an order, please share your 8-digit order number!
#         </div>
#       </div>
#       <div class="chat-controls">
#         <button class="btn btn-mic" id="micBtn" onclick="toggleMic()">🎙️ Record</button>
#         <input type="text" class="chat-input" id="chatInput" placeholder="Type customer message or click Record..." onkeydown="if(event.key==='Enter') sendText()">
#         <button class="btn" onclick="sendText()">Send ➔</button>
#       </div>
#     </div>
 
#     <div class="inspector-pane">
#       <div class="card">
#         <div class="card-title">🛡️ Caller Security & Identity (IDV-2)</div>
#         <div class="status-row">
#           <span class="status-label">Order Identified:</span>
#           <span class="status-val" id="insOrderId">None</span>
#         </div>
#         <div class="status-row">
#           <span class="status-label">Verification Gate:</span>
#           <span class="status-val" id="insVerified" style="color: var(--danger)">UNVERIFIED</span>
#         </div>
#         <div class="status-row">
#           <span class="status-label">Escalation Ticket:</span>
#           <span class="status-val" id="insTicket" style="color: var(--text-muted)">None</span>
#         </div>
#       </div>
 
#       <div class="card">
#         <div class="card-title">📚 Retrieved Knowledge Chunks (RAG)</div>
#         <div id="insChunks">
#           <span class="status-label">No retrieval yet</span>
#         </div>
#       </div>
 
#       <div class="card">
#         <div class="card-title">📦 Verified Order State (Cached)</div>
#         <pre id="insOrderData">// Order details will be unlocked only after identity verification.</pre>
#       </div>
#     </div>
#   </div>
 
#   <audio id="audioPlayer" style="display:none"></audio>
 
#   <script>
#     let isRecording = false;
#     let mediaRecorder = null;
#     let audioChunks = [];
 
#     async function sendText() {
#       const input = document.getElementById("chatInput");
#       const text = input.value.trim();
#       if (!text) return;
#       input.value = "";
 
#       appendMessage("customer", text);
 
#       try {
#         const resp = await fetch("/api/chat", {
#           method: "POST",
#           headers: {"Content-Type": "application/json"},
#           body: JSON.stringify({ message: text })
#         });
#         const data = await resp.json();
#         appendMessage("assistant", data.reply);
#         updateInspector(data);
 
#         if (data.audio_url) {
#           playAudio(data.audio_url);
#         }
#       } catch (err) {
#         console.error("Chat error:", err);
#         appendMessage("assistant", "Sorry, something went wrong. Please try again.");
#       }
#     }
 
#     function appendMessage(role, text) {
#       const history = document.getElementById("chatHistory");
#       const div = document.createElement("div");
#       div.className = "message " + role;
#       div.textContent = text;
#       history.appendChild(div);
#       history.scrollTop = history.scrollHeight;
#       return div;
#     }
 
#     function updateInspector(data) {
#       document.getElementById("insOrderId").innerText = data.order_id || "None";
#       const verEl = document.getElementById("insVerified");
#       if (data.verified) {
#         verEl.innerText = "VERIFIED ✓";
#         verEl.style.color = "var(--success)";
#       } else {
#         verEl.innerText = "UNVERIFIED 🔒";
#         verEl.style.color = "var(--danger)";
#       }
 
#       const tktEl = document.getElementById("insTicket");
#       if (data.ticket_id) {
#         tktEl.innerText = data.ticket_id;
#         tktEl.style.color = "var(--warning)";
#       }
 
#       if (data.order_data) {
#         document.getElementById("insOrderData").innerText = JSON.stringify(data.order_data, null, 2);
#       }
 
#       const container = document.getElementById("insChunks");
#       container.innerHTML = "";
#       if (!data.used_sources || !data.used_sources.length) {
#         container.innerHTML = '<span class="status-label">No retrieval this turn</span>';
#       } else {
#         data.used_sources.forEach(src => {
#           const pill = document.createElement("span");
#           pill.className = "chunk-pill";
#           pill.innerText = "[" + src + "]";
#           container.appendChild(pill);
#         });
#       }
#     }
 
#     function playAudio(url) {
#       const player = document.getElementById("audioPlayer");
#       player.src = url + "?t=" + new Date().getTime();
#       player.play().catch(e => console.log("Audio autoplay prevented:", e));
#     }
 
#     async function toggleMic() {
#       const btn = document.getElementById("micBtn");
#       if (!isRecording) {
#         try {
#           const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
#           mediaRecorder = new MediaRecorder(stream);
#           audioChunks = [];
#           mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
#           mediaRecorder.onstop = uploadAudio;
#           mediaRecorder.start();
#           isRecording = true;
#           btn.classList.add("recording");
#           btn.innerText = "⏹️ Stop";
#         } catch (e) {
#           alert("Microphone permission denied: " + e);
#         }
#       } else {
#         mediaRecorder.stop();
#         isRecording = false;
#         btn.classList.remove("recording");
#         btn.innerText = "🎙️ Record";
#       }
#     }
 
#     async function uploadAudio() {
#       const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
#       const formData = new FormData();
#       formData.append("audio", audioBlob, "recording.wav");
      
#       const bubble = appendMessage("customer", "🎙️ Spoken audio clip...");
      
#       const resp = await fetch("/api/voice", { method: "POST", body: formData });
#       const data = await resp.json();
#       if (data.heard) bubble.textContent = "🎙️ " + data.heard;
#       appendMessage("assistant", data.reply);
#       updateInspector(data);
#       if (data.audio_url) playAudio(data.audio_url);
#     }
#   </script>
# </body>
# </html>
# """
 
 
# class VoiceOpsRequestHandler(http.server.BaseHTTPRequestHandler):
#     def do_GET(self):
#         url_parts = urllib.parse.urlparse(self.path)
#         if url_parts.path in ("/", "/index.html"):
#             self.send_response(200)
#             self.send_header("Content-Type", "text/html; charset=utf-8")
#             self.end_headers()
#             self.wfile.write(HTML_PAGE.encode("utf-8"))
#         elif url_parts.path.startswith("/reply.wav"):
#             reply_wav = PROJECT_ROOT / "sample_outputs" / "web_reply.wav"
#             if reply_wav.exists():
#                 self.send_response(200)
#                 self.send_header("Content-Type", "audio/wav")
#                 self.end_headers()
#                 with open(reply_wav, "rb") as f:
#                     self.wfile.write(f.read())
#             else:
#                 self.send_response(404)
#                 self.end_headers()
#         else:
#             self.send_response(404)
#             self.end_headers()
 
#     def log_message(self, format, *args):
#         pass  # Suppress noisy HTTP access logs
 
#     def do_POST(self):
#         url_parts = urllib.parse.urlparse(self.path)
 
#         if url_parts.path == "/api/chat":
#             content_len = int(self.headers.get("Content-Length", 0))
#             post_body = self.rfile.read(content_len).decode("utf-8")
#             data = json.loads(post_body)
#             msg = data.get("message", "")
#             print(f"[Chat] User: {msg}", flush=True)
 
#             try:
#                 reply = active_agent.respond(msg)
#             except Exception as e:
#                 print(f"[Chat] ERROR: {e}", flush=True)
#                 reply = "Sorry, I ran into a problem answering that. Please try again."
#             print(f"[Chat] Agent replied.", flush=True)
#             out_wav = PROJECT_ROOT / "sample_outputs" / "web_reply.wav"
#             audio_url = "/reply.wav"
#             try:
#                 voice_handler.synthesize_speech(reply, output_file=str(out_wav))
#             except Exception as e:
#                 print(f"[Chat] TTS error: {e}", flush=True)
#                 audio_url = None
 
#             resp_payload = {
#                 "reply": reply,
#                 "order_id": active_agent.order_id,
#                 "verified": active_agent.verified,
#                 "ticket_id": active_agent.last_ticket_id,
#                 "order_data": active_agent.order_data,
#                 "used_sources": active_agent.last_chunks,
#                 "audio_url": audio_url
#             }
#             self.send_response(200)
#             self.send_header("Content-Type", "application/json; charset=utf-8")
#             self.end_headers()
#             self.wfile.write(json.dumps(resp_payload).encode("utf-8"))
 
#         elif url_parts.path == "/api/voice":
#             import tempfile
#             length = int(self.headers.get("Content-Length", 0))
#             body = self.rfile.read(length)
#             ctype = self.headers.get("Content-Type", "")
#             boundary = ctype.split("boundary=")[-1].encode()
#             audio_data = b""
#             for part in body.split(b"--" + boundary):
#                 if b"audio" in part and b"\r\n\r\n" in part:
#                     audio_data = part.split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n--")
#                     break
#             with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
#                 tmp.write(audio_data if audio_data else body)
#                 tmp_path = tmp.name
 
#             print(f"[Voice] Transcribing mic audio...", flush=True)
#             try:
#                 heard, reply, _ = voice_handler.voice_turn(
#                     tmp_path, active_agent,
#                     output_audio_path=str(PROJECT_ROOT / "sample_outputs" / "web_reply.wav")
#                 )
#             except Exception as e:
#                 print(f"[Voice] ERROR: {e}", flush=True)
#                 heard, reply = "", "Sorry, I didn't catch that. Could you please say it again?"
#             print(f"[Voice] Heard: {heard}", flush=True)
#             os.unlink(tmp_path)
 
#             resp_payload = {
#                 "heard": heard,
#                 "reply": reply,
#                 "order_id": active_agent.order_id,
#                 "verified": active_agent.verified,
#                 "ticket_id": active_agent.last_ticket_id,
#                 "order_data": active_agent.order_data,
#                 "used_sources": active_agent.last_chunks,
#                 "audio_url": "/reply.wav"
#             }
#             self.send_response(200)
#             self.send_header("Content-Type", "application/json; charset=utf-8")
#             self.end_headers()
#             self.wfile.write(json.dumps(resp_payload).encode("utf-8"))
 
#         else:
#             self.send_response(404)
#             self.end_headers()
 
 
# def run_server():
#     server = http.server.HTTPServer(("0.0.0.0", PORT), VoiceOpsRequestHandler)
#     print(f"=== ZentroMart VoiceOps Web Dashboard Running! ===")
#     print(f"Open your browser at: http://localhost:{PORT}")
#     try:
#         server.serve_forever()
#     except KeyboardInterrupt:
#         print("\nShutting down server.")
#         server.server_close()
 
 
# if __name__ == "__main__":
#     run_server()
 
##############################################################################

#!/usr/bin/env python3
"""Interactive Web Dashboard for ZentroMart VoiceOps 2026.

Provides a modern browser UI to test the VoiceOps agent:
- Record live audio via microphone or upload .wav files.
- Visual chat interface with audio playback of agent's voice replies.
- Agent Brain Inspector: shows caller verification badge, order state,
  retrieved [SECTION-ID] policy chunks, and escalation tickets.
- Zero extra dependencies (uses Python standard library http.server).

Usage:
    python web_app.py
    Open http://localhost:8080 in your web browser.
"""
import http.server
import json
import os
import sys
import urllib.parse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.agent import SupportAgent
from src.voice import VoiceHandler, normalize_text_for_speech

PORT = 8080
active_agent = SupportAgent(conversation_id="web_session")
voice_handler = VoiceHandler(allow_mock=True)  # UI stays usable without a key; the console warns when Gnani is off

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ZentroMart VoiceOps 2026 — AI Voice Support Agent</title>

  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --border: #1f2937;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }
    header {
      background: #0f172a;
      border-bottom: 1px solid var(--border);
      padding: 14px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-logo {
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      color: white;
      font-weight: 700;
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 16px;
    }
    .brand-title {
      font-size: 17px;
      font-weight: 600;
      color: #fff;
    }
    .brand-sub {
      font-size: 12px;
      color: var(--text-muted);
    }
    .header-badges {
      display: flex;
      gap: 8px;
    }
    .badge {
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 20px;
      font-weight: 600;
      letter-spacing: 0.3px;
      text-transform: uppercase;
    }
    .badge-primary { background: #1e3a8a; color: #93c5fd; }
    .badge-success { background: #064e3b; color: #6ee7b7; }
    .badge-warning { background: #78350f; color: #fde68a; }

    .main-container {
      display: flex;
      flex: 1;
      overflow: hidden;
    }
    .chat-pane {
      flex: 1.4;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--border);
      background: #0d1322;
    }
    .chat-history {
      flex: 1;
      padding: 24px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .message {
      white-space: pre-wrap;
      max-width: 80%;
      padding: 14px 18px;
      border-radius: 14px;
      font-size: 14px;
      line-height: 1.5;
    }
    .message.customer {
      align-self: flex-end;
      background: #2563eb;
      color: #fff;
      border-bottom-right-radius: 4px;
    }
    .message.assistant {
      align-self: flex-start;
      background: var(--card-bg);
      border: 1px solid var(--border);
      color: var(--text);
      border-bottom-left-radius: 4px;
    }
    .chat-controls {
      padding: 16px 24px;
      background: #0f172a;
      border-top: 1px solid var(--border);
      display: flex;
      gap: 12px;
      align-items: center;
    }
    .chat-input {
      flex: 1;
      background: #1e293b;
      border: 1px solid #334155;
      color: #fff;
      padding: 12px 16px;
      border-radius: 10px;
      font-size: 14px;
      outline: none;
    }
    .chat-input:focus { border-color: var(--accent); }
    .btn {
      background: var(--accent);
      color: #fff;
      border: none;
      padding: 12px 20px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background 0.15s;
    }
    .btn:hover { background: var(--accent-hover); }
    .btn-mic {
      background: #ef4444;
    }
    .btn-mic.recording {
      animation: pulse 1s infinite alternate;
    }
    @keyframes pulse {
      from { transform: scale(1); }
      to { transform: scale(1.08); background: #dc2626; }
    }

    .inspector-pane {
      flex: 1;
      padding: 24px;
      overflow-y: auto;
      background: #0b0f19;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
    }
    .card-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .status-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
      font-size: 13px;
    }
    .status-label { color: var(--text-muted); }
    .status-val { font-weight: 600; font-family: 'JetBrains Mono', monospace; }
    .chunk-pill {
      display: inline-block;
      background: #1e293b;
      border: 1px solid #334155;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-family: 'JetBrains Mono', monospace;
      color: #93c5fd;
      margin-right: 6px;
      margin-bottom: 6px;
    }
    pre {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      background: #0a0e17;
      padding: 10px;
      border-radius: 8px;
      overflow-x: auto;
      color: #a5b4fc;
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-logo">ZM</div>
      <div>
        <div class="brand-title">ZentroMart VoiceOps 2026</div>
        <div class="brand-sub">Grounded Customer Support Voice AI · IITG × Gnani.ai</div>
      </div>
    </div>
    <div class="header-badges">
      <span class="badge badge-primary">Ref Date: 20 Oct 2026</span>
      <span class="badge badge-success">Gemini 3.5 Flash Lite</span>
      <span class="badge badge-warning">Gnani Timbre v2.5</span>
    </div>
  </header>

  <div class="main-container">
    <div class="chat-pane">
      <div class="chat-history" id="chatHistory">
        <div class="message assistant">Hello! I am your <strong>ZentroMart AI assistant</strong>. How can I help you today? If you have an inquiry regarding an order, please share your 8-digit order number! </div>
      </div>
      <div class="chat-controls">
        <button class="btn btn-mic" id="micBtn" onclick="toggleMic()">🎙️ Record</button>
        <input type="text" class="chat-input" id="chatInput" placeholder="Type customer message or click Record..." onkeydown="if(event.key==='Enter') sendText()">
        <button class="btn" onclick="sendText()">Send ➔</button>
        <button class="btn" style="background:#475569" onclick="newConversation()">New chat</button>
      </div>
    </div>

    <div class="inspector-pane">
      <div class="card">
        <div class="card-title">🛡️ Caller Security & Identity (IDV-2)</div>
        <div class="status-row">
          <span class="status-label">Order Identified:</span>
          <span class="status-val" id="insOrderId">None</span>
        </div>
        <div class="status-row">
          <span class="status-label">Verification Gate:</span>
          <span class="status-val" id="insVerified" style="color: var(--danger)">UNVERIFIED</span>
        </div>
        <div class="status-row">
          <span class="status-label">Escalation Ticket:</span>
          <span class="status-val" id="insTicket" style="color: var(--text-muted)">None</span>
        </div>
      </div>

      <div class="card">
        <div class="card-title">📚 Retrieved Knowledge Chunks (RAG)</div>
        <div id="insChunks">
          <span class="status-label">No retrieval yet</span>
        </div>
      </div>

      <div class="card">
        <div class="card-title">📦 Verified Order State (Cached)</div>
        <pre id="insOrderData">// Order details will be unlocked only after identity verification.</pre>
      </div>
    </div>
  </div>

  <audio id="audioPlayer" style="display:none"></audio>

  <script>
    async function newConversation() {
      try { await fetch("/api/reset", { method: "POST" }); } catch (e) { console.error(e); }
      location.reload();
    }
    // A fresh page always starts a fresh, unverified conversation on the server too
    fetch("/api/reset", { method: "POST" }).catch(e => console.error(e));

    let isRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];

    async function sendText() {
      const input = document.getElementById("chatInput");
      const text = input.value.trim();
      if (!text) return;
      input.value = "";

      appendMessage("customer", text);

      try {
        const resp = await fetch("/api/chat", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({ message: text })
        });
        const data = await resp.json();
        appendMessage("assistant", data.reply);
        updateInspector(data);

        if (data.audio_url) {
          playAudio(data.audio_url);
        }
      } catch (err) {
        console.error("Chat error:", err);
        appendMessage("assistant", "Sorry, something went wrong. Please try again.");
      }
    }

    function appendMessage(role, text) {
      const history = document.getElementById("chatHistory");
      const div = document.createElement("div");
      div.className = "message " + role;
      div.textContent = text;
      history.appendChild(div);
      history.scrollTop = history.scrollHeight;
      return div;
    }

    function updateInspector(data) {
      document.getElementById("insOrderId").innerText = data.order_id || "None";
      const verEl = document.getElementById("insVerified");
      if (data.verified) {
        verEl.innerText = "VERIFIED ✓";
        verEl.style.color = "var(--success)";
      } else {
        verEl.innerText = "UNVERIFIED 🔒";
        verEl.style.color = "var(--danger)";
      }

      const tktEl = document.getElementById("insTicket");
      if (data.ticket_id) {
        tktEl.innerText = data.ticket_id;
        tktEl.style.color = "var(--warning)";
      }

      if (data.order_data) {
        document.getElementById("insOrderData").innerText = JSON.stringify(data.order_data, null, 2);
      }

      const container = document.getElementById("insChunks");
      container.innerHTML = "";
      if (!data.used_sources || !data.used_sources.length) {
        container.innerHTML = '<span class="status-label">No retrieval this turn</span>';
      } else {
        data.used_sources.forEach(src => {
          const pill = document.createElement("span");
          pill.className = "chunk-pill";
          pill.innerText = "[" + src + "]";
          container.appendChild(pill);
        });
      }
    }

    function playAudio(url) {
      const player = document.getElementById("audioPlayer");
      player.src = url + "?t=" + new Date().getTime();
      player.play().catch(e => console.log("Audio autoplay prevented:", e));
    }

    async function toggleMic() {
      const btn = document.getElementById("micBtn");
      if (!isRecording) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          mediaRecorder = new MediaRecorder(stream);
          audioChunks = [];
          mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
          mediaRecorder.onstop = uploadAudio;
          mediaRecorder.start();
          setTimeout(() => { if (isRecording) toggleMic(); }, 55000);
          isRecording = true;
          btn.classList.add("recording");
          btn.innerText = "⏹️ Stop";
        } catch (e) {
          alert("Microphone permission denied: " + e);
        }
      } else {
        mediaRecorder.stop();
        isRecording = false;
        btn.classList.remove("recording");
        btn.innerText = "🎙️ Record";
      }
    }

    async function toWav16k(blob) {
      const buf = await blob.arrayBuffer();
      const ac = new (window.AudioContext || window.webkitAudioContext)();
      const decoded = await ac.decodeAudioData(buf);
      ac.close();
      const rate = 16000;
      const off = new OfflineAudioContext(1, Math.max(1, Math.ceil(decoded.duration * rate)), rate);
      const src = off.createBufferSource();
      src.buffer = decoded;
      src.connect(off.destination);
      src.start();
      const pcm = (await off.startRendering()).getChannelData(0);
      const out = new ArrayBuffer(44 + pcm.length * 2);
      const v = new DataView(out);
      const tag = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
      tag(0, "RIFF"); v.setUint32(4, 36 + pcm.length * 2, true); tag(8, "WAVE"); tag(12, "fmt ");
      v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
      v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
      tag(36, "data"); v.setUint32(40, pcm.length * 2, true);
      let o = 44;
      for (let i = 0; i < pcm.length; i++, o += 2) {
        const x = Math.max(-1, Math.min(1, pcm[i]));
        v.setInt16(o, x < 0 ? x * 0x8000 : x * 0x7FFF, true);
      }
      return new Blob([out], { type: "audio/wav" });
    }

    async function uploadAudio() {
      const bubble = appendMessage("customer", "🎙️ Spoken audio clip...");
      try {
        const raw = new Blob(audioChunks, { type: (mediaRecorder && mediaRecorder.mimeType) || "audio/webm" });
        const wav = await toWav16k(raw);
        const formData = new FormData();
        formData.append("audio", wav, "recording.wav");
        const resp = await fetch("/api/voice", { method: "POST", body: formData });
        const data = await resp.json();
        if (data.error) bubble.textContent = "🎙️ ⚠ " + data.error;
        else bubble.textContent = "🎙️ " + (data.heard || "(no speech detected)");
        appendMessage("assistant", data.reply);
        updateInspector(data);
        if (data.audio_url) playAudio(data.audio_url);
      } catch (e) {
        console.error("Voice error:", e);
        bubble.textContent = "🎙️ ⚠ Could not process the recording: " + e;
      }
    }
  </script>
</body>
</html>
"""


class VoiceOpsRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        if url_parts.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif url_parts.path.startswith("/reply.wav"):
            reply_wav = PROJECT_ROOT / "sample_outputs" / "web_reply.wav"
            if reply_wav.exists():
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.end_headers()
                with open(reply_wav, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress noisy HTTP access logs

    def do_POST(self):
        url_parts = urllib.parse.urlparse(self.path)

        if url_parts.path == "/api/reset":
            global active_agent
            active_agent = SupportAgent(conversation_id="web_session")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
            return

        if url_parts.path == "/api/chat":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(post_body)
            msg = data.get("message", "")
            print(f"[Chat] User: {msg}", flush=True)

            try:
                reply = active_agent.respond(msg)
            except Exception as e:
                print(f"[Chat] ERROR: {e}", flush=True)
                reply = "Sorry, I ran into a problem answering that. Please try again."
            print(f"[Chat] Agent replied.", flush=True)
            out_wav = PROJECT_ROOT / "sample_outputs" / "web_reply.wav"
            audio_url = "/reply.wav"
            try:
                voice_handler.synthesize_speech(reply, output_file=str(out_wav))
            except Exception as e:
                print(f"[Chat] TTS error: {e}", flush=True)
                audio_url = None

            resp_payload = {
                "reply": reply,
                "order_id": active_agent.order_id,
                "verified": active_agent.verified,
                "ticket_id": active_agent.last_ticket_id,
                "order_data": active_agent.order_data,
                "used_sources": active_agent.last_chunks,
                "audio_url": audio_url
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(resp_payload).encode("utf-8"))

        elif url_parts.path == "/api/voice":
            import tempfile
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            ctype = self.headers.get("Content-Type", "")
            from email.parser import BytesParser
            from email.policy import default as email_default
            msg = BytesParser(policy=email_default).parsebytes(
                b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + body)
            audio_data = b""
            for part in msg.iter_parts():
                if part.get_param("name", header="content-disposition") == "audio":
                    audio_data = part.get_payload(decode=True) or b""
                    break
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            print(f"[Voice] Received {len(audio_data)} bytes of audio", flush=True)

            print(f"[Voice] Transcribing mic audio...", flush=True)
            try:
                heard, reply, _ = voice_handler.voice_turn(
                    tmp_path, active_agent,
                    output_audio_path=str(PROJECT_ROOT / "sample_outputs" / "web_reply.wav")
                )
                voice_error = None
            except Exception as e:
                import traceback; traceback.print_exc()
                print(f"[Voice] ERROR: {e}", flush=True)
                voice_error = f"{type(e).__name__}: {e}"
                heard, reply = "", "Sorry, I didn't catch that. Could you please say it again?"
            print(f"[Voice] Heard: {heard!r}", flush=True)
            os.unlink(tmp_path)

            resp_payload = {
                "heard": heard,
                "error": voice_error,
                "reply": reply,
                "order_id": active_agent.order_id,
                "verified": active_agent.verified,
                "ticket_id": active_agent.last_ticket_id,
                "order_data": active_agent.order_data,
                "used_sources": active_agent.last_chunks,
                "audio_url": "/reply.wav"
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(resp_payload).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    server = http.server.HTTPServer(("0.0.0.0", PORT), VoiceOpsRequestHandler)
    print(f"=== ZentroMart VoiceOps Web Dashboard Running! ===")
    print(f"Open your browser at: http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    run_server()