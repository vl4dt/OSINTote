# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Recipe system — JSON recipe config with stage definitions.

Recipes define ordered, named pipelines of stages to execute.
Each recipe has:
    - name, description
    - stages array (ordered by depends_on)
    - per-stage config (stage name + parameters)

Recipe lookup order:
    1. User overrides in .osintote/recipes/
    2. Bundled defaults in osintote/recipes/
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StageDef:
    """Definition of a single stage within a recipe.

    Attributes
    ----------
    stage:
        Registry key (e.g., "dns-enumerate", "http-probe").
    params:
        Stage-specific parameters (may be None).
    depends_on:
        Stage names that must complete before this stage runs.
    """

    def __init__(
        self,
        stage: str,
        params: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
    ) -> None:
        self.stage = stage
        self.params = params or {}
        self.depends_on = depends_on or []


class Recipe:
    """A recipe definition — ordered pipeline of stages.

    Attributes
    ----------
    name:
        Recipe identifier (e.g., "full-scan").
    description:
        Human-readable description.
    stages:
        Ordered list of StageDef objects.
    """

    def __init__(
        self,
        name: str,
        description: str,
        stages: list[StageDef],
    ) -> None:
        self.name = name
        self.description = description
        self.stages = stages

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Recipe:
        """Construct a Recipe from a JSON dict."""
        stages = [
            StageDef(
                stage=s["stage"],
                params=s.get("params"),
                depends_on=s.get("depends_on"),
            )
            for s in data.get("stages", [])
        ]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            stages=stages,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize recipe to a JSON-safe dict."""
        return {
            "name": self.name,
            "description": self.description,
            "stages": [
                {
                    "stage": s.stage,
                    "params": s.params,
                    "depends_on": s.depends_on,
                }
                for s in self.stages
            ],
        }

    def ordered_stages(self) -> list[StageDef]:
        """Return stages in topological order (respecting depends_on)."""
        stage_map: dict[str, StageDef] = {s.stage: s for s in self.stages}
        visited: set[str] = set()
        result: list[StageDef] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            stage = stage_map.get(name)
            if stage is None:
                return
            for dep in stage.depends_on:
                visit(dep)
            visited.add(name)
            result.append(stage)

        for s in self.stages:
            visit(s.stage)

        return result


# ── Default Bundled Recipes ──────────────────────────────────────────────────


DEFAULT_RECIPES: dict[str, Recipe] = {
    "quick-scan": Recipe(
        name="quick-scan",
        description="Quick reconnaissance: DNS + HTTP probe",
        stages=[
            StageDef(stage="dns-enumerate", depends_on=[]),
            StageDef(stage="http-probe", depends_on=["dns-enumerate"]),
        ],
    ),
    "full-scan": Recipe(
        name="full-scan",
        description="Full recon: DNS → HTTP → nmap → nuclei",
        stages=[
            StageDef(stage="dns-enumerate", depends_on=[]),
            StageDef(stage="http-probe", depends_on=["dns-enumerate"]),
            StageDef(stage="nmap", depends_on=["http-probe"]),
            StageDef(stage="nuclei", depends_on=["nmap"]),
        ],
    ),
    "passive-only": Recipe(
        name="passive-only",
        description="Passive reconnaissance only: DNS + WHOIS",
        stages=[
            StageDef(stage="dns-enumerate", depends_on=[]),
            StageDef(stage="whois", depends_on=[]),
        ],
    ),
}


# ── Recipe Loader ────────────────────────────────────────────────────────────


class RecipeLoader:
    """Load recipes from bundled defaults and user overrides.

    Lookup order:
        1. User overrides in .osintote/recipes/
        2. Bundled defaults in osintote/recipes/
    """

    def __init__(self, project_root: Path | None = None) -> None:
        self._recipes: dict[str, Recipe] = {}
        self._load_defaults()
        if project_root is not None:
            self._load_user_overrides(project_root)

    def _load_defaults(self) -> None:
        """Load bundled default recipes."""
        for name, recipe in DEFAULT_RECIPES.items():
            self._recipes[name] = recipe

    def _load_user_overrides(self, project_root: Path) -> None:
        """Load user override recipes from .osintote/recipes/."""
        recipe_dir = project_root / ".osintote" / "recipes"
        if not recipe_dir.is_dir():
            return

        for recipe_file in recipe_dir.glob("*.json"):
            try:
                data = json.loads(recipe_file.read_text(encoding="utf-8"))
                recipe = Recipe.from_dict(data)
                self._recipes[recipe.name] = recipe
                logger.info("Loaded user recipe: %s", recipe.name)
            except Exception as e:
                logger.warning("Failed to load recipe %s: %s", recipe_file.name, e)

    def get_recipe(self, name: str) -> Recipe | None:
        """Get a recipe by name (user override takes precedence)."""
        return self._recipes.get(name)

    def list_recipes(self) -> list[Recipe]:
        """List all available recipes."""
        return list(self._recipes.values())

    def save_recipe(self, recipe: Recipe, project_root: Path) -> None:
        """Save a recipe to .osintote/recipes/ (creates user override)."""
        recipe_dir = project_root / ".osintote" / "recipes"
        recipe_dir.mkdir(parents=True, exist_ok=True)
        recipe_file = recipe_dir / f"{recipe.name}.json"
        recipe_file.write_text(
            json.dumps(recipe.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
