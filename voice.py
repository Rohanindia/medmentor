"""
voice.py — Hindi & Kannada Voice/Language Support for MedMentor
Uses Google Translate (free, via deep-translator) for translation.
Groq is used ONLY for the AI medical response — saves ~66% of tokens.
"""

import os
import re
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()

# Groq is now only used for the AI medical answer, NOT for translation
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

try:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except ImportError:
    groq_client = None

# ── Language code mapping ─────────────────────────────────────────────────────
# Maps our internal language names → Google Translate language codes
LANG_CODES = {
    "hindi"  : "hi",
    "kannada": "kn",
    "english": "en",
}

# ── Indian Medical Vocabulary (slang → standard terms) ────────────────────────
# Pre-processes colloquial Indian medical terms before translation / AI
INDIAN_MEDICAL_VOCAB = {
    # Hindi/Hinglish slang → standard medical terms
    "sugar":            "diabetes mellitus",
    "sugar ki bimari":  "diabetes mellitus",
    "madhumeh":         "diabetes mellitus",
    "BP":               "hypertension (blood pressure)",
    "high BP":          "hypertension",
    "low BP":           "hypotension",
    "TB":               "tuberculosis",
    "tapedik":          "tuberculosis",
    "report":           "diagnostic findings / investigation report",
    "saline":           "intravenous (IV) fluids / normal saline",
    "drip":             "intravenous infusion",
    "thakaan":          "fatigue / weakness",
    "dard":             "pain",
    "bukhar":           "fever / pyrexia",
    "khoon":            "blood / haemoglobin",
    "khoon ki kami":    "anaemia",
    "dil":              "heart / cardiac",
    "dil ka dora":      "cardiac arrest / heart attack",
    "dawai":            "medication / medicine",
    "peshab":           "urine / urination",
    "pet dard":         "abdominal pain",
    "chakkar":          "dizziness / vertigo",
    "sans":             "breathing / respiration",
    "khasi":            "cough",
    "nali":             "catheter / tube",
    "pathar":           "renal calculi / kidney stone",

    # Kannada slang → standard terms
    "sakkare":          "diabetes mellitus",
    "madhumeha":        "diabetes mellitus",
    "rakta":            "blood / haemoglobin",
    "rakta heenatve":   "anaemia",
    "jvara":            "fever / pyrexia",
    "vedane":           "pain",
    "shrama":           "fatigue",
    "kashe":            "cough",
    "soru":             "fatigue / weakness",
    "hrudaya":          "heart / cardiac",
    "mutru":            "urine",
    "hotte":            "abdomen / stomach",
    "tarala":           "fluid / liquid",
    "oshadha":          "medicine / medication",

    # Common Indian abbreviations
    "HB":   "haemoglobin",
    "Hb":   "haemoglobin",
    "RBS":  "random blood sugar",
    "FBS":  "fasting blood sugar",
    "PPBS": "post-prandial blood sugar",
    "ECG":  "electrocardiogram",
    "USG":  "ultrasound",
    "OPD":  "outpatient department",
    "IPD":  "inpatient department",
    "ICU":  "intensive care unit",
    "NICU": "neonatal intensive care unit",
    "OT":   "operation theatre / surgical suite",
}


# ── Language Detection ────────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    """
    Detect if text is Hindi, Kannada, or English using Unicode range detection.
    Hindi   Unicode range: U+0900–U+097F (Devanagari)
    Kannada Unicode range: U+0C80–U+0CFF
    Returns: 'hindi' | 'kannada' | 'english'
    """
    if not text or not text.strip():
        return "english"

    hindi_chars   = len(re.findall(r'[\u0900-\u097F]', text))
    kannada_chars = len(re.findall(r'[\u0C80-\u0CFF]', text))
    total_chars   = len(text.replace(' ', ''))

    if total_chars == 0:
        return "english"

    if (hindi_chars   / total_chars) > 0.15:
        return "hindi"
    if (kannada_chars / total_chars) > 0.15:
        return "kannada"
    return "english"


# ── Indian Medical Vocabulary Pre-Processor ───────────────────────────────────
def preprocess_indian_medical_terms(text: str) -> str:
    """
    Replace Indian medical slang with standard medical terminology
    before translation / AI processing.
    """
    result = text
    for slang, standard in INDIAN_MEDICAL_VOCAB.items():
        pattern = r'(?<!\w)' + re.escape(slang) + r'(?!\w)'
        result  = re.sub(pattern, standard, result, flags=re.IGNORECASE)
    return result


# ── Google Translate Helpers ──────────────────────────────────────────────────
def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translate Hindi or Kannada text → English using Google Translate (FREE).
    Falls back to original text on any error.
    """
    if source_lang == "english" or not text.strip():
        return text

    gt_code = LANG_CODES.get(source_lang, "auto")
    try:
        translated = GoogleTranslator(source=gt_code, target="en").translate(text)
        return translated or text
    except Exception as e:
        print(f"[voice] Google Translate (→en) error: {e}")
        return text


def translate_to_language(text: str, target_lang: str) -> str:
    """
    Translate English medical explanation → Hindi or Kannada using
    Google Translate (FREE). Falls back to original text on any error.
    """
    if target_lang == "english" or not text.strip():
        return text

    gt_code = LANG_CODES.get(target_lang)
    if not gt_code:
        return text

    try:
        # Google Translate has a ~5000 char limit per call — split if needed
        if len(text) <= 4500:
            translated = GoogleTranslator(source="en", target=gt_code).translate(text)
            return translated or text

        # Split on sentence boundaries and translate in chunks
        sentences  = re.split(r'(?<=[.!?])\s+', text)
        chunks, current = [], ""
        for s in sentences:
            if len(current) + len(s) < 4000:
                current += s + " "
            else:
                chunks.append(current.strip())
                current = s + " "
        if current.strip():
            chunks.append(current.strip())

        parts = []
        for chunk in chunks:
            try:
                t = GoogleTranslator(source="en", target=gt_code).translate(chunk)
                parts.append(t or chunk)
            except Exception:
                parts.append(chunk)
        return " ".join(parts)

    except Exception as e:
        print(f"[voice] Google Translate (→{target_lang}) error: {e}")
        return text


# ── Main Multilingual Response Pipeline ───────────────────────────────────────
def get_medical_response_in_language(
    question      : str,
    language      : str,
    patient_context: str = "",
    difficulty    : str  = "intermediate"
) -> dict:
    """
    Full multilingual pipeline — now Groq is called ONLY ONCE (for AI answer):

    1. Pre-process Indian medical slang
    2. Google Translate: question → English          (FREE)
    3. Groq AI: English question → English answer    (1 token call)
    4. Google Translate: answer → Hindi/Kannada      (FREE)

    Returns dict: response, detected_language, english_question, english_response
    """
    if not groq_client:
        return {
            "response"         : "⚠️ Set GROQ_API_KEY to enable AI responses.",
            "detected_language": language,
            "english_question" : question,
            "english_response" : ""
        }

    # Step 1: Pre-process Indian medical slang
    processed = preprocess_indian_medical_terms(question)

    # Step 2: Auto-detect language if not explicitly set
    if language == "auto":
        language = detect_language(question)

    # Step 3: Google Translate → English (FREE, no Groq token used)
    english_question = translate_to_english(processed, language)
    print(f"[voice] [{language}] Q translated: {english_question[:80]}...")

    # Step 4: Groq AI — English answer only (single token call)
    system_prompt = f"""You are MedMentor — a friendly AI clinical tutor for medical students.
You explain complex medical concepts in simple, clear language.
You use the Socratic method — ask one follow-up question at the end to deepen learning.
Difficulty level: {difficulty}
{("Patient context: " + patient_context) if patient_context else ""}

Keep responses concise and educational. Use emojis occasionally.
Always end with ONE follow-up question."""

    try:
        ai_resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": english_question}
            ],
            max_tokens=500,
            temperature=0.7
        )
        english_response = ai_resp.choices[0].message.content.strip()
        print(f"[voice] AI answered ({len(english_response)} chars)")
    except Exception as e:
        english_response = f"I apologize, I encountered an error: {str(e)}"

    # Step 5: Google Translate → target language (FREE, no Groq token used)
    final_response = translate_to_language(english_response, language)
    print(f"[voice] Response translated to {language} ({len(final_response)} chars)")

    return {
        "response"         : final_response,
        "english_response" : english_response,
        "detected_language": language,
        "english_question" : english_question
    }


# ── Supported Languages Info ───────────────────────────────────────────────────
SUPPORTED_LANGUAGES = [
    {
        "code"       : "english",
        "name"       : "English",
        "native_name": "English",
        "flag"       : "🇬🇧",
        "speech_lang": "en-US",
        "gt_code"    : "en",
        "welcome"    : "Hello! I am MedMentor — your AI Clinical Tutor. Ask me anything about medicine! 🩺"
    },
    {
        "code"       : "hindi",
        "name"       : "Hindi",
        "native_name": "हिंदी",
        "flag"       : "🇮🇳",
        "speech_lang": "hi-IN",
        "gt_code"    : "hi",
        "welcome"    : "नमस्ते! मैं MedMentor हूं — आपका AI क्लिनिकल ट्यूटर। आप हिंदी में प्रश्न पूछ सकते हैं। 🩺"
    },
    {
        "code"       : "kannada",
        "name"       : "Kannada",
        "native_name": "ಕನ್ನಡ",
        "flag"       : "🇮🇳",
        "speech_lang": "kn-IN",
        "gt_code"    : "kn",
        "welcome"    : "ನಮಸ್ಕಾರ! ನಾನು MedMentor — ನಿಮ್ಮ AI ಕ್ಲಿನಿಕಲ್ ಟ್ಯೂಟರ್. ನೀವು ಕನ್ನಡದಲ್ಲಿ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಬಹುದು. 🩺"
    }
]
