# 🏥 MedMentor — AI Clinical Tutor

> **"ChatGPT gives you the answer. MedMentor makes you a better doctor."**

An AI-powered clinical tutor that teaches medical students and helps common people understand their health — completely free.

![MedMentor](https://img.shields.io/badge/MedMentor-AI%20Clinical%20Tutor-blue) ![FHIR](https://img.shields.io/badge/FHIR-R4-green) ![MCP](https://img.shields.io/badge/MCP-Enabled-orange) ![Groq AI](https://img.shields.io/badge/Groq%20AI-FREE-brightgreen) ![Hackathon](https://img.shields.io/badge/Agents%20Assemble-Hackathon%202026-purple)

## 🎯 The Problem

Every day in India and worldwide:
- A patient visits **3 different doctors**
- Each doctor prescribes different medicines
- **Nobody checks if they are safe together**
- Patient suffers from dangerous drug interactions ⚠️

Medical students learn from **textbooks** — but real doctors think from **patient cases**. There is a huge gap between theory and real-world clinical reasoning. **MedMentor bridges that gap.**

## 💡 What MedMentor Does

| For Who | What They Can Do |
|---|---|
| 🎓 Medical Students | Practice clinical reasoning with real patient cases |
| 👴 Common People | Understand their medicines and health conditions |
| 👩‍⚕️ Doctors & Nurses | Quick drug interaction checks |
| 🏫 Medical Colleges | AI-powered teaching tool |

## ✨ Features

- 📋 **Real Patient Cases** — Fetches real patient data from FHIR R4 hospital database
- 🔬 **Lab Results** — Shows actual blood test results and vitals
- 💊 **Drug Interaction Checker** — Checks RxNorm database for dangerous combinations
- 🧠 **AI Tutor** — Powered by Groq AI (Llama 3) for intelligent responses
- ❓ **Clinical Questions** — Socratic teaching method to build reasoning skills
- 🆓 **Completely Free** — No payment required

## 🏗️ Architecture

```
Student asks question
        ↓
Chat UI (index.html)
        ↓
HTTP Bridge (bridge.py) — FastAPI
        ↓              ↓
   Groq AI        MCP Server (server.py)
   (answers)           ↓
                  FHIR Server → Real patient data
                  RxNorm API  → Drug interactions
```

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **MCP** (Model Context Protocol) | Connects AI to real hospital data |
| **FHIR R4** | Real hospital patient data standard |
| **A2A** (Agent to Agent) | AI agent communication |
| **Groq AI** (Llama 3) | Free AI responses |
| **FastAPI** | HTTP bridge server |
| **RxNorm API** | Drug interaction database (NIH) |
| **HAPI FHIR** | Public FHIR sandbox |

## 🚀 Getting Started

**Step 1 — Clone the repo:**
```bash
git clone https://github.com/Rohanindia/medmentor.git
cd medmentor
```

**Step 2 — Install dependencies:**
```bash
pip install fastapi uvicorn httpx groq python-dotenv
```

**Step 3 — Create .env file:**
```
GROQ_API_KEY=gsk_your_key_here
```

**Step 4 — Run the bridge:**
```bash
python bridge.py
```

**Step 5 — Open browser:**
```
http://localhost:8000/app
```

## 📁 Project Structure

```
medmentor/
├── server.py          # MCP Server with 4 FHIR tools
├── bridge.py          # FastAPI HTTP bridge + Groq AI
├── requirements.txt   # Python dependencies
├── .env               # API keys (not on GitHub)
├── .gitignore         # Ignores sensitive files
└── frontend/
    └── index.html     # Chat UI
```

## 🔧 MCP Tools

| Tool | Description | Data Source |
|---|---|---|
| `get_patient_case` | Fetch patient demographics, conditions, medications | HAPI FHIR R4 |
| `get_lab_results` | Get recent blood tests and vitals | HAPI FHIR R4 |
| `get_drug_interactions` | Check dangerous drug combinations | RxNorm (NIH) |
| `get_clinical_question` | Generate Socratic quiz questions | Groq AI |

## 💊 Real Example

```
User: Check drug interactions for warfarin and ibuprofen

MedMentor: ⚠️ [HIGH] Warfarin + Ibuprofen may increase bleeding risk.
           NSAIDs inhibit platelet aggregation which combined with
           anticoagulants raises hemorrhage risk significantly.

           ⚠️ [MODERATE] Ibuprofen may worsen renal function in CKD patients.
```

## 🌍 Real World Impact

- **5 million** medical students in India alone
- **250,000** deaths per year from drug errors globally
- **1.3 billion** people with no access to proper health information

MedMentor is **free**, works in **any browser**, and helps **everyone**.

## 🏆 Hackathon

Built for **Agents Assemble — Healthcare AI Hackathon 2026** by Prompt Opinion · Devpost

Uses all 3 required standards:
- ✅ MCP (Model Context Protocol)
- ✅ A2A (Agent to Agent)
- ✅ FHIR (Fast Healthcare Interoperability Resources)

## 👨‍💻 Developer

**Rohan** — Student Developer from India 🇮🇳

> Building MedMentor to make medical education free and accessible for everyone.

## 📄 License

MIT License — Free to use, modify and share.