# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado
# SPDX-License-Identifier: MIT
"""Recipes API — list and manage OSINT recon recipes.

Endpoints:
    GET    /api/recipes             — List all recipes
    GET    /api/recipes/{name}      — Get recipe details
    POST   /api/recipes             — Save a custom recipe
    DELETE /api/recipes/{name}      — Delete a custom recipe
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/recipes", tags=["Recipes"])


class RecipeStage(BaseModel):
    """Single stage in a recipe."""

    stage: str
    params: dict[str, Any] | None = None
    depends_on: list[str] = []


class RecipeCreateRequest(BaseModel):
    """Request body for creating/saving a recipe."""

    name: str
    description: str
    stages: list[RecipeStage]


class RecipeResponse(BaseModel):
    """Recipe API response."""

    name: str
    description: str
    stages: list[RecipeStage]
    is_builtin: bool = False


def _get_recipe_dir() -> Path:
    """Get the user recipe directory."""
    user_dir = Path.home() / ".osintote" / "recipes"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _get_builtin_recipes() -> dict[str, RecipeResponse]:
    """Load built-in recipes."""
    from osintote.recipes.models import DEFAULT_RECIPES

    recipes: dict[str, RecipeResponse] = {}
    for name, recipe in DEFAULT_RECIPES.items():
        recipes[name] = RecipeResponse(
            name=recipe.name,
            description=recipe.description,
            stages=[
                RecipeStage(
                    stage=s.stage,
                    params=s.params,
                    depends_on=s.depends_on,
                )
                for s in recipe.stages
            ],
            is_builtin=True,
        )
    return recipes


def _get_user_recipes() -> dict[str, RecipeResponse]:
    """Load user-defined recipes from .osintote/recipes/."""
    recipes: dict[str, RecipeResponse] = {}
    recipe_dir = _get_recipe_dir()

    for recipe_file in recipe_dir.glob("*.json"):
        try:
            data = json.loads(recipe_file.read_text(encoding="utf-8"))
            recipes[data["name"]] = RecipeResponse(
                name=data["name"],
                description=data.get("description", ""),
                stages=[
                    RecipeStage(
                        stage=s["stage"],
                        params=s.get("params"),
                        depends_on=s.get("depends_on", []),
                    )
                    for s in data.get("stages", [])
                ],
                is_builtin=False,
            )
        except Exception:
            # Silently skip invalid recipe files
            pass

    return recipes


@router.get("", response_model=list[dict])
async def list_recipes() -> list[dict]:
    """List all recipes (builtin + user-defined)."""
    all_recipes = {**_get_builtin_recipes(), **_get_user_recipes()}
    return [r.model_dump() for r in all_recipes.values()]


@router.get("/{name}", response_model=dict)
async def get_recipe(name: str) -> dict:
    """Get a recipe by name."""
    all_recipes = {**_get_builtin_recipes(), **_get_user_recipes()}
    recipe = all_recipes.get(name)
    if recipe is None:
        raise HTTPException(status_code=404, detail=f"Recipe {name} not found")
    return recipe.model_dump()


@router.post("", response_model=dict, status_code=201)
async def save_recipe(body: RecipeCreateRequest) -> dict:
    """Save a custom recipe to .osintote/recipes/."""
    builtin = _get_builtin_recipes()
    if body.name in builtin and builtin[body.name].is_builtin:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot overwrite built-in recipe {body.name}",
        )

    user_dir = _get_recipe_dir()
    recipe_file = user_dir / f"{body.name}.json"
    recipe_data = {
        "name": body.name,
        "description": body.description,
        "stages": [
            {
                "stage": s.stage,
                "params": s.params,
                "depends_on": s.depends_on,
            }
            for s in body.stages
        ],
    }
    recipe_file.write_text(json.dumps(recipe_data, indent=2) + "\n", encoding="utf-8")

    return RecipeResponse(
        name=body.name,
        description=body.description,
        stages=[
            RecipeStage(
                stage=s.stage,
                params=s.params,
                depends_on=s.depends_on,
            )
            for s in body.stages
        ],
        is_builtin=False,
    ).model_dump()


@router.delete("/{name}", response_model=dict)
async def delete_recipe(name: str) -> dict:
    """Delete a user-defined recipe."""
    builtin = _get_builtin_recipes()
    if name in builtin:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete built-in recipe {name}",
        )

    recipe_file = _get_recipe_dir() / f"{name}.json"
    if not recipe_file.exists():
        raise HTTPException(status_code=404, detail=f"Recipe {name} not found")

    recipe_file.unlink()
    return {"status": "deleted", "name": name}
