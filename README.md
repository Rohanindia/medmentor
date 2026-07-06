# 🏥 MedMentor — AI Clinical Tutor

> **"ChatGPT gives you the answer. MedMentor makes you a better doctor."**

An AI-powered clinical tutor that teaches medical students and helps patients understand their health. Now with complete **Hindi & Kannada Voice Support**, **Sarvam AI Indian Text-to-Speech (TTS)**, and a **Claude-style premium typography interface**.

![MedMentor](https://img.shields.io/badge/MedMentor-AI%20Clinical%20Tutor-blue) ![FHIR](https://img.shields.io/badge/FHIR-R4-green) ![MCP](https://img.shields.io/badge/MCP-Enabled-orange) ![Sarvam AI](https://img.shields.io/badge/Sarvam%20AI-TTS-red) ![Groq AI](https://img.shields.io/badge/Groq%20AI-FREE-brightgreen) ![Hackathon](https://img.shields.io/badge/Agents%20Assemble-Hackathon%202026-purple)

---

## 🎯 The Problem

Every day in India and worldwide:
- A patient visits **3 different doctors**
- Each doctor prescribes different medicines
- **Nobody checks if they are safe together**
- Patients suffer from dangerous drug-drug interactions ⚠️

Medical students learn from **textbooks** — but real doctors think from **patient cases**. There is a huge gap between theory and real-world clinical reasoning. **MedMentor bridges that gap.**

---

## 💡 What MedMentor Does

| For Whom | What They Can Do |
|---|---|
| 🎓 **Medical Students** | Practice clinical reasoning with real patient cases and Socratic quizzes |
| 👴 **Common People** | Understand their medicines and health conditions in English, Hindi, or Kannada |
| 👩‍⚕️ **Doctors & Nurses** | Run quick, intelligent drug interaction checks on the go |
| 🏫 **Medical Colleges** | Integrate as an AI-powered teaching assistant for MBBS students |

---

## 🚀 New Features in v6.0

### 🎙️ 1. Complete Indian Voice & Language Support
MedMentor now supports complete voice-in and voice-out in **English 🇬🇧**, **Hindi 🇮🇳**, and **Kannada 🇮🇳**:
- **Automatic Language Detection:** Unicode-based language detection dynamically checks if you speak/type in Hindi, Kannada, or English.
- **Voice Typing:** Speak using the microphone button 🎤. It automatically detects your spoken Indian language and translates/sends it to the AI.
- **Native Welcome Messages:** Custom, friendly, native welcome greetings automatically adjust based on your selected language.
- **Local State Caching:** Saves your preferred language in `localStorage` as `mm_language` so it stays selected next time you load.

### 🏆 2. Sarvam AI Text-to-Speech (TTS) Integration
We integrated **Sarvam AI's Bulbul Model** (`bulbul:v2`) to provide industry-leading, natural-sounding voice output:
- **Real Indian Voices:** Speaks with human-like Indian accentuation, including correct pronunciation of English medical words within Hindi/Kannada sentences (e.g. pronouncing "diabetes" or "paracetamol" perfectly).
- **3-Layer Speech Fallback System:**
  1. **Layer 1: Sarvam AI** (Primary) — High-quality, natural Indian voice synthesis.
  2. **Layer 2: Google Translate TTS** (Fallback 1) — Smooth, zero-cost online audio fallback.
  3. **Layer 3: Web Speech API** (Fallback 2) — Offline browser native speech synthesis.

### ⚡ 3. 66% Token Savings with Google Translate Hybrid
To prevent Groq API rate limits and conserve tokens, translation is decoupled from the LLM:
- **Before:** 3 expensive Groq LLM API calls per message (translate in → generate response → translate out).
- **Now:** Google Translate is used for inputs and outputs (free & instant), leaving Groq to focus **solely** on generating the clinical explanation. This reduces Groq token consumption by **66%**!

### 🎨 4. Claude-Style Premium Chat UI
Upgraded typography and reading layout inspired by Anthropic's Claude:
- **Lora Serif Font** for AI responses — offering an elegant, textbook-like reading experience.
- **Inter Sans Font** for user text — clean, modern, and highly readable.
- **Custom Markdown Parser:** Displays **bold**, *italic*, `# headings`, `inline code`, blockquotes with left borders, bullet lists with custom accent dots, and horizontal dividers.
- **Micro-Animations:** Sleek transitions, pulsing record indicator, and bouncing thinking dots.

---

## 🏗️ Multilingual Architecture

```
                       🎙️ Voice Input (hi-IN / kn-IN)
                                    ↓
                       🌐 Web Speech API Recognition
                                    ↓
                       📝 Hindi/Kannada Input Text
                                    ↓
                  🌐 Google Translate (FREE Translate)
                                    ↓
                       📝 English Medical Question
                                    ↓
                        🧠 Groq AI Llama-3 API
                                    ↓
                       📝 English Medical Answer
                                    ↓
                  🌐 Google Translate (FREE Translate)
                                    ↓
                  📝 Hindi/Kannada Medical Explanation
                                    ↓
                    🔊 Sarvam AI Bulbul TTS (hi / kn)
                                    ↓
                        🎧 Real Indian Voice Out
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **MCP** (Model Context Protocol) | Connects AI to live hospital data |
| **FHIR R4 Standard** | Real hospital patient data schema (demographics, meds, labs) |
| **Sarvam AI API** | High-fidelity Indian Text-to-Speech (`hi-IN` & `kn-IN`) |
| **Deep Translator** | Free, fast Google Translate pipeline |
| **Groq AI (Llama 3.3 70B)** | Clinical tutor intelligence and Socratic quiz engine |
| **FastAPI / Uvicorn** | HTTP server bridge |
| **RxNorm API (NIH)** | Live drug-drug interaction checker |
| **Web Speech API** | Browser-native Speech-to-Text |

---

## 🚀 Getting Started

### Step 1 — Clone the Repository
```bash
git clone https://github.com/Rohanindia/medmentor.git
cd medmentor
```

### Step 2 — Set Up Python Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate   # On Windows
source venv/bin/activate # On Unix/macOS
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Configure Keys
Create a `.env` file in the root folder:
```ini
GROQ_API_KEY=your_groq_key_here
SARVAM_API_KEY=your_sarvam_key_here
```
> Get your free Groq API key at [console.groq.com](https://console.groq.com) and your Sarvam key at [dashboard.sarvam.ai](https://dashboard.sarvam.ai).

### Step 5 — Run MedMentor
```bash
python bridge.py
```

### Step 6 — Open in Browser
Open **Chrome or Edge** (required for microphone support):
```
http://localhost:8000/app
```

---

## 🔧 MCP Tools

| Tool Name | Description | Source |
|---|---|---|
| `get_patient_case` | Fetch patient demographics, conditions, medications | Live HAPI FHIR R4 |
| `get_lab_results` | Fetch recent blood tests, vitals, and diagnostics | Live HAPI FHIR R4 |
| `get_drug_interactions` | Find clinical drug-drug interactions | RxNorm Database (NIH) |
| `get_clinical_question` | Generate custom Socratic quiz questions | Groq LLM |

---

## 👨‍💻 Developer

**Rohan** — Student Developer from India 🇮🇳

> Building MedMentor to make healthcare education free, accessible, and inclusive for everyone in their mother tongue. 🩺

---

## 📄 License

MIT License — Free to use, modify, and share.