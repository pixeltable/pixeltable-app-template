from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import schema

app = FastAPI(title='Pixeltable Agent')

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


def _sanitize(records: list[dict]) -> list[dict]:
    for row in records:
        for k, v in row.items():
            if not isinstance(v, (str, int, float, bool, list, dict, type(None))):
                row[k] = str(v)
    return records


class AskRequest(BaseModel):
    question: str
    conversation_id: str = 'default'


class KnowledgeRequest(BaseModel):
    text: str
    title: str = ''
    source: str = ''


@app.post('/api/ask')
def ask(body: AskRequest):
    try:
        answer = schema.ask(body.question, body.conversation_id)
        return {'answer': answer}
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.get('/api/conversations')
def conversations():
    import pixeltable as pxt

    try:
        t = pxt.get_table('agent.conversations')
        df = t.select(t.conversation_id).group_by(t.conversation_id).collect().to_pandas()
        ids = df['conversation_id'].tolist()
        return {'conversations': ids}
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.get('/api/history')
def history(conversation_id: str = 'default', limit: int = 50):
    try:
        result = schema.get_history(conversation_id, limit)
        records = _sanitize(result.collect().to_pandas().to_dict('records'))
        records.reverse()
        return {'messages': records}
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.post('/api/knowledge')
def add_knowledge(body: KnowledgeRequest):
    try:
        schema.knowledge.insert([{
            'text': body.text,
            'title': body.title,
            'source': body.source,
        }])
        return {'status': 'ok'}
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.get('/api/knowledge/search')
def knowledge_search(q: str = ''):
    try:
        result = schema.search_knowledge(q)
        records = _sanitize(result.collect().to_pandas().to_dict('records'))
        return {'results': records}
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.get('/api/memory/search')
def memory_search(q: str = ''):
    try:
        result = schema.recall_memory(q)
        records = _sanitize(result.collect().to_pandas().to_dict('records'))
        return {'results': records}
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


static_dir = Path(__file__).parent / 'static'
app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')


@app.get('/')
def index():
    return FileResponse(str(static_dir / 'index.html'))


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
