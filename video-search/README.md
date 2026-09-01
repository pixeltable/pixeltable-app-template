# Video search

Ingest a video, extract frames at 1 FPS, CLIP-index them, search by text.
Ingest images for thumbnails and size metadata. One application file (`app.py`).

```bash
cd video-search
uv sync
uv run pxt schema update app.py videointel
uv run pxt service update app.py videointel
uv run pxt service list
```

Foreground: `uv run pxt service run app.py videointel --port 8000`.
Docker Compose keeps 8000: `docker compose up --build`.

Video ingest is a background job (frame extraction is slow). Poll `job_url` from the insert response.

```bash
curl -s -X POST http://localhost:8000/api/ingest \
  -F "video=@/path/to/clip.mp4" \
  -F "title=demo"
# Response includes job_url. Poll it until the frames are indexed.

curl -s -X POST http://localhost:8000/api/ingest/image \
  -F "image=@/path/to/photo.jpg" \
  -F "label=demo" \
  -F "source_id=api-001"

curl -s http://localhost:8000/api/images

curl -s -X POST http://localhost:8000/api/search/visual \
  -H "Content-Type: application/json" \
  -d '{"query_text": "a person walking", "limit": 5}'
```

Cloud:

```bash
pxt db create pxt://org:mydb
pxt schema update app.py pxt://org:mydb
```

`pxt service` stays local. On Cloud, insert from the dashboard.
[Cloud docs](https://docs.pixeltable.com/howto/deployment/cloud).

| Object | Role |
|--------|------|
| `videointel.videos` | Source videos |
| `videointel.frames` | `frame_iterator` at 1 FPS, thumbnail, CLIP index |
| `videointel.images` | Image ingest, thumbnail, width/height |
| `search_visual` | Text-to-image CLIP search |
