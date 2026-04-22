"""
MedMentor MCP Server
====================
Exposes FHIR-based clinical tools for the MedMentor AI tutor agent.
Uses the public HAPI FHIR R4 sandbox (no auth needed for testing).

Tools exposed:
  - get_patient_case     : Fetch a patient with conditions & medications
  - get_lab_results      : Fetch lab observations for a patient
  - get_drug_interactions: Check interactions between two drug names
  - get_clinical_question: Generate a Socratic question from a patient case
"""

import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ── Config ────────────────────────────────────────────────────────────────────
FHIR_BASE = "https://hapi.fhir.org/baseR4"
TIMEOUT    = 15  # seconds

app = Server("medmentor-mcp")

# ── Helper ────────────────────────────────────────────────────────────────────
async def fhir_get(path: str, params: dict = None) -> dict:
    """Make a GET request to the HAPI FHIR sandbox."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        url = f"{FHIR_BASE}/{path}"
        headers = {"Accept": "application/fhir+json"}
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()


def extract_entries(bundle: dict) -> list:
    """Pull resource entries from a FHIR Bundle."""
    return [e["resource"] for e in bundle.get("entry", [])]


# ── Tool 1: get_patient_case ──────────────────────────────────────────────────
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_patient_case",
            description=(
                "Fetch a FHIR patient record including their name, age, gender, "
                "active conditions, and current medications. Use this to create "
                "a clinical case study for a medical student."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "FHIR Patient resource ID (e.g. 'example' for sandbox)"
                    }
                },
                "required": ["patient_id"]
            }
        ),
        types.Tool(
            name="get_lab_results",
            description=(
                "Fetch recent laboratory observations (blood tests, vitals, etc.) "
                "for a given FHIR patient. Returns test name, value, unit, and date."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "FHIR Patient resource ID"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of lab results to return (default 10)",
                        "default": 10
                    }
                },
                "required": ["patient_id"]
            }
        ),
        types.Tool(
            name="get_drug_interactions",
            description=(
                "Check for potential drug-drug interactions between two medications "
                "using the RxNorm / OpenFDA API. Returns interaction warnings if found."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "drug_one": {
                        "type": "string",
                        "description": "First drug name (e.g. 'warfarin')"
                    },
                    "drug_two": {
                        "type": "string",
                        "description": "Second drug name (e.g. 'ibuprofen')"
                    }
                },
                "required": ["drug_one", "drug_two"]
            }
        ),
        types.Tool(
            name="get_clinical_question",
            description=(
                "Generate a Socratic clinical reasoning question based on a patient "
                "summary. Used by the tutor agent to quiz medical students."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_summary": {
                        "type": "string",
                        "description": "A text summary of the patient case"
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "advanced"],
                        "description": "Difficulty level of the question",
                        "default": "intermediate"
                    }
                },
                "required": ["patient_summary"]
            }
        ),
    ]


# ── Tool Handlers ─────────────────────────────────────────────────────────────
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    # ── get_patient_case ──────────────────────────────────────────────────────
    if name == "get_patient_case":
        pid = arguments["patient_id"]

        # Fetch patient demographics
        patient = await fhir_get(f"Patient/{pid}")
        name_block = patient.get("name", [{}])[0]
        full_name = " ".join(
            name_block.get("given", ["Unknown"]) + [name_block.get("family", "")]
        ).strip()
        gender      = patient.get("gender", "unknown")
        birth_date  = patient.get("birthDate", "unknown")

        # Fetch active conditions
        cond_bundle = await fhir_get("Condition", {"patient": pid, "_count": "10"})
        conditions  = []
        for c in extract_entries(cond_bundle):
            code_text = (
                c.get("code", {})
                 .get("text")
                or c.get("code", {})
                   .get("coding", [{}])[0]
                   .get("display", "Unknown condition")
            )
            conditions.append(code_text)

        # Fetch current medications
        med_bundle = await fhir_get("MedicationRequest", {"patient": pid, "_count": "10"})
        medications = []
        for m in extract_entries(med_bundle):
            med_text = (
                m.get("medicationCodeableConcept", {})
                 .get("text")
                or m.get("medicationCodeableConcept", {})
                   .get("coding", [{}])[0]
                   .get("display", "Unknown medication")
            )
            medications.append(med_text)

        result = (
            f"**Patient Case**\n"
            f"Name       : {full_name}\n"
            f"Gender     : {gender}\n"
            f"DOB        : {birth_date}\n\n"
            f"**Active Conditions** ({len(conditions)} found):\n"
            + ("\n".join(f"  • {c}" for c in conditions) if conditions else "  None found")
            + f"\n\n**Current Medications** ({len(medications)} found):\n"
            + ("\n".join(f"  • {m}" for m in medications) if medications else "  None found")
        )
        return [types.TextContent(type="text", text=result)]

    # ── get_lab_results ───────────────────────────────────────────────────────
    elif name == "get_lab_results":
        pid         = arguments["patient_id"]
        max_results = arguments.get("max_results", 10)

        obs_bundle = await fhir_get(
            "Observation",
            {"patient": pid, "category": "laboratory", "_count": str(max_results), "_sort": "-date"}
        )
        entries = extract_entries(obs_bundle)

        if not entries:
            return [types.TextContent(type="text", text="No lab results found for this patient.")]

        lines = ["**Lab Results**\n"]
        for obs in entries:
            test_name = (
                obs.get("code", {}).get("text")
                or obs.get("code", {}).get("coding", [{}])[0].get("display", "Unknown test")
            )
            value     = obs.get("valueQuantity", {})
            val_str   = f"{value.get('value', '?')} {value.get('unit', '')}".strip()
            date      = obs.get("effectiveDateTime", "unknown date")[:10]
            lines.append(f"  • {test_name}: {val_str}  [{date}]")

        return [types.TextContent(type="text", text="\n".join(lines))]

    # ── get_drug_interactions ─────────────────────────────────────────────────
    elif name == "get_drug_interactions":
        drug1 = arguments["drug_one"].lower().strip()
        drug2 = arguments["drug_two"].lower().strip()

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Look up RxCUI for drug 1
            r1 = await client.get(
                f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug1}&search=1"
            )
            r2 = await client.get(
                f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug2}&search=1"
            )

            cui1 = r1.json().get("idGroup", {}).get("rxnormId", [None])[0]
            cui2 = r2.json().get("idGroup", {}).get("rxnormId", [None])[0]

            if not cui1 or not cui2:
                missing = drug1 if not cui1 else drug2
                return [types.TextContent(
                    type="text",
                    text=f"Could not find RxNorm ID for '{missing}'. Check the drug name spelling."
                )]

            # Check interactions
            ix = await client.get(
                f"https://rxnav.nlm.nih.gov/REST/interaction/list.json?rxcuis={cui1}+{cui2}"
            )
            ix_data = ix.json()

        interactions = []
        for group in ix_data.get("fullInteractionTypeGroup", []):
            for itype in group.get("fullInteractionType", []):
                for pair in itype.get("interactionPair", []):
                    desc = pair.get("description", "")
                    sev  = pair.get("severity", "unknown")
                    interactions.append(f"  ⚠️  [{sev.upper()}] {desc}")

        if interactions:
            result = f"**Drug Interactions: {drug1.title()} + {drug2.title()}**\n\n"
            result += "\n".join(interactions)
        else:
            result = f"✅ No known interactions found between **{drug1}** and **{drug2}**."

        return [types.TextContent(type="text", text=result)]

    # ── get_clinical_question ─────────────────────────────────────────────────
    elif name == "get_clinical_question":
        summary    = arguments["patient_summary"]
        difficulty = arguments.get("difficulty", "intermediate")

        # Question templates by difficulty
        templates = {
            "beginner": [
                "What are the most likely diagnoses based on this patient's symptoms?",
                "Which vital signs are abnormal, and what do they suggest?",
                "What is the first-line treatment for the primary condition you identified?",
            ],
            "intermediate": [
                "Given the medication list, what drug interaction risks should you assess first?",
                "Which lab results are most concerning, and why?",
                "How would you prioritize the treatment plan for this patient's multiple conditions?",
            ],
            "advanced": [
                "What is the pathophysiological mechanism linking these comorbidities?",
                "How would you modify the treatment if the patient had renal impairment?",
                "What evidence-based guidelines apply here, and are there any contraindications?",
            ],
        }

        import random
        questions = templates.get(difficulty, templates["intermediate"])
        chosen    = random.choice(questions)

        result = (
            f"**Clinical Reasoning Question** ({difficulty.title()} level)\n\n"
            f"Patient Summary:\n{summary}\n\n"
            f"---\n"
            f"❓ {chosen}\n\n"
            f"_Think carefully before answering. Consider the full clinical picture._"
        )
        return [types.TextContent(type="text", text=result)]

    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
