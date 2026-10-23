# VoiceOps 2026 — ZentroMart AI Voice Customer Support Agent

**An LLM-powered, retrieval-augmented conversational voice assistant for e-commerce customer support.**

Developed for the **VoiceOps 2026 Capstone Project**, organized by the Consulting & Analytics Club, IIT Guwahati, in collaboration with Gnani.ai.

## Project Overview

VoiceOps 2026 is an AI customer support system developed for ZentroMart, a simulated Indian e-commerce retailer.

The project combines Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), conversational state management, mock business tools, and speech processing to support customer interactions.

The assistant is designed to help customers with order tracking, cancellations, returns, refunds, warranty queries, and escalation requests while grounding responses in company documentation.

The implementation includes a browser-based voice dashboard, a batch audio-processing pipeline, and automated evaluations across three development milestones.

## Key Features

- **Retrieval-Augmented Generation:** Retrieves relevant information from ZentroMart's policies, FAQs, help articles, and product catalog.
- **Policy-Aware Responses:** Prioritizes active policy documents over outdated or superseded information.
- **Multi-Turn Conversations:** Maintains conversational context across customer interactions.
- **Identity Verification:** Requests a registered phone-number suffix or delivery PIN code before disclosing protected order information.
- **Tool Integration:** Uses mock order-lookup and support-ticket tools.
- **Refund Timeline Calculations:** Includes deterministic business-day calculations that account for holidays.
- **Voice Interaction:** Integrates Gnani.ai speech-to-text (STT) and text-to-speech (TTS).
- **Interactive Dashboard:** Supports typed messages, microphone input, spoken responses, and agent-state inspection.
- **Batch Audio Processing:** Processes audio files and saves structured JSON results and synthesized replies.

## System Architecture

```text
Customer Voice / Text
         |
         v
Gnani.ai Speech-to-Text
    (Voice input only)
         |
         v
Conversational Support Agent
         |
         +---- Gemini LLM
         |
         +---- RAG Retrieval
         |       |
         |       +---- Company Policies
         |       +---- FAQs / Help Articles
         |       +---- Product Catalog
         |
         +---- Mock Business Tools
         |       |
         |       +---- Order Lookup
         |       +---- Identity Verification
         |       +---- Ticket Creation
         |
         +---- Conversation State
         |
         v
Grounded Text Response
         |
         v
Speech Text Normalization
         |
         v
Gnani.ai Text-to-Speech
         |
         v
Customer Response + JSON Logs
```

## Development Milestones

### Step 1 — Prompted LLM Baseline

Implemented a baseline customer support assistant using a Gemini language model without retrieval from company documentation.

The baseline was evaluated on 52 practice questions.

**Result: 17/52 correct (32.69%).**

The evaluation demonstrated the limitations of relying on general model knowledge for company-specific policies, including inaccurate return periods and refund timelines.

### Step 2 — Knowledge Grounding with RAG

Developed a retrieval system using ZentroMart's knowledge base and product catalog.

Implementation includes:

- Parsing Markdown policy documents and metadata.
- Section-level knowledge-base chunking.
- Product catalog indexing.
- Dense embeddings using `gemini-embedding-001`.
- Cosine-similarity retrieval with document-priority weighting.
- Additional matching for product identifiers and relevant policy categories.
- Response generation using retrieved context.

**Result: 42/52 correct (80.77%).**

This represents a **48.08 percentage-point improvement** over the baseline.

The evaluation script reported a retrieval hit rate of **96.15% (50/52)** under its matching criteria. This metric includes questions without specified reference evidence and should not be interpreted as retrieval precision.

### Step 3 — Multi-Turn Conversations and Tool Calling

Implemented a stateful customer support agent that manages ongoing conversations and invokes mock business tools.

The agent supports:

- Order-number recognition and lookup.
- Customer identity verification.
- Verified access to order details.
- Context retention across multiple turns.
- Escalation and support-ticket creation.
- Policy-grounded follow-up responses.

**Result: 86/96 evaluated turns passed (89.58%) across 23 conversations.**

These results reflect automated practice-scenario evaluations rather than production deployment performance.

### Step 4 — Voice Integration

Integrated Gnani.ai speech services with the conversational agent.

**Speech-to-Text:** Converts customer audio into text for processing.

**Text-to-Speech:** Converts the agent's response into spoken audio using Gnani.ai's TTS service.

**Speech Normalization:** Formats dates, amounts, and order identifiers for clearer spoken responses.

**Batch Processing:** The `run.py` runner accepts audio files, processes them through the support pipeline, and saves output audio and structured JSON logs.

## Evaluation Results

| Metric | Result |
|---|---|
| Step 1 — LLM Baseline | 32.69% (17/52) |
| Step 2 — Grounded RAG | 80.77% (42/52) |
| Absolute Improvement | +48.08 percentage points |
| Step 2 Retrieval Hit Rate* | 96.15% (50/52) |
| Step 3 Multi-Turn Evaluation | 89.58% (86/96 turns) |
| Multi-Turn Scenarios | 23 |

*Retrieval hit rate follows the project's evaluation-script definition and includes cases without specified gold evidence.*

The evaluation uses automated matching criteria. These scores do not establish equivalent human-rated answer quality or complete freedom from hallucinations.

Evaluation artifacts are available in:

```text
sample_outputs/
├── step1_baseline_results.json
├── step2_rag_results.json
└── step3_conversation_results.json
```

## Known Limitations and Future Improvements

The RAG implementation substantially improved benchmark performance, but some issues remain:

| Observed issue | Planned improvement |
|---|---|
| Refund answers sometimes omit exact dates | Integrate deterministic timeline results directly into final response formatting |
| Some escalation scenarios are missed | Enforce escalation rules before LLM response generation |
| A product warranty duration was answered incorrectly | Give verified SKU-level metadata stronger priority |
| Some non-returnable product queries fail | Improve category normalization and policy matching |

Additional improvements could include human evaluation, more comprehensive regression tests, stronger confidence calibration, and broader voice-testing coverage.

## Bonus Implementations

### Interactive Web Dashboard

A browser-based interface is provided through `web_app.py`.

It supports customer text input, microphone interaction, audio playback, and inspection of relevant conversation state.

The interface also exposes useful debugging information such as verification status, order context, retrieved policy references, and ticket details.

### Batch Voice Runner

`run.py` supports processing audio files from an input directory and writing structured results to an output directory.

### Speech Testing and Diagnostics

Additional scripts support voice testing, sample-audio preparation, and local project diagnostics.

## Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Language model | Google Gemini |
| Embedding model | `gemini-embedding-001` |
| Retrieval | Dense vector similarity with policy-aware scoring |
| Speech-to-Text | Gnani.ai STT |
| Text-to-Speech | Gnani.ai TTS |
| Web dashboard | Python HTTP server, HTML, CSS, JavaScript |
| Business tools | Python-based mock order and ticket operations |
| Evaluation | Custom Python evaluation scripts |

## Project Structure

```text
VoiceOps-2026/
│
├── src/
│   ├── agent.py
│   ├── config.py
│   ├── llm.py
│   ├── rag.py
│   ├── timelines.py
│   ├── voice.py
│   ├── step1_baseline.py
│   ├── step2_rag_eval.py
│   └── step3_conv_eval.py
│
├── sample_outputs/
│   ├── step1_baseline_results.json
│   ├── step2_rag_results.json
│   ├── step3_conversation_results.json
│   └── batch_summary.json
│
├── web_app.py
├── run.py
├── test_voice.py
├── check_files.py
├── lookup_order.py
├── create_sample_audio.py
├── requirements.txt
├── .env.example
├── REPORT.md
└── README.md
```

The capstone dataset is maintained locally and excluded from the public repository.

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Shikha07-Git/VoiceOps-2026.git
cd VoiceOps-2026
```

### 2. Install dependencies

Use a suitable Python 3 environment.

```bash
python -m pip install -r requirements.txt
```

### 3. Configure API credentials

Copy `.env.example` to `.env` and supply your own credentials.

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure these environment variables:

```dotenv
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_supported_gemini_model
GEMINI_EMBED_MODEL=gemini-embedding-001

GNANI_API_KEY=your_gnani_api_key
```

The `.env` file is excluded from Git tracking. Never commit real API keys.

### 4. Set up the dataset

The application expects the provided capstone dataset to be extracted into the project root with this directory name:

```text
Capstone_Project_Dataset_FTTT_2026/
├── data/
├── kb/
├── practice/
└── tools/
```

The original dataset must be obtained separately through authorized capstone materials. It is not included in this public repository.

### 5. Launch the web dashboard

```bash
python web_app.py
```

Open:

**http://localhost:8080**

Use the interface to enter a customer query or record a voice message.

### 6. Run the batch voice pipeline

```bash
python run.py --input_dir sample_audio --output_dir batch_test_outputs
```

Place supported audio inputs in the selected input directory before running the command.

The batch pipeline produces response files and JSON logs. Real speech processing requires valid Gnani.ai credentials and compatible audio input.

## Evaluation Scripts

The project includes separate scripts for its first three milestones:

```bash
python -m src.step1_baseline
python -m src.step2_rag_eval
python -m src.step3_conv_eval
```

Evaluation requires the locally available capstone dataset, configured model access, and any relevant generated embedding cache.

Running the evaluations again may produce different results due to model behavior, configuration, or API changes.

## Privacy and Security

- API credentials are stored locally in `.env`.
- The raw capstone dataset is excluded from the public Git repository.
- Order-related information is subject to application-level identity-verification checks.
- Mock business tools are used for order lookup and ticket creation.
- Evaluation artifacts are provided for reproducibility.

This is a capstone prototype, not a production-hardened customer support service. Real-world deployment would require additional authentication, privacy controls, monitoring, and security testing.

## Conclusion

VoiceOps 2026 demonstrates how retrieval grounding, conversational state, business-tool integration, and speech services can be combined into a customer support assistant.

The improvement from **32.69% baseline accuracy to 80.77% RAG accuracy** demonstrates the value of company-specific knowledge grounding under the project's automated evaluation criteria.

The project also highlights remaining challenges in exact timeline generation, escalation consistency, and product-specific policy interpretation.

**Repository:** https://github.com/Shikha07-Git/VoiceOps-2026

**Project:** VoiceOps 2026 Capstone — IIT Guwahati × Gnani.ai
