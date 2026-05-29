# Custom Recipes

How to write and register custom reconnaissance recipes.

## Writing a Stage

Every stage implements the `Stage` abstract base class:

```python
from osintote.engine.stage import Stage, StageContext, StageResult

class MyStage(Stage):
    name = "my_stage"

    def execute(self, context: StageContext) -> StageResult:
        # Perform reconnaissance
        data = {"result": "collected_data"}
        return StageResult(
            stage_name=self.name,
            success=True,
            data=data,
        )
```

### StageContext

The context carries state between stages:

```python
@dataclass
class StageContext:
    task_id: UUID
    target: Target
    results: dict[str, Any]  # Accumulated results from previous stages
    metadata: dict[str, Any]  # Shared metadata
```

### StageResult

Each stage returns a result:

```python
@dataclass
class StageResult:
    stage_name: str
    success: bool
    data: dict[str, Any]
    error: str | None = None
    confidence: float = 1.0
```

## Registering a Stage

Add your stage to the registry:

```python
from osintote.engine.stage import STAGE_REGISTRY

STAGE_REGISTRY["my_stage"] = MyStage
```

## Defining a Recipe

Recipes are ordered lists of stage names:

```python
RECIPE_REGISTRY = {
    "custom_full": [
        "dns",
        "http_probe",
        "whois",
        "my_stage",
    ],
}
```

## Best Practices

1. **Idempotency**: Stages should produce the same result when run multiple times
2. **Timeouts**: Use `asyncio.wait_for()` to prevent hanging stages
3. **Error handling**: Return `StageResult(success=False, error="...")` instead of raising exceptions
4. **Resource limits**: Don't open unbounded connections or download unlimited data
5. **Documentation**: Document the expected inputs and outputs in the stage docstring
