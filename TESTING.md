# Testing

This repo's automated tests are written with `pytest` and live under `backend/tests/`.

## Run (host)

From the repo root:

```bash
python -m pip install -r backend/requirements-dev.txt
pytest
```

Notes:
- Tests do not require a running Postgres or Ollama by default; network/DB calls are mocked.
- The test suite forces the `anyio` backend to asyncio (the code uses asyncio primitives).

## Run (docker)

If you want to run tests inside the backend container:

```bash
docker compose run --rm backend pytest
```

If `pytest` isn't installed in the image, install dev requirements first:

```bash
docker compose run --rm backend python -m pip install -r requirements-dev.txt
docker compose run --rm backend pytest
```

