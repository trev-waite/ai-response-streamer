# ai-response-streamer
Streams AI responses back through a web socket connection

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install core dependencies (streamer + websocket + Gemini client)
uv sync

# Run the streamer
uv run python src/streamer.py
```

### Local embedding extras

The `embedding/` scripts (local sentence-transformers + faiss embedding) are an
optional extra, since they pull in heavier dependencies like `torch`:

```bash
uv sync --extra embedding
```

**Intel macOS note:** PyTorch stopped publishing Intel macOS wheels after
2.2.2 (Python 3.11 was the last CPython it supports on that platform). If
you're on an Intel Mac, run the embedding extra in its own Python 3.11
environment:

```bash
uv sync --extra embedding --python 3.11
```
