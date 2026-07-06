import os
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
from groq import Groq
from auth import register_student, login_student, verify_token, logout_student, get_all_sessions, get_online_count
from admin import (
    admin_login, verify_admin_token,
    get_all_students, toggle_student_active, delete_student, get_admin_stats,
    get_drug_checks,
)
from voice import (
    detect_language,
    translate_to_english,
    translate_to_language,
    get_medical_response_in_language,
    SUPPORTED_LANGUAGES,
)

# ── Setup ──────────────────────────────────────────────────────────────────
app = FastAPI(title="MedMentor Bridge")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GROQ_API_KEY   = os.environ.get("GROQ_API_KEY")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")
groq_client    = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

FHIR_BASE   = "https://hapi.fhir.org/baseR4"
RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"

# ── Models ─────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message        : str
    patient_context: Optional[str] = ""
    history        : Optional[List[dict]] = []
    difficulty     : Optional[str] = "intermediate"
    language       : Optional[str] = "english"   # 'english' | 'hindi' | 'kannada'

class VoiceChatRequest(BaseModel):
    message        : str
    language       : Optional[str] = "english"   # 'english' | 'hindi' | 'kannada'
    patient_context: Optional[str] = ""
    difficulty     : Optional[str] = "intermediate"
    student_id     : Optional[str] = None

class DetectLanguageRequest(BaseModel):
    text: str

class TTSRequest(BaseModel):
    text    : str
    language: Optional[str] = "hindi"   # 'hindi' | 'kannada'
    speaker : Optional[str] = None       # e.g. 'anushka', 'arvind' (Sarvam voices)

class ToolRequest(BaseModel):
    tool     : str
    arguments: Optional[dict] = {}

class RegisterRequest(BaseModel):
    full_name : str
    email     : str
    password  : str
    college   : str
    course    : str

class LoginRequest(BaseModel):
    email    : str
    password : str

class AdminLoginRequest(BaseModel):
    username : str
    password : str

class LogoutRequest(BaseModel):
    session_id : int

# ── Auth Routes ────────────────────────────────────────────────────────────
@app.post("/auth/register")
async def register(req: RegisterRequest):
    return register_student(
        req.full_name, req.email,
        req.password, req.college, req.course
    )

@app.post("/auth/login")
async def login(req: LoginRequest):
    return login_student(req.email, req.password)

@app.get("/auth/verify")
async def verify(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return {"valid": False}
    token   = authorization.split(" ")[1]
    payload = verify_token(token)
    if payload:
        return {"valid": True, "student": payload}
    return {"valid": False}

@app.post("/auth/logout")
async def logout(req: LogoutRequest):
    """Mark session as ended in the database."""
    return logout_student(req.session_id)

# ── Groq AI Chat ───────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    if not groq_client:
        return {"response": "⚠️ Set GROQ_API_KEY to enable AI responses."}

    # If a non-English language is requested, route through the voice pipeline
    lang = (req.language or "english").lower().strip()
    if lang in ("hindi", "kannada"):
        try:
            result = get_medical_response_in_language(
                question=req.message,
                language=lang,
                patient_context=req.patient_context or "",
                difficulty=req.difficulty or "intermediate"
            )
            return {
                "response": result["response"],
                "language": lang,
                "english_question": result.get("english_question", req.message)
            }
        except Exception as e:
            return {"response": f"⚠️ Translation error: {str(e)}"}

    system_prompt = f"""You are MedMentor — a friendly AI clinical tutor for medical students.
You explain complex medical concepts in simple, clear language.
You ask Socratic questions to guide students toward answers rather than giving them directly.
Difficulty level: {req.difficulty}
{"Patient context: " + req.patient_context if req.patient_context else ""}

Keep responses concise and educational. Use emojis occasionally to keep it engaging.
Always end with a follow-up question to deepen learning."""

    messages = [{"role": "system", "content": system_prompt}]

    for h in req.history[-8:]:
        role = "assistant" if h.get("role") == "ai" else "user"
        messages.append({"role": role, "content": str(h.get("content", ""))})

    messages.append({"role": "user", "content": req.message})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "max_tokens": 500,
                    "temperature": 0.7
                }
            )
            data  = r.json()
            reply = data["choices"][0]["message"]["content"]
            return {"response": reply}
    except Exception as e:
        return {"response": f"⚠️ Groq error: {str(e)}"}


# ── Voice / Multilingual Routes ────────────────────────────────────────────────
@app.post("/voice/chat")
async def voice_chat(req: VoiceChatRequest):
    """Multilingual AI chat: translates Hindi/Kannada → English → AI → back to language."""
    lang = (req.language or "english").lower().strip()
    try:
        result = get_medical_response_in_language(
            question=req.message,
            language=lang,
            patient_context=req.patient_context or "",
            difficulty=req.difficulty or "intermediate"
        )
        return {
            "response":          result["response"],
            "language":          result["detected_language"],
            "english_question":  result.get("english_question", req.message),
            "english_response":  result.get("english_response", result["response"]),
        }
    except Exception as e:
        return {"response": f"⚠️ Voice chat error: {str(e)}", "language": lang}


@app.get("/voice/languages")
async def voice_languages():
    """Return list of all supported languages with metadata."""
    return {
        "languages":  SUPPORTED_LANGUAGES,
        "default":    "english",
        "supported":  [lang["code"] for lang in SUPPORTED_LANGUAGES]
    }


@app.post("/voice/detect-language")
async def voice_detect_language(req: DetectLanguageRequest):
    """Detect whether a given text is Hindi, Kannada, or English."""
    detected = detect_language(req.text)
    lang_info = next(
        (lang for lang in SUPPORTED_LANGUAGES if lang["code"] == detected),
        SUPPORTED_LANGUAGES[0]
    )
    return {
        "detected":    detected,
        "language":    lang_info,
        "text_sample": req.text[:50]
    }


@app.post("/voice/tts")
async def voice_tts(req: TTSRequest):
    """
    Sarvam AI Text-to-Speech — returns base64-encoded WAV audio.
    Language: 'hindi' → hi-IN, 'kannada' → kn-IN
    Falls back to {sarvam: false} if API key is not set.
    """
    if not SARVAM_API_KEY:
        return {"success": False, "error": "SARVAM_API_KEY not set", "sarvam": False}

    lang_code_map = {"hindi": "hi-IN", "kannada": "kn-IN", "english": "en-IN"}
    # Default speakers per language — natural sounding Indian voices
    default_speaker = {
        "hindi"  : "anushka",   # female Hindi voice
        "kannada": "anushka",   # female Kannada voice
        "english": "anushka"
    }

    lang     = (req.language or "hindi").lower()
    lang_code = lang_code_map.get(lang, "hi-IN")
    speaker   = req.speaker or default_speaker.get(lang, "anushka")

    # Truncate to 500 chars — Sarvam TTS limit per call
    text = req.text.strip()[:500]
    if not text:
        return {"success": False, "error": "Empty text"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={
                    "api-subscription-key": SARVAM_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "inputs"               : [text],
                    "target_language_code" : lang_code,
                    "speaker"              : speaker,
                    "model"                : "bulbul:v2",
                    "pitch"                : 0,
                    "pace"                 : 1.0,
                    "loudness"             : 1.0,
                    "speech_sample_rate"   : 22050,
                    "enable_preprocessing" : True
                }
            )
            if r.status_code == 200:
                data   = r.json()
                # Sarvam returns base64-encoded WAV in audios[0]
                audio  = data.get("audios", [""])[0]
                return {
                    "success" : True,
                    "audio"   : audio,        # base64 WAV string
                    "format"  : "wav",
                    "language": lang,
                    "speaker" : speaker,
                    "sarvam"  : True
                }
            else:
                return {
                    "success": False,
                    "error"  : f"Sarvam API error {r.status_code}: {r.text[:200]}",
                    "sarvam" : False
                }
    except Exception as e:
        return {"success": False, "error": str(e), "sarvam": False}


@app.get("/voice/tts/status")
async def tts_status():
    """Check if Sarvam TTS is configured."""
    return {
        "sarvam_configured": bool(SARVAM_API_KEY),
        "model"            : "bulbul:v2",
        "languages"        : ["hi-IN", "kn-IN", "en-IN"]
    }


# ── MCP Tool Caller ────────────────────────────────────────────────────────
@app.post("/tool")
async def call_tool(req: ToolRequest):
    tool = req.tool
    args = req.arguments or {}

    if tool == "get_patient_case":
        result = await get_patient_case(args.get("patient_id", "example"))
    elif tool == "get_lab_results":
        result = await get_lab_results(args.get("patient_id", "example"))
    elif tool == "get_drug_interactions":
        result = await get_drug_interactions(args.get("drug_one", "warfarin"), args.get("drug_two", "ibuprofen"))
    elif tool == "get_clinical_question":
        result = generate_clinical_question(args.get("patient_summary", ""), args.get("difficulty", "intermediate"))
    else:
        result = f"Unknown tool: {tool}"

    return {"result": result}

# ── FHIR Tools ─────────────────────────────────────────────────────────────
async def get_patient_case(patient_id: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            if patient_id.lower() == "example":
                pid = "592905"
            else:
                search = await client.get(f"{FHIR_BASE}/Patient?_count=1&_id={patient_id}")
                data   = search.json()
                pid    = data["entry"][0]["resource"]["id"] if data.get("entry") else "592905"

            pr = await client.get(f"{FHIR_BASE}/Patient/{pid}")
            p  = pr.json()
            name   = p.get("name", [{}])[0]
            fname  = " ".join(name.get("given", ["Unknown"]))
            lname  = name.get("family", "")
            gender = p.get("gender", "unknown")
            dob    = p.get("birthDate", "unknown")

            cr = await client.get(f"{FHIR_BASE}/Condition?patient={pid}&_count=5")
            conditions = []
            for e in cr.json().get("entry", []):
                c = e["resource"].get("code", {}).get("text") or \
                    e["resource"].get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
                conditions.append(c)

            mr = await client.get(f"{FHIR_BASE}/MedicationRequest?patient={pid}&_count=5")
            meds = []
            for e in mr.json().get("entry", []):
                m = e["resource"].get("medicationCodeableConcept", {}).get("text") or \
                    e["resource"].get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "Unknown")
                meds.append(m)

            result  = f"**Patient Case**\n"
            result += f"Name: {fname} {lname}\nGender: {gender}\nDOB: {dob}\n\n"
            result += f"**Active Conditions** ({len(conditions)}):\n"
            result += "\n".join(f"  • {c}" for c in conditions) or "  • None found"
            result += f"\n\n**Medications** ({len(meds)}):\n"
            result += "\n".join(f"  • {m}" for m in meds) or "  • None found"
            return result
    except:
        return """**Patient Case** _(FHIR sandbox fallback)_
Name: John Smith
Gender: male
DOB: 1957-04-15

**Active Conditions** (3):
  • Type 2 Diabetes Mellitus
  • Hypertension
  • Chronic Kidney Disease Stage 3

**Medications** (4):
  • Metformin 500mg
  • Lisinopril 10mg
  • Warfarin 5mg
  • Furosemide 40mg"""

async def get_lab_results(patient_id: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            pid = "592905" if patient_id.lower() == "example" else patient_id
            r   = await client.get(f"{FHIR_BASE}/Observation?patient={pid}&category=laboratory&_count=8&_sort=-date")
            labs = []
            for e in r.json().get("entry", []):
                obs  = e["resource"]
                name = obs.get("code", {}).get("text") or obs.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
                val  = obs.get("valueQuantity", {})
                v    = f"{val.get('value', '?')} {val.get('unit', '')}".strip()
                date = obs.get("effectiveDateTime", "")[:10]
                labs.append(f"  • {name}: {v}  [{date}]")
            if labs:
                return "**Lab Results**\n\n" + "\n".join(labs)
            raise Exception("No labs")
    except:
        return """**Lab Results** _(FHIR sandbox fallback)_

  • HbA1c: 8.2 %  [2024-11-01]
  • Serum Creatinine: 2.1 mg/dL  [2024-11-01]
  • eGFR: 38 mL/min/1.73m²  [2024-11-01]
  • Blood Pressure: 148/92 mmHg  [2024-11-01]
  • Potassium: 5.1 mEq/L  [2024-11-01]
  • INR: 2.8  [2024-11-01]"""

async def get_drug_interactions(drug1: str, drug2: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r1 = await client.get(f"{RXNORM_BASE}/rxcui.json?name={drug1}")
            r2 = await client.get(f"{RXNORM_BASE}/rxcui.json?name={drug2}")
            id1 = r1.json().get("idGroup", {}).get("rxnormId", [""])[0]
            id2 = r2.json().get("idGroup", {}).get("rxnormId", [""])[0]
            if id1 and id2:
                ir = await client.get(f"{RXNORM_BASE}/interaction/interaction.json?rxcui={id1}")
                pairs = ir.json().get("interactionTypeGroup", [])
                results = []
                for group in pairs:
                    for itype in group.get("interactionType", []):
                        for pair in itype.get("interactionPair", []):
                            desc = pair.get("description", "")
                            sev  = pair.get("severity", "unknown").upper()
                            results.append(f"  ⚠️  [{sev}] {desc}")
                if results:
                    return f"**Drug Interactions: {drug1.title()} + {drug2.title()}**\n\n" + "\n".join(results[:3])
            raise Exception("No data")
    except:
        d1, d2 = drug1.title(), drug2.title()
        return f"""**Drug Interactions: {d1} + {d2}** _(RxNorm fallback)_

  ⚠️  [HIGH] {d1} and {d2} may increase bleeding risk. NSAIDs inhibit platelet aggregation which combined with anticoagulants raises hemorrhage risk significantly.
  ⚠️  [MODERATE] {d2} may reduce antihypertensive effect and worsen renal function in CKD patients."""

def generate_clinical_question(summary: str, difficulty: str) -> str:
    questions = {
        "beginner"    : "❓ What is the most common symptom of high blood pressure?\n\n_Think about what patients usually complain about._",
        "intermediate": "❓ Given the medication list and lab results, what drug interaction risks should you assess first, and why?\n\n_Think carefully. Consider the full clinical picture._",
        "advanced"    : "❓ This patient has CKD Stage 3 with an INR of 2.8. How would you adjust anticoagulation therapy, and what monitoring parameters would you track?\n\n_Consider renal clearance, bleeding risk, and therapeutic targets._"
    }
    return f"**Clinical Reasoning Question**\n\n{questions.get(difficulty, questions['intermediate'])}"

# ── Admin Auth Guard ──────────────────────────────────────────────────────
def _require_admin(authorization: Optional[str]) -> dict | None:
    """Extract & verify admin JWT. Returns payload or None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return verify_admin_token(authorization.split(" ")[1])

# ── Admin Routes ───────────────────────────────────────────────────────────
@app.post("/admin/login")
async def admin_login_route(req: AdminLoginRequest):
    """Admin login — returns JWT token on success."""
    return admin_login(req.username, req.password)

@app.get("/admin/verify")
async def admin_verify(authorization: Optional[str] = Header(None)):
    """Verify admin JWT token validity."""
    payload = _require_admin(authorization)
    if payload:
        return {"valid": True, "admin": payload}
    return {"valid": False}

@app.get("/admin/stats")
async def admin_stats(authorization: Optional[str] = Header(None)):
    """Dashboard stats: student counts, today/week registrations, drug checks."""
    if not _require_admin(authorization):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return get_admin_stats()

@app.get("/admin/students")
async def admin_students(authorization: Optional[str] = Header(None)):
    """List all registered students with full details."""
    if not _require_admin(authorization):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Admin authentication required")
    students = get_all_students()
    return {"success": True, "students": students, "count": len(students)}

@app.put("/admin/students/{student_id}/toggle")
async def admin_toggle_student(
    student_id: int,
    authorization: Optional[str] = Header(None)
):
    """Activate or deactivate a student account."""
    if not _require_admin(authorization):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return toggle_student_active(student_id)

@app.delete("/admin/students/{student_id}")
async def admin_delete_student(
    student_id: int,
    authorization: Optional[str] = Header(None)
):
    """Permanently delete a student record."""
    if not _require_admin(authorization):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return delete_student(student_id)

@app.get("/admin/drug-checks")
async def admin_drug_checks(authorization: Optional[str] = Header(None)):
    """List all drug interaction checks performed by students."""
    if not _require_admin(authorization):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Admin authentication required")
    checks = get_drug_checks()
    return {"success": True, "checks": checks, "count": len(checks)}

@app.get("/admin/sessions")
async def admin_sessions(authorization: Optional[str] = Header(None)):
    """Return full login/logout session history for all students."""
    if not _require_admin(authorization):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Admin authentication required")
    sessions = get_all_sessions()
    online   = get_online_count()
    return {"success": True, "sessions": sessions, "online_count": online}

# ── Static Files ───────────────────────────────────────────────────────────
try:
    app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
except:
    pass

# ── Root redirect to login ─────────────────────────────────────────────────
@app.get("/")
async def root():
    return RedirectResponse(url="/app/login.html")


# ── Health ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status"  : "ok",
        "groq_ai" : "✅ Connected" if groq_client else "❌ Set GROQ_API_KEY",
        "fhir"    : "✅ hapi.fhir.org",
        "rxnorm"  : "✅ rxnav.nlm.nih.gov",
        "auth"    : "✅ Login system active"
    }

# ── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, uvicorn
    # Ensure UTF-8 output on Windows terminals
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ai_status = "Connected" if groq_client else "Set GROQ_API_KEY first"
    print("\n[MedMentor v6.0] -- With Hindi & Kannada Voice Support")
    print("-" * 54)
    print(f"  Groq AI      : {ai_status}")
    print(f"  Login        : http://localhost:8000/app/login.html")
    print(f"  Chat UI      : http://localhost:8000/app")
    print(f"  Admin Panel  : http://localhost:8000/app/admin.html")
    print(f"  Health       : http://localhost:8000/health")
    print(f"  Voice API    : http://localhost:8000/voice/languages")
    print(f"  Languages    : English | Hindi | Kannada")
    print("-" * 54 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)