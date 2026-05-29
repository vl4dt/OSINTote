# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Recipe management commands — list, show, save, delete."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

app = typer.Typer(help="Recipe management commands")


@app.command("list")
def recipe_list() -> None:
    """List all available recipes."""
    from osintote.recipes import RecipeLoader

    loader = RecipeLoader()
    recipes = loader.list_recipes()

    if not recipes:
        console.print("[blue]--[/] No recipes found.")
        return

    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
    )
    table.add_column("[bold]Name[/]")
    table.add_column("[bold]Description[/]")
    table.add_column("[bold]Stages[/]")

    for recipe in recipes:
        table.add_row(
            recipe.name,
            recipe.description,
            " → ".join(s.stage for s in recipe.stages),
        )

    console.print(table)


@app.command("show")
def recipe_show(
    name: str = typer.Argument(..., help="Recipe name"),
) -> None:
    """Show details of a specific recipe."""
    from osintote.recipes import RecipeLoader

    loader = RecipeLoader()
    recipe = loader.get_recipe(name)

    if recipe is None:
        console.print(f"[red]Recipe '{name}' not found.[/]")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            f"[bold]Name:[/] {recipe.name}\n"
            f"[bold]Description:[/] {recipe.description}\n\n"
            "[bold]Stages:[/]\n"
            + "\n".join(
                f"  {i + 1}. {s.stage}"
                + (f" (depends: {', '.join(s.depends_on)})" if s.depends_on else "")
                for i, s in enumerate(recipe.stages)
            ),
            title=f"Recipe: {recipe.name}",
            border_style="green",
        )
    )


@app.command("save")
def recipe_save(
    name: str = typer.Argument(..., help="Recipe name"),
    description: str = typer.Option("", "-d", "--description", help="Recipe description"),
    stages: str = typer.Option(
        "",
        "-s",
        "--stages",
        help='Comma-separated stage names (e.g., "dns-enumerate,http-probe,nmap")',
    ),
    depends: str = typer.Option(
        "",
        "-dp",
        "--depends",
        help='Dependency map (stage:dep1,dep2) e.g. "http-probe:dns-enumerate"',
    ),
) -> None:
    """Save a new recipe (creates user override)."""
    from osintote.recipes import Recipe, RecipeLoader, StageDef

    loader = RecipeLoader()

    # Parse stages
    stage_names = [s.strip() for s in stages.split(",") if s.strip()]
    stage_deps: dict[str, list[str]] = {}
    if depends:
        for part in depends.split(","):
            part = part.strip()
            if ":" in part:
                sname, deps_str = part.split(":", 1)
                stage_deps[sname.strip()] = [d.strip() for d in deps_str.split(",") if d.strip()]

    stages = []
    for sname in stage_names:
        deps = stage_deps.get(sname, [])
        stages.append(StageDef(stage=sname, depends_on=deps))

    recipe = Recipe(name=name, description=description, stages=stages)
    loader.save_recipe(recipe, project_root=Path.cwd())
    console.print(f"[green]OK[/] Recipe '{name}' saved to .osintote/recipes/")


@app.command("delete")
def recipe_delete(
    name: str = typer.Argument(..., help="Recipe name"),
) -> None:
    """Delete a user-defined recipe (overrides only)."""
    from osintote.recipes import RecipeLoader

    loader = RecipeLoader()
    recipe = loader.get_recipe(name)
    if recipe is None:
        console.print(f"[red]Recipe '{name}' not found.[/]")
        raise typer.Exit(code=1)

    recipe_file = Path.cwd() / ".osintote" / "recipes" / f"{name}.json"
    if recipe_file.exists():
        recipe_file.unlink()
        console.print(f"[green]OK[/] Recipe '{name}' deleted.")
    else:
        console.print(
            f"[yellow]Note:[/] '{name}' is a bundled recipe (cannot delete)."
        )
