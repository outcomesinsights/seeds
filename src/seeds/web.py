"""seeds web UI - simple Flask app for viewing seeds."""

from flask import Flask, render_template, abort
from pathlib import Path

from seeds.db import Database, find_seeds_dir, SEEDS_DIR, DB_FILE


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
        raise RuntimeError(
            "No .seeds directory found. Run 'seeds init' first."
        )

    db_path = seeds_dir / DB_FILE

    def get_db() -> Database:
        """Get database instance."""
        db = Database(db_path)
        return db

    @app.route("/")
    def index():
        """List all seeds."""
        db = get_db()
        seeds = db.list_seeds(include_terminal=True)
        db.close()
        return render_template("list.html", seeds=seeds)

    @app.route("/seed/<seed_id>")
    def seed_detail(seed_id: str):
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
    def questions_list():
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


def run_server(host: str = "127.0.0.1", port: int = 53365, debug: bool = False):
    """Run the development server.

    Args:
        host: Host to bind to.
        port: Port to bind to.
        debug: Enable debug mode.
    """
    app = create_app()
    app.run(host=host, port=port, debug=debug)
