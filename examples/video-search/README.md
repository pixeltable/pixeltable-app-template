# Video search

Ingest a video, extract frames at 1 FPS, CLIP-index them, search by text.
This is not what `uvx pixeltable-new` copies. Same apply path as `serving/`.

```bash
cd examples/video-search
uv sync
uv run pxt schema update app.py videointel
uv run pxt service update app.py videointel
uv run pxt service list
```

Foreground: `uv run pxt service run app.py videointel --port 8000`.
`videointel` is a catalog directory, not a folder on disk.

Ingest is a background job (frame extraction is slow). Poll `job_url` from the insert response.

```bash
curl -s -X POST http://localhost:8000/api/ingest \
  -F "video=@/path/to/clip.mp4" \
  -F "title=demo"
# Response includes job_url. Poll it until the frames are indexed.

curl -s -X POST http://localhost:8000/api/search/visual \
  -H "Content-Type: application/json" \
  -d '{"query_text": "a person walking", "limit": 5}'
```

Hosted:

```bash
pxt db update pxt://org:db
pxt schema update app.py pxt://org:db
pxt service update app.py pxt://org:db
```

| Object | Role |
|--------|------|
| `videointel.videos` | Source videos |
| `videointel.frames` | `frame_iterator` at 1 FPS, thumbnail, CLIP index |
| `search_visual` | Text-to-image CLIP search |
