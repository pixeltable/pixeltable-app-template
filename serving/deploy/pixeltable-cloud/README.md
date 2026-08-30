# Pixeltable Cloud

Apply the same application file to a hosted catalog.

```bash
pxt db update pxt://org:mydb
pxt schema update app.py pxt://org:mydb
pxt service update app.py pxt://org:mydb
```

`PIXELTABLE_API_KEY` is required. Set it in the environment or in config. See [Deploy to Pixeltable Cloud](https://docs.pixeltable.com/howto/deployment/cloud).

`pxt service run` stays on this machine. Hosted HTTP is `pxt service update` against the `pxt://` URI.

## Local HTTP

```bash
pxt schema update app.py pipeline
pxt service update app.py pipeline
pxt service list
```

Or foreground: `pxt service run app.py pipeline --port 8000`.

## What you write

The application file (`app.py`) holds `TableModel` classes and a `FastAPIRouter`. `pixeltable.toml` is the project root:

```toml
[[pixeltable.database]]
```

Do not put routes in TOML. Routes live on the router in `app.py`.

## Local vs Cloud

| | Local | Cloud |
|---|---|---|
| Catalog | `pxt schema update app.py pipeline` | `pxt schema update app.py pxt://org:mydb` |
| HTTP | `pxt service update` / `pxt service run` | `pxt service update app.py pxt://org:mydb` |
| Media | local disk | `pxtfs://org:mydb/home` |

## See Also

- [`serving/`](../../): application file + `pxt service`
- [HTTP serving](https://docs.pixeltable.com/howto/deployment/serving)
- [Cloud](https://docs.pixeltable.com/howto/deployment/cloud)
