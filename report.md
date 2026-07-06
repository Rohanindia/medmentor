# 🏥 PROJECT REPORT: MedMentor — AI Clinical Tutor
**An Open-Source, Multilingual, MCP-Enabled Clinical Education and Patient Safety Platform**

---

## 📌 1. EXECUTIVE SUMMARY
**MedMentor** is an innovative, production-grade AI Clinical Tutor and Patient Safety tool built to bridge the gap between textbook medical knowledge and real-world clinical reasoning. 

Leveraging the **Model Context Protocol (MCP)**, **FHIR R4 (Fast Healthcare Interoperability Resources)** standard, and **RxNorm (NIH drug interaction database)**, MedMentor allows medical students to practice clinical decision-making using real, live hospital patient data in a completely safe simulation environment. 

In version 6.0, MedMentor introduces complete **multilingual voice and text capabilities (English, Hindi, Kannada)**, powered by a cost-efficient **hybrid translation pipeline** (offloading translation from the LLM to Google Translate, reducing API tokens by 66%) and high-fidelity **Sarvam AI Text-to-Speech (TTS)**. The user interface has been overhauled with a premium **Claude-style typography engine** and an custom Socratic markdown parser.

---

## 🔍 2. PROBLEM STATEMENT & CLINICAL CONTEXT

### A. The Pedagogical Gap in Medical Education
Medical students worldwide, especially in developing nations like India, are trained heavily on passive rote memorization of clinical facts. However, actual clinical practice requires active, non-linear reasoning based on patient profiles, lab reports, and drug lists. MedMentor addresses this by acting as a Socratic tutor, engaging students in case-based discussions rather than giving them immediate, direct answers.

### B. The Threat of Adverse Drug Events (ADEs)
- **Polypharmacy:** Patients often visit multiple specialists, receiving separate prescriptions. In India, self-medication is highly prevalent.
- **Drug-Drug Interactions (DDIs):** Without automated clinical support, doctors and patients miss critical contraindications (e.g., combining Warfarin with Ibuprofen, leading to severe internal hemorrhage).
- **The Numbers:** Over **250,000 deaths** occur annually due to medical errors globally.

---

## 🏗️ 3. SYSTEM ARCHITECTURE & INTEGRATION STANDARDS

MedMentor is constructed on a decoupled microservices model using lightweight, high-performance APIs:

```
+-------------------------------------------------------------+
|                     Frontend Chat UI                        |
|        (index.html - HTML5, CSS Variables, Web Speech API)  |
+-------------------------------------------------------------+
                              │   ▲
             HTTP / JSON      │   │   JSON Response
                              ▼   │
+-------------------------------------------------------------+
|                     FastAPI HTTP Bridge                     |
|                         (bridge.py)                         |
+------------------------------┬────────────────--------------+
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
+---------------------+ +-------------+ +--------------------+
|     voice.py        | |   Groq AI   | |   server.py (MCP)  |
| (Google Translate & | | (Llama 70B  | | (FHIR & RxNorm SDK)|
|   Sarvam AI TTS)    | |  Tutor LLM) | |                    |
+---------------------+ +-------------+ +----------┬---------+
                                                   │
                                ┌──────────────────┴──────────────────┐
                                ▼                                     ▼
                     +--------------------+                +--------------------+
                     | HAPI FHIR R4 API   |                |   RxNorm REST API  |
                     | (Real Hospital data|                | (NIH Drug Database)|
                     +--------------------+                +--------------------+
```

### Key Technical Standards Used:
1. **Model Context Protocol (MCP):** Connects the LLM client to structured tool endpoints, allowing standard data schema sharing.
2. **FHIR R4:** Serves patient resources (`Patient`, `MedicationRequest`, `Observation`) in standard JSON format.
3. **RxNorm REST API:** Pulls official RXCUI (RxNorm Concept Unique Identifier) codes to query drug-drug interaction pairs.

---

## 🚀 4. CORE MODULES & WORKFLOW IMPLEMENTATION

### 📁 A. The Backend Routing & Authentication Engine (`bridge.py`)
Developed using **FastAPI**, this module manages user authentication (JWT-based token creation), acts as the main HTTP interface, and routes requests to either the standard MCP tools or the voice translation pipeline.

### 📁 B. The Multilingual Voice & Translation Pipeline (`voice.py`)
To make medical education accessible to students and common citizens in India, this script introduces native Hindi (`hi-IN`) and Kannada (`kn-IN`) support.

#### 1. Unicode-Based Language Detection
Instead of consuming expensive AI api calls to detect input language, `voice.py` runs a regex search using local Unicode ranges:
*   **Hindi Range:** `\u0900-\u097F`
*   **Kannada Range:** `\u0C80-\u0CFF`

#### 2. Hybrid Translation Pipeline (66% Token Savings)
Instead of forcing Groq to perform English translation, we use the `deep-translator` package (Google Translate) for input/output text rendering. Groq is called exactly **once** for the core medical explanation:

```
[Hindi/Kannada User Input] ──► [Google Translate (FREE)] ──► [English Text]
                                                                  │
[Hindi/Kannada Output] ◄── [Google Translate (FREE)] ◄── [Groq AI (English)]
```

#### 3. Indian Medical Vocabulary Mapping
Colloquial terminology used in Indian health centers (e.g. "Sugar", "BP", "Drip", "TB", "Chakkar", "Sakkare", "Jvara") is automatically pre-processed and normalized into clinical terms ("Diabetes Mellitus", "Hypertension", "Intravenous Infusion", "Tuberculosis", "Vertigo") before being sent to the AI.

### 📁 C. Text-To-Speech (TTS) Engine
We implemented a robust **3-Layer Speech Synthesizer** in the frontend:
1.  **Sarvam AI TTS (Primary):** Utilizes Sarvam's `bulbul:v2` model via backend proxy (`POST /voice/tts`). It delivers natural Indian accents and accurately handles mixed-language text (such as English medical terms embedded in Hindi sentences).
2.  **Google Translate TTS (Fallback 1):** Audio streams fetched from the translation engine chunked into 190-character segments.
3.  **Web Speech API (Fallback 2):** Native browser speech synthesis.

### 📁 D. Frontend Interface & Typography Upgrade (`index.html`)
The frontend is constructed using pure HTML5 and Vanilla CSS. It features:
*   **Premium Fonts:** *Lora Serif* for the AI response prose (improving legibility of academic case files) and *Inter Sans* for the user input.
*   **Custom Markdown Renderer:** Parses standard markdown (`#`, `##`, `###`, `**`, `*`, `> blockquotes`, code blocks, lists) directly to clean HTML tags.
*   **Voice Control HUD:** Interactive microphone button that toggles recording states with a CSS pulsing ring.

---

## 🛠️ 5. KEY API ENDPOINTS

### 1. `POST /voice/chat`
Accepts a multilingual query and returns the translated AI response.
*   **Payload:** `{ "message": "ಮಧುಮೇಹದ ಬಗ್ಗೆ ಹೇಳಿ", "language": "kannada", "difficulty": "intermediate" }`
*   **Response:** `{ "response": "[Translated Kannada Answer]", "detected_language": "kannada", "english_question": "Tell me about diabetes", "english_response": "[English Tutor Answer]" }`

### 2. `POST /voice/tts`
Synthesizes speech using Sarvam AI.
*   **Payload:** `{ "text": "नमस्ते, मैं आपका क्लिनिकल ट्यूटर हूँ।", "language": "hindi" }`
*   **Response:** `{ "success": true, "audio": "[Base64 encoded WAV Audio]", "format": "wav", "speaker": "anushka" }`

### 3. `POST /tool`
Direct execution interface for the MCP hospital database tools.
*   **Payload:** `{ "tool": "get_drug_interactions", "arguments": { "rxcuis": ["1191", "8410"] } }`

---

## 📊 6. IMPACT & EDUCATIONAL VALUE

1.  **Immersive Learning:** Medical students can pull real EHR records directly from the hospital FHIR database to study active diagnoses, laboratory tests (vitals, blood profiles), and evaluate potential complications.
2.  **Inclusive Access:** By supporting local Indian languages with high-fidelity speech synthesis, regional healthcare students and patients can comprehend critical drug warnings and disease pathophysiology in their mother tongue.
3.  **Cost Efficiency:** Decoupling translation from the primary LLM reduces API usage overhead, allowing MedMentor to operate at a fraction of standard LLM application costs.

---

## 🔮 7. FUTURE ROADMAP
*   **Offline Support:** Pack local language models (like IndicTrans2) to run on local servers without internet access.
*   **FHIR Write-Back:** Enable students to write practice diagnosis notes back to a simulation FHIR server for assessment.
*   **Speech-to-Speech Low Latency:** Implement WebSocket streaming with Sarvam AI and Groq Llama-3-Guard for real-time oral exams.
