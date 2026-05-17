"""Audio Intelligence — FastAPI application."""

import os
from pathlib import Path

import pixeltable as pxt
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import schema

app = FastAPI(title='Audio Intelligence')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

UPLOAD_DIR = Path(__file__).parent / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)
STATIC_DIR = Path(__file__).parent / 'static'

app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')

ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}


def _serialize_records(df_records: list[dict]) -> list[dict]:
    serialized = []
    for row in df_records:
        serialized.append({k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for k, v in row.items()})
    return serialized


class SearchBody(BaseModel):
    query: str
    limit: int = 10


class SearchInBody(BaseModel):
    title: str
    query: str
    limit: int = 10


@app.get('/')
async def index():
    return FileResponse(str(STATIC_DIR / 'index.html'))


@app.post('/api/upload')
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f'Unsupported file type: {ext}')

    title = Path(file.filename).stem
    save_path = UPLOAD_DIR / file.filename
    content = await file.read()
    save_path.write_bytes(content)

    schema.audio_files.insert([{'audio': str(save_path), 'title': title, 'source': 'upload'}])
    return {'status': 'ok', 'title': title}


@app.get('/api/recordings')
async def recordings():
    result = schema.list_recordings()
    records = _serialize_records(result.collect().to_pandas().to_dict('records'))
    return {'recordings': records}


@app.get('/api/transcript')
async def transcript(title: str):
    result = schema.get_transcript(title)
    records = _serialize_records(result.collect().to_pandas().to_dict('records'))
    return {'segments': records}


@app.get('/api/summary')
async def summary(title: str):
    result = schema.get_summary(title)
    records = _serialize_records(result.collect().to_pandas().to_dict('records'))
    return {'segments': records}


@app.post('/api/search')
async def search(body: SearchBody):
    result = schema.search_transcripts(body.query, body.limit)
    records = _serialize_records(result.collect().to_pandas().to_dict('records'))
    return {'results': records}


@app.post('/api/search-in')
async def search_in(body: SearchInBody):
    result = schema.search_in_recording(body.title, body.query, body.limit)
    records = _serialize_records(result.collect().to_pandas().to_dict('records'))
    return {'results': records}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
