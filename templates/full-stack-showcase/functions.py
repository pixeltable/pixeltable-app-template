"""Shared helpers — Gemini response parsing, severity extraction."""

import json
from typing import Any

_EMPTY_ANALYSIS: dict[str, Any] = {
    'description': '',
    'severity': 'INFO',
    'severity_reason': '',
    'ppe_status': 'N_A',
    'ppe_details': '',
    'equipment': [],
    'hazards': [],
}


def gemini_text(val: dict[str, Any] | None) -> str:
    """Extract plain text from a Gemini generate_content response dict."""
    if not val:
        return ''
    try:
        return val['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError, TypeError):
        return str(val)


def parse_segment_analysis(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Parse structured JSON from a Gemini segment_analysis response."""
    text = gemini_text(raw)
    if not text:
        return dict(_EMPTY_ANALYSIS)
    try:
        cleaned = text.strip()
        if '```' in cleaned:
            cleaned = (
                cleaned.split('```json')[-1].split('```')[0]
                if '```json' in cleaned
                else cleaned.split('```')[1].split('```')[0]
            )
        result = json.loads(cleaned.strip())
        result.setdefault('severity', 'INFO')
        return result
    except (json.JSONDecodeError, IndexError):
        sev = 'INFO'
        if 'CRITICAL' in text.upper():
            sev = 'CRITICAL'
        elif 'WARNING' in text.upper():
            sev = 'WARNING'
        return {**_EMPTY_ANALYSIS, 'description': text[:500], 'severity': sev}


def severity_from_analysis(analysis: dict[str, Any] | None) -> str:
    """Normalized severity: 'critical', 'warning', or 'info'."""
    if not analysis:
        return 'info'
    raw = (analysis if isinstance(analysis, dict) else {}).get('severity', 'INFO')
    s = str(raw).strip().upper()
    if 'CRITICAL' in s:
        return 'critical'
    if 'WARNING' in s:
        return 'warning'
    return 'info'
