"""seeds web UI - simple Flask app for viewing seeds."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, abort, render_template

from seeds.db import DB_FILE, Database, find_seeds_dir
from seeds.models import Seed, get_parent_id


def build_seed_tree(seeds: list[Seed]) -> list[dict[str, Any]]:
    """Build a hierarchical tree structure from flat seed list.

    Returns a list of top-level seeds, each with a 'children' list
    recursively populated. Each dict has: 'seed' (the Seed object),
    'children' (list of child dicts), 'depth' (int).
    """

    # Create tree nodes for each seed
    nodes: dict[str, dict[str, Any]] = {}
    for s in seeds:
        nodes[s.id] = {"seed": s, "children": [], "depth": 0}

    # Build parent-child relationships
    top_level: list[dict[str, Any]] = []
    for s in seeds:
        parent_id = get_parent_id(s.id)
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(nodes[s.id])
        else:
            top_level.append(nodes[s.id])

    # Calculate depths recursively
    def set_depths(node: dict[str, Any], depth: int = 0) -> None:
        node["depth"] = depth
        for child in node["children"]:
            set_depths(child, depth + 1)

    for node in top_level:
        set_depths(node)

    # Sort children by ID within each parent
    def sort_children(node: dict[str, Any]) -> None:
        node["children"].sort(key=lambda n: n["seed"].id)
        for child in node["children"]:
            sort_children(child)

    for node in top_level:
        sort_children(node)

    return top_level


def flatten_tree(tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten tree to list, preserving depth information for indentation."""
    result: list[dict[str, Any]] = []

    def visit(node: dict[str, Any]) -> None:
        result.append(node)
        for child in node["children"]:
            visit(child)

    for node in tree:
        visit(node)

    return result


def create_app(seeds_dir: Path | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        seeds_dir: Path to .seeds directory. If None, searches up from cwd.
    """
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))

    # Find seeds directory
    if seeds_dir is None:
        seeds_dir = find_seeds_dir()

    if seeds_dir is None:
        raise RuntimeError("No .seeds directory found. Run 'seeds init' first.")

    db_path = seeds_dir / DB_FILE

    def get_db() -> Database:
        """Get database instance."""
        return Database(db_path)

    @app.route("/")
    def index() -> str:
        """List all seeds."""
        db = get_db()
        seeds = db.list_seeds(include_terminal=True)
        db.close()

        # Build tree and flatten for template
        tree = build_seed_tree(seeds)
        flat_tree = flatten_tree(tree)

        return render_template("list.html", seeds=seeds, tree=flat_tree)

    @app.route("/seed/<seed_id>")
    def seed_detail(seed_id: str) -> str:
        """Show details for a single seed."""
        db = get_db()
        seed = db.get_seed(seed_id)
        if seed is None:
            db.close()
            abort(404)

        questions = db.list_questions(seed_id=seed_id)
        children = db.get_children(seed_id)

        # Get related seeds (resolve IDs to actual seeds for display)
        related_seeds = []
        for related_id in seed.related_to:
            related = db.get_seed(related_id)
            if related:
                related_seeds.append(related)

        # Check if parent exists
        parent = None
        if seed.parent_id:
            parent = db.get_seed(seed.parent_id)

        db.close()
        return render_template(
            "detail.html",
            seed=seed,
            questions=questions,
            children=children,
            related_seeds=related_seeds,
            parent=parent,
        )

    @app.route("/questions")
    def questions_list() -> str:
        """List all open questions."""
        db = get_db()
        questions = db.get_open_questions()

        # Get parent seed for each question
        questions_with_seeds = []
        for q in questions:
            seed = db.get_seed(q.seed_id)
            questions_with_seeds.append((q, seed))

        db.close()
        return render_template("questions.html", questions=questions_with_seeds)

    return app


def run_server(host: str = "127.0.0.1", port: int = 53365, debug: bool = False) -> None:
    """Run the development server.

    Args:
        host: Host to bind to.
        port: Port to bind to.
        debug: Enable debug mode.
    """
    app = create_app()
    app.run(host=host, port=port, debug=debug)
