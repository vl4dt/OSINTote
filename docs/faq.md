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

Or use the API:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{"name": "example.com", "type": "domain"}'
```

### How do I run a task?

Tasks are run through the Web UI or the API. Currently, the pipeline stages (DNS, HTTP, WHOIS) are being developed. Use `bd ready` to check available work items.

### Can I write custom pipeline stages?

Yes. Create a new module that implements the `Stage` abstract base class and register it in the `STAGE_REGISTRY`. See the [Custom Recipes guide](recipes/custom.md).

## Configuration

### How do I change the listen address?

Edit `.osintote/config.json`:

```json
{
  "listen_host": "0.0.0.0",
  "listen_port": 8080
}
```

Or pass CLI flags:

```bash
osintote serve --host 0.0.0.0 --port 8080
```

### How do I configure webhooks?

Use the `--on-complete` flag during initialization, or edit `.osintote/callbacks.json` directly.

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

## Contributing

See [GitHub](https://github.com/vl4dt/OSINTote) for the repository. Use `bd ready` to find available tasks.
