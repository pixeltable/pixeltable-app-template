"""Pixeltable Agent — FastAPI application.

Uses pixeltable.serving.FastAPIRouter for Pixeltable-native routes.
Custom endpoints for the ask() flow and conversation listing.
Run: python app.py
"""

from pathlib import Path

import pixeltable as pxt
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pixeltable.serving import FastAPIRouter

import schema

app = FastAPI(title='Pixeltable Agent')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

# ── Pixeltable router ────────────────────────────────────────────────────

router = FastAPIRouter(prefix='/api', tags=['chat-agent'])

router.add_insert_route(
    schema.knowledge,
    path='/knowledge',
    inputs=['text', 'title', 'source'],
    outputs=['uuid'],
)

router.add_query_route(path='/knowledge/search', query=schema.search_knowledge, method='get')
router.add_query_route(path='/memory/search', query=schema.recall_memory, method='get')
router.add_query_route(path='/history', query=schema.get_history, method='get')

app.include_router(router)

# ── Custom endpoints (not expressible as a single insert/query) ──────────


class AskRequest(BaseModel):
    question: str
    conversation_id: str = 'default'


@app.post('/api/ask')
def ask(body: AskRequest):
    try:
        answer = schema.ask(body.question, body.conversation_id)
        return {'answer': answer}
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.get('/api/conversations')
def conversations():
    try:
        t = pxt.get_table('agent.conversations')
        df = t.select(t.conversation_id).group_by(t.conversation_id).collect().to_pandas()
        return {'conversations': df['conversation_id'].tolist()}
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


# ── Static UI ────────────────────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent / 'static'
app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')


@app.get('/')
def index():
    return FileResponse(str(STATIC_DIR / 'index.html'))


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
