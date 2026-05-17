import base64
import io
from pathlib import Path

import pixeltable as pxt
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import schema

UPLOAD_DIR = Path('uploads')
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title='Multimodal RAG')

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

DOCUMENT_EXTS = {'.pdf', '.docx', '.txt', '.md'}
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.webm'}
AUDIO_EXTS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}


def _detect_type(filename: str) -> tuple[str, str]:
    ext = Path(filename).suffix.lower()
    if ext in DOCUMENT_EXTS:
        return 'document', ext
    if ext in IMAGE_EXTS:
        return 'image', ext
    if ext in VIDEO_EXTS:
        return 'video', ext
    if ext in AUDIO_EXTS:
        return 'audio', ext
    raise ValueError(f'Unsupported file type: {ext}')


def _serialize_value(v):
    try:
        from PIL import Image as PILImage
        if isinstance(v, PILImage.Image):
            buf = io.BytesIO()
            fmt = 'PNG' if v.mode == 'RGBA' else 'JPEG'
            v.save(buf, format=fmt)
            b64 = base64.b64encode(buf.getvalue()).decode()
            mime = 'image/png' if fmt == 'PNG' else 'image/jpeg'
            return f'data:{mime};base64,{b64}'
    except ImportError:
        pass
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, bytes):
        return base64.b64encode(v).decode()
    return v


def _serialize_row(row: dict) -> dict:
    return {k: _serialize_value(v) for k, v in row.items()}


class SearchRequest(BaseModel):
    query: str
    n: int = 5


class AskRequest(BaseModel):
    question: str


@app.post('/api/upload')
def upload_file(file: UploadFile = File(...)):
    try:
        file_type, ext = _detect_type(file.filename)
    except ValueError as exc:
        return {'status': 'error', 'message': str(exc)}

    save_path = UPLOAD_DIR / file.filename
    save_path.write_bytes(file.file.read())
    saved = str(save_path.resolve())

    if file_type == 'document':
        schema.documents.insert([{'doc': saved}])
    elif file_type == 'image':
        schema.images.insert([{'image': saved, 'caption': file.filename}])
    elif file_type == 'video':
        schema.videos.insert([{'video': saved}])
    elif file_type == 'audio':
        schema.audio_files.insert([{'audio': saved}])

    return {'status': 'ok', 'type': file_type, 'filename': file.filename}


@app.post('/api/search')
def search(req: SearchRequest):
    results = schema.search_knowledge(req.query, req.n)
    return {'results': [_serialize_row(r) for r in results]}


@app.post('/api/ask')
def ask(req: AskRequest):
    result = schema.ask_question(req.question)
    if 'context' in result and isinstance(result['context'], list):
        result['context'] = [_serialize_row(c) if isinstance(c, dict) else c for c in result['context']]
    return result


@app.get('/api/stats')
def stats():
    return {
        'documents': schema.documents.count(),
        'images': schema.images.count(),
        'videos': schema.videos.count(),
        'audio': schema.audio_files.count(),
    }


app.mount('/static', StaticFiles(directory='static'), name='static')


@app.get('/')
def index():
    return FileResponse('static/index.html')


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
