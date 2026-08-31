# Examples

Same apply path as `serving/`: the application file (`app.py`), then `pxt schema update`, then `pxt service`.
`uvx pixeltable-new` does not copy these folders. Cloud reads them from [`gallery.json`](../gallery.json).

Cloud is `pxt schema update app.py pxt://org:db`. `pxt service` stays local.

| Folder | Catalog TARGET | What it adds beyond `serving/` |
|--------|----------------|--------------------------------|
| [`video-search/`](video-search/) | `videointel` | `frame_iterator` + CLIP visual search. Video ingest is `background=True`. |
| [`chat-agent/`](chat-agent/) | `agent` | Query functions as computed columns. Knowledge + memory + Anthropic answer. |

Do not add a second apply path. Do not put routes in TOML.
