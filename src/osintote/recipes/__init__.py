# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Recipe system — JSON recipe configuration with bundled defaults."""

from .models import (
    DEFAULT_RECIPES,
    Recipe,
    RecipeLoader,
    StageDef,
)

__all__ = ["DEFAULT_RECIPES", "Recipe", "RecipeLoader", "StageDef"]
