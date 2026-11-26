# Local AI companion

PocketLedger keeps accounting and forecasting deterministic. The companion explains a small, explicitly approved financial snapshot using an Ollama model. It cannot change records or move money. Tracking, budgets, forecasts and the assistant's snapshot still work with AI disabled.

## Run on your computer

1. Install [Ollama](https://ollama.com/download) and start it.
2. Download a local model: `ollama pull qwen3:4b`.
3. Set the following environment variables **in the shell that starts Django**, then restart the app. The Docker Compose `.env` file is read by Compose; the local Django process does not automatically read it.

PowerShell:

```powershell
$env:OLLAMA_ENABLED = '1'
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = 'qwen3:4b'
.\.venv\Scripts\python.exe manage.py runserver
```

macOS / Linux:

```bash
OLLAMA_ENABLED=1 OLLAMA_MODEL=qwen3:4b .venv/bin/python manage.py runserver
```

Open **Money companion**. The page checks whether Ollama has the selected model. Preview the financial summary, write a question, and approve sharing it for this request. The model runs on the app server; installing the PWA on a phone does not install a language model on that phone.

## Model and API

The default is [`qwen3:4b`](https://ollama.com/library/qwen3:4b), an Apache-2.0 licensed model with a roughly 2.5 GB quantized download. Runtime memory is higher and depends on context size and hardware. The [original Qwen model card](https://huggingface.co/Qwen/Qwen3-4B) documents its license and capabilities. A smaller `qwen3:1.7b` may suit limited hardware; set `OLLAMA_MODEL` to the exact installed tag. Answers are capped to 750 generated tokens with a 4096-token context.

The integration uses Ollama's [model list](https://docs.ollama.com/api/tags) and [chat API](https://docs.ollama.com/api/chat), with non-streaming output and thinking disabled. `OLLAMA_TIMEOUT` defaults to 45 seconds (bounded to 1–120). The app server's request timeout must be longer; for example, Gunicorn `--timeout 90`. A cold model or CPU-only inference may time out; allow it to load and retry, or select a smaller model.

## Docker

If Ollama runs on the Docker Desktop host, set the web service's `OLLAMA_BASE_URL=http://host.docker.internal:11434` and `OLLAMA_ENABLED=1`. Ollama must listen on an address reachable from the container. For Linux Docker, add `extra_hosts: ["host.docker.internal:host-gateway"]` when using this host address. Alternatively put an Ollama container on the same private Compose network and use `http://ollama:11434`. Keep the Ollama API private; the authenticated Django server is the caller.

## Data handling

- AI is off by default. The page displays server configuration; visitors cannot override the endpoint or model in a request.
- A status check sends no financial data. Asking requires a checked consent field on every submitted request.
- Only the shown aggregates are sent: balance, month-to-date totals, previous full-month expenses, up to five category totals, and forecast totals/assumptions. Account names, individual descriptions, credentials and other users' records are excluded. Category names and anything typed in the question are sent.
- PocketLedger does not persist the question or answer and does not cache the assistant page. Your app host, reverse proxy, and configured model server remain within your trust boundary; configure their logging accordingly.
- The client disables proxy inheritance and refuses HTTP redirects. There is no cloud fallback. Use a locally downloaded model and a trusted endpoint. Ollama also supports [disabling its cloud features](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features).
- Model output is displayed as escaped text. It has no tools, database writes or code execution. Forecasts depend on entered records and assumptions; the model's explanation may still be wrong.

## Verification

`python manage.py test assistant` covers context ownership, opt-in, no-network disabled mode, response escaping, endpoint validation, timeouts, malformed responses and model availability using a mocked server. A live model response additionally requires Ollama and the selected model to be installed.
