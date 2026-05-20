"""Configuration and Gemini prompts for the full-stack showcase."""

import os

NAMESPACE = "sitewatch"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2-preview")
DETR_MODEL = os.getenv("DETR_MODEL", "facebook/detr-resnet-50-panoptic")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")

FRAME_FPS = 1.0
SEGMENT_DURATION = 10.0
SEGMENT_OVERLAP = 2.0
MIN_SEGMENT_DURATION = 4.0
AUDIO_CHUNK_DURATION = 30.0

UPLOAD_FOLDER = "data"
ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}

CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

VIDEO_SUMMARY_PROMPT = (
    "Analyze this surveillance footage. Provide a structured assessment:\n"
    "1. EQUIPMENT CONDITION: corrosion, overheating, leaks, damaged components\n"
    "2. WORKER SAFETY: PPE compliance, proximity to hazards\n"
    "3. ENVIRONMENTAL HAZARDS: vegetation, water, debris, wildlife\n"
    "4. SECURITY: unauthorized personnel, perimeter integrity\n"
    "5. OVERALL RISK ASSESSMENT: summarize the most urgent finding.\n"
    "Be specific and concise."
)

SEGMENT_ANALYSIS_PROMPT = (
    "Analyze this video segment. "
    "Return ONLY a JSON object (no markdown, no code fences) with this structure:\n"
    "{\n"
    '  "description": "2-3 sentence assessment of what is visible",\n'
    '  "severity": "CRITICAL" or "WARNING" or "INFO",\n'
    '  "severity_reason": "one-line justification",\n'
    '  "ppe_status": "COMPLIANT" or "PARTIAL" or "NON_COMPLIANT" or "N_A",\n'
    '  "ppe_details": "PPE details or N/A if no workers",\n'
    '  "equipment": ["list", "of", "visible", "equipment"],\n'
    '  "hazards": ["list", "of", "identified", "hazards"]\n'
    "}\n\n"
    "Severity criteria:\n"
    "- CRITICAL: fire, smoke, sparking, equipment failure, active safety hazard\n"
    "- WARNING: corrosion, vegetation encroachment, missing PPE, degradation\n"
    "- INFO: normal operations, no issues detected\n\n"
    "Respond with ONLY the JSON object."
)
