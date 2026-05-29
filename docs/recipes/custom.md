# Custom Recipes

How to write and register custom reconnaissance stages and recipes.

## Writing a Stage

Every stage implements the `Stage` abstract base class:

```python
from osintote.engine.stage import Stage, StageContext, StageResult

class MyStage(Stage):
    name = "my_stage"
    cost = "light"  # light | medium | heavy

    def execute(self, ctx: StageContext) -> StageResult:
        # Perform reconnaissance
        data = {"result": "collected_data"}
        return StageResult(
            success=True,
            data=data,
            records_count=1,
            message="Stage completed",
        )
```

### Stage Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Unique identifier (lowercase, e.g. `"dns"`, `"http_probe"`) |
| `cost` | `str` | Resource cost tier — `"light"`, `"medium"`, `"heavy"` |
| `retry_on` | `frozenset[str]` | Error sub-string prefixes that trigger retry |
| `timeout_s` | `float` | Per-attempt timeout in seconds (0 = unlimited) |

### StageResult Fields

Each stage returns a `StageResult`:

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether the stage completed without error |
| `data` | `Any` | Arbitrary payload (dict, list, scalar) |
| `records_count` | `int` | Number of data records produced |
| `message` | `str \| None` | Human-readable status message |
| `error` | `str \| None` | Error message if failed |
| `elapsed_ms` | `int` | Execution time in milliseconds |

Use the helper methods for convenience:

```python
return StageResult.success(data={"key": "value"})
# or
return StageResult.failure(error="Something went wrong")
```

### StageContext

The context carries state between stages and provides database access:

```python
ctx.target_name      # str — Name of the target being investigated
ctx.target_id         # UUID — Database UUID of the target
ctx.task_id           # UUID — Database UUID of the task
ctx.task_status       # TaskStatus — Current lifecycle status
ctx.config            # EngineConfig — Engine config snapshot (frozen at task start)
ctx.findings          # dict — Shared dictionary; stages append results here
ctx.records           # list — Accumulated records produced by all stages
ctx.errors            # list — Accumulated errors produced by all stages
ctx.metadata_         # dict — General-purpose key-value store for cross-stage data
```

### Timeout Handling

Stages support automatic timeout via the `timeout_s` attribute. If the stage exceeds the timeout, it returns a failure result without raising.

```python
class SlowStage(Stage):
    name = "slow_stage"
    timeout_s = 30.0  # 30 second timeout
```

## Registering a Stage

Stages are auto-registered using the `@register_stage` decorator or `__register__()`:

```python
from osintote.engine.stage import register_stage

@register_stage
class MyCustom(Stage):
    name = "my_custom"

    def execute(self, ctx: StageContext) -> StageResult:
        return StageResult.success(data={"result": "collected_data"})
```

Or using the class method:

```python
class MyCustom(Stage):
    name = "my_custom"

    def execute(self, ctx: StageContext) -> StageResult:
        return StageResult.success(data={"result": "collected_data"})

MyCustom.__register__()
```

After registration, the stage is available in `STAGE_REGISTRY` and can be referenced in recipes.

## Defining a Recipe

Recipes are defined as `Recipe` objects with `StageDef` entries:

```python
from osintote.engine.config import DEFAULT_RECIPES
from osintote.recipes.models import Recipe, StageDef

my_recipe = Recipe(
    name="custom-full",
    description="Custom deep scan",
    stages=[
        StageDef(stage="dns-enumerate", depends_on=[]),
        StageDef(stage="http-probe", depends_on=["dns-enumerate"]),
        StageDef(stage="nmap", depends_on=["http-probe"]),
        StageDef(stage="my_custom", depends_on=["http-probe"]),
    ],
)
```

### Recipe Serialization

Recipes can be saved as JSON:

```python
recipe_json = my_recipe.to_dict()
# {
#   "name": "custom-full",
#   "description": "Custom deep scan",
#   "stages": [
#     {"stage": "dns-enumerate", "params": null, "depends_on": []},
#     {"stage": "http-probe", "params": null, "depends_on": ["dns-enumerate"]},
#     ...
#   ]
# }
```

### Recipe Loader

Recipes are loaded in priority order:

1. **User overrides** in `.osintote/recipes/*.json`
2. **Bundled defaults** from `osintote/recipes/models.py` (`DEFAULT_RECIPES`)

```python
from osintote.recipes.models import RecipeLoader
from pathlib import Path

loader = RecipeLoader(project_root=Path.cwd())
recipe = loader.get_recipe("custom-full")
all_recipes = loader.list_recipes()
```

## Best Practices

1. **Idempotency**: Stages should produce the same result when run multiple times
2. **Timeouts**: Set `timeout_s` on stages that may hang
3. **Error handling**: Return `StageResult(success=False, error="...")` instead of raising exceptions
4. **Resource limits**: Don't open unbounded connections or download unlimited data
5. **Documentation**: Document the expected inputs and outputs in the stage docstring
6. **Cost classification**: Use `"light"` for fast stages, `"medium"` for moderate, `"heavy"` for CPU-bound
7. **Stage naming**: Use lowercase with hyphens (e.g., `"my-custom-stage"`)

## Recipe CLI

User recipes can be managed via CLI:

```bash
# Save a new recipe
osintote recipes save my-recipe \
  --description "My custom scan" \
  --stages "dns-enumerate,http-probe,nmap" \
  --depends "http-probe:dns-enumerate,nmap:http-probe"

# List all recipes
osintote recipes list

# Show a recipe
osintote recipes show my-recipe

# Delete a user recipe
osintote recipes delete my-recipe
```
