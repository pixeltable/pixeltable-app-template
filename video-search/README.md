# Video search

Ingest a video, extract frames at 1 FPS, CLIP-index them, search by text.
Ingest images for thumbnails and size metadata. One application file (`app.py`).
Declare (`pxt schema update app.py videointel`), Experiment (insert, search, `pxt dashboard`), Serve (`pxt service update`).
Advertised order is schema, then service, then insert.

```bash
cd video-search
uv sync
uv run pxt schema update app.py videointel
uv run pxt service update app.py videointel
uv run pxt service list
```

Video ingest is a background job (frame extraction is slow). Poll `job_url` from the insert response.
`pxt service list` prints the port.

```bash
curl -s -X POST http://127.0.0.1:<port>/api/ingest \
  -F "video=@/path/to/clip.mp4" \
  -F "title=demo"
# Response includes job_url. Poll it until the frames are indexed.

curl -s -X POST http://127.0.0.1:<port>/api/ingest/image \
  -F "image=@/path/to/photo.jpg" \
  -F "label=demo" \
  -F "source_id=api-001"

curl -s http://127.0.0.1:<port>/api/images

curl -s -X POST http://127.0.0.1:<port>/api/search/visual \
  -H "Content-Type: application/json" \
  -d '{"query_text": "a person walking", "limit": 5}'
```

## Same file, hosted

```bash
uv run pxt db update pxt://org:mydb
uv run pxt schema update app.py pxt://org:mydb
uv run pxt service update app.py pxt://org:mydb
```

`pxt db update` packs the hosted image and workers; it is not Experiment.
`pxt service run` is local only. Experiment on Cloud is dashboard insert plus `pxt schema diff`.
[Cloud docs](https://docs.pixeltable.com/howto/deployment/cloud).

## Foreground and container

`uv run pxt service run app.py videointel --port 8000` stays in this terminal.
`docker compose up --build` pins port 8000.

| Object | Role |
|--------|------|
| `videointel.videos` | Source videos |
| `videointel.frames` | `frame_iterator` at 1 FPS, thumbnail, CLIP index |
| `videointel.images` | Image ingest, thumbnail, width/height |
| `search_visual` | Text-to-image CLIP search |
