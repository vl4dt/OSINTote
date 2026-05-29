# FAQ

Frequently asked questions about OSINTote.

## General

### What is OSINTote?

OSINTote is a modular Open Source Intelligence (OSINT) collection and analysis platform. It provides a CLI tool, a Web UI, and an extensible pipeline engine for running reconnaissance against targets.

### Is OSINTote free to use?

Yes. OSINTote is released under the [MIT License](../LICENSE).

### Who is OSINTote for?

OSINTote is designed for security researchers, penetration testers, and anyone who needs to systematically collect and analyze open-source intelligence data.

## Installation

### Do I need Node.js?

Only if you want to use the Web UI. The CLI and API work independently of Node.js.

### Can I use OSINTote without a database?

No. OSINTote uses SQLite for data storage. You can specify a custom database path during initialization.

## Usage

### How do I add a new target?

1. Start the web server: `osintote serve`
2. Open `http://127.0.0.1:8000` in your browser
3. Go to the **Targets** page and click **"+ Add Target"**

Or create a task directly via CLI (which auto-creates the target):

```bash
osintote recon start example.com
```

### How do I run a task?

**Via CLI:**

```bash
# Quick scan (DNS + HTTP probe)
osintote recon start example.com

# Full scan (DNS + HTTP + nmap + nuclei)
osintote recon start example.com --recipe full-scan

# Passive only (DNS + WHOIS)
osintote recon start example.com --recipe passive-only
```

**Via Web UI:**

1. Go to the **Tasks** page
2. Click **"+ New Task"**
3. Select a target and recipe
4. Click **Start**

**Via API:**

```bash
# Create a task
curl -X POST http://127.0.0.1:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"target_id": "uuid-here", "name": "my-task", "recipe": "quick-scan"}'

# Start it
curl -X POST http://127.0.0.1:8000/api/tasks/uuid-here/start
```

### Can I write custom pipeline stages?

Yes. Create a new module that implements the `Stage` abstract base class and register it with `@register_stage` or `MyStage.__register__()`. See the [Custom Recipes guide](recipes/custom.md).

### How do I create a custom recipe?

Save a recipe via CLI:

```bash
osintote recipes save custom-scan \
  --description "My custom scan" \
  --stages "dns-enumerate,http-probe,nmap" \
  --depends "http-probe:dns-enumerate,nmap:http-probe"
```

Or define it in code:

```python
from osintote.recipes.models import Recipe, StageDef

my_recipe = Recipe(
    name="custom-scan",
    description="My custom scan",
    stages=[
        StageDef(stage="dns-enumerate", depends_on=[]),
        StageDef(stage="http-probe", depends_on=["dns-enumerate"]),
        StageDef(stage="nmap", depends_on=["http-probe"]),
    ],
)
```

## Configuration

### How do I change the listen address?

```bash
osintote serve --host 0.0.0.0 --port 8080
```

Or edit `.osintote/config.json`:

```json
{
  "listen_host": "0.0.0.0",
  "listen_port": 8080
}
```

### How do I configure webhooks?

**Via CLI:**

```bash
osintote webhook add my-webhook https://example.com/hook \
  --events on_task_complete,on_task_fail,on_critical_finding \
  --secret my-secret-key
```

**Via API:**

```bash
curl -X POST http://127.0.0.1:8000/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{"name": "my-webhook", "url": "https://example.com/hook", "events": ["on_task_complete"], "secret": "my-secret-key"}'
```

### How do I manage API keys?

**Via CLI:**

```bash
# Add a key
osintote api-key add my-shodan shodan SHODAN_KEY --primary

# List keys
osintote api-key list

# Show a key
osintote api-key show KEY_ID

# Rotate primary key
osintote api-key rotate shodan NEW_KEY
```

**Via Web UI:**

Go to **Settings → API Keys** to add, edit, delete, and rotate keys.

## AI Features

### Which AI providers are supported?

OpenAI, Ollama, LMStudio, vLLM, and any OpenAI-compatible endpoint.

### How do I configure AI?

Go to **Settings → AI Configuration** and set the provider type, model name, and API endpoint. Or use the API:

```bash
osintote settings set ai_provider ollama
osintote settings set ai_model llama3
osintote settings set ai_endpoint http://localhost:11434
```

### Can I use AI to query results?

Yes. The `/api/ai/query` endpoint converts natural language to a structured query:

```bash
curl -X POST http://127.0.0.1:8000/api/ai/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show critical vulnerabilities", "use_ai": true}'
```

## Troubleshooting

### The Web UI doesn't load

1. Make sure the dev server is running: `make dev`
2. Check that `frontend/` has `node_modules/` installed
3. Verify you're visiting `http://localhost:5173` (dev) or `http://127.0.0.1:8000` (production)

### Tests are failing

1. Run `make init` to ensure the virtual environment is set up
2. Check that `uv.lock` is up to date: `uv lock`
3. Verify the editable install is working: `uv run python -c "import osintote; print(osintote.__version__)"`

### Database migration errors

1. Delete the database file and re-initialize:
   ```bash
   rm osintote.db
   osintote init --force
   ```

### External tools not found (nmap, nuclei, subfinder)

Install the required tools:

```bash
# nmap
sudo apt install nmap

# nuclei
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# subfinder
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
```

## Contributing

See [GitHub](https://github.com/vl4dt/OSINTote) for the repository. All tasks are completed (52/52). Feature requests and bugs should be filed as issues.
