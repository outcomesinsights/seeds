"""Tests for the seeds web UI."""

import pytest

from seeds.models import Seed, SeedStatus, SeedType
from seeds.web import build_seed_tree, create_app, flatten_tree


@pytest.fixture
def app(db):
    """Create Flask test app with test database."""
    app = create_app(seeds_dir=db.path.parent)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def populated_db(db):
    """Create a database with hierarchical seeds for testing."""
    # Top-level seeds
    seeds = [
        Seed(id="seed-aaa", title="First Idea", status=SeedStatus.CAPTURED, seed_type=SeedType.IDEA, tags=["ui", "feature"]),
        Seed(id="seed-bbb", title="Second Idea", status=SeedStatus.EXPLORING, seed_type=SeedType.EXPLORATION, tags=["backend"]),
        Seed(id="seed-ccc", title="Third Idea", status=SeedStatus.RESOLVED, seed_type=SeedType.DECISION, tags=["ui"]),
        # Children of seed-aaa
        Seed(id="seed-aaa.1", title="Sub-idea 1", status=SeedStatus.CAPTURED, seed_type=SeedType.IDEA, tags=["detail"]),
        Seed(id="seed-aaa.2", title="Sub-idea 2", status=SeedStatus.DEFERRED, seed_type=SeedType.CONCERN, tags=["risk"]),
        # Grandchild
        Seed(id="seed-aaa.1.1", title="Deep thought", status=SeedStatus.CAPTURED, seed_type=SeedType.QUESTION, tags=["meta"]),
        # Child of seed-bbb
        Seed(id="seed-bbb.1", title="Backend detail", status=SeedStatus.EXPLORING, seed_type=SeedType.EXPLORATION, tags=["api"]),
    ]
    for seed in seeds:
        db.create_seed(seed)
    return db


class TestBuildSeedTree:
    """Tests for the tree-building function."""

    def test_empty_list(self):
        """Empty seed list returns empty tree."""
        tree = build_seed_tree([])
        assert tree == []

    def test_single_seed(self):
        """Single seed becomes single top-level node."""
        seed = Seed(id="seed-abc", title="Test")
        tree = build_seed_tree([seed])
        assert len(tree) == 1
        assert tree[0]["seed"] == seed
        assert tree[0]["children"] == []
        assert tree[0]["depth"] == 0

    def test_parent_child_relationship(self):
        """Child seeds are nested under parents."""
        parent = Seed(id="seed-abc", title="Parent")
        child = Seed(id="seed-abc.1", title="Child")
        tree = build_seed_tree([parent, child])

        assert len(tree) == 1  # Only parent at top level
        assert tree[0]["seed"] == parent
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["seed"] == child

    def test_multiple_children(self):
        """Multiple children are grouped under parent."""
        parent = Seed(id="seed-abc", title="Parent")
        child1 = Seed(id="seed-abc.1", title="Child 1")
        child2 = Seed(id="seed-abc.2", title="Child 2")
        tree = build_seed_tree([parent, child1, child2])

        assert len(tree) == 1
        assert len(tree[0]["children"]) == 2

    def test_grandchildren(self):
        """Grandchildren are nested under children."""
        parent = Seed(id="seed-abc", title="Parent")
        child = Seed(id="seed-abc.1", title="Child")
        grandchild = Seed(id="seed-abc.1.1", title="Grandchild")
        tree = build_seed_tree([parent, child, grandchild])

        assert len(tree) == 1
        assert len(tree[0]["children"]) == 1
        assert len(tree[0]["children"][0]["children"]) == 1
        assert tree[0]["children"][0]["children"][0]["seed"] == grandchild

    def test_depth_calculation(self):
        """Depth is calculated correctly for each level."""
        parent = Seed(id="seed-abc", title="Parent")
        child = Seed(id="seed-abc.1", title="Child")
        grandchild = Seed(id="seed-abc.1.1", title="Grandchild")
        tree = build_seed_tree([parent, child, grandchild])

        assert tree[0]["depth"] == 0
        assert tree[0]["children"][0]["depth"] == 1
        assert tree[0]["children"][0]["children"][0]["depth"] == 2

    def test_orphan_children_become_top_level(self):
        """Children without parents in the list become top-level."""
        # Only child, no parent
        child = Seed(id="seed-abc.1", title="Orphan Child")
        tree = build_seed_tree([child])

        assert len(tree) == 1
        assert tree[0]["seed"] == child
        assert tree[0]["depth"] == 0  # Treated as top-level

    def test_multiple_top_level_seeds(self):
        """Multiple independent seeds at top level."""
        seed1 = Seed(id="seed-aaa", title="First")
        seed2 = Seed(id="seed-bbb", title="Second")
        seed3 = Seed(id="seed-ccc", title="Third")
        tree = build_seed_tree([seed1, seed2, seed3])

        assert len(tree) == 3

    def test_children_sorted_by_id(self):
        """Children are sorted by ID within each parent."""
        parent = Seed(id="seed-abc", title="Parent")
        child3 = Seed(id="seed-abc.3", title="Third")
        child1 = Seed(id="seed-abc.1", title="First")
        child2 = Seed(id="seed-abc.2", title="Second")
        # Pass in random order
        tree = build_seed_tree([parent, child3, child1, child2])

        children = tree[0]["children"]
        assert children[0]["seed"].id == "seed-abc.1"
        assert children[1]["seed"].id == "seed-abc.2"
        assert children[2]["seed"].id == "seed-abc.3"


class TestFlattenTree:
    """Tests for the tree-flattening function."""

    def test_empty_tree(self):
        """Empty tree returns empty list."""
        result = flatten_tree([])
        assert result == []

    def test_single_node(self):
        """Single node returns single-element list."""
        seed = Seed(id="seed-abc", title="Test")
        tree = build_seed_tree([seed])
        flat = flatten_tree(tree)
        assert len(flat) == 1
        assert flat[0]["seed"] == seed

    def test_preserves_depth(self):
        """Flattening preserves depth information."""
        parent = Seed(id="seed-abc", title="Parent")
        child = Seed(id="seed-abc.1", title="Child")
        grandchild = Seed(id="seed-abc.1.1", title="Grandchild")
        tree = build_seed_tree([parent, child, grandchild])
        flat = flatten_tree(tree)

        assert len(flat) == 3
        assert flat[0]["depth"] == 0
        assert flat[1]["depth"] == 1
        assert flat[2]["depth"] == 2

    def test_parent_before_children(self):
        """Parents appear before their children in flattened list."""
        parent = Seed(id="seed-abc", title="Parent")
        child1 = Seed(id="seed-abc.1", title="Child 1")
        child2 = Seed(id="seed-abc.2", title="Child 2")
        tree = build_seed_tree([parent, child1, child2])
        flat = flatten_tree(tree)

        ids = [node["seed"].id for node in flat]
        assert ids.index("seed-abc") < ids.index("seed-abc.1")
        assert ids.index("seed-abc") < ids.index("seed-abc.2")


class TestWebRoutes:
    """Tests for Flask routes."""

    def test_index_returns_200(self, client, populated_db):
        """Index route returns 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_index_contains_seeds(self, client, populated_db):
        """Index page contains seed data."""
        response = client.get("/")
        html = response.data.decode()
        assert "seed-aaa" in html
        assert "First Idea" in html
        assert "seed-bbb" in html

    def test_index_shows_nested_view_toggle(self, client, populated_db):
        """Index page contains view toggle buttons."""
        response = client.get("/")
        html = response.data.decode()
        assert 'id="btn-nested"' in html
        assert 'id="btn-flat"' in html

    def test_index_shows_filter_controls(self, client, populated_db):
        """Index page contains filter inputs."""
        response = client.get("/")
        html = response.data.decode()
        assert 'id="filter-id"' in html
        assert 'id="filter-title"' in html
        assert 'id="status-select"' in html
        assert 'id="type-select"' in html
        assert 'id="filter-tags"' in html

    def test_index_shows_sortable_headers(self, client, populated_db):
        """Index page contains sortable table headers."""
        response = client.get("/")
        html = response.data.decode()
        assert 'class="sortable"' in html
        assert 'onclick="sortBy(' in html

    def test_index_shows_depth_info(self, client, populated_db):
        """Index page includes depth data for nested view."""
        response = client.get("/")
        html = response.data.decode()
        assert 'data-depth="0"' in html
        assert 'data-depth="1"' in html  # Children have depth 1
        assert 'data-depth="2"' in html  # Grandchildren have depth 2

    def test_index_shows_child_indicators(self, client, populated_db):
        """Index page shows child indicators for nested seeds."""
        response = client.get("/")
        html = response.data.decode()
        assert 'class="child-indicator"' in html

    def test_detail_page_returns_200(self, client, populated_db):
        """Seed detail page returns 200 OK."""
        response = client.get("/seed/seed-aaa")
        assert response.status_code == 200

    def test_detail_page_shows_content(self, client, populated_db):
        """Seed detail page shows seed title."""
        response = client.get("/seed/seed-aaa")
        html = response.data.decode()
        assert "First Idea" in html

    def test_detail_page_has_markdown_rendering(self, client, populated_db):
        """Detail page has markdown rendering setup."""
        response = client.get("/seed/seed-aaa")
        html = response.data.decode()
        assert "marked.min.js" in html
        assert "prettifyMarkdown" in html

    def test_detail_page_404_for_missing(self, client, populated_db):
        """Detail page returns 404 for nonexistent seed."""
        response = client.get("/seed/seed-nonexistent")
        assert response.status_code == 404

    def test_questions_page_returns_200(self, client, populated_db):
        """Questions page returns 200 OK."""
        response = client.get("/questions")
        assert response.status_code == 200


class TestMarkdownPrettifier:
    """Tests for markdown prettification (client-side, but verify script present)."""

    def test_prettifier_script_present(self, client, populated_db):
        """Prettifier JavaScript function is included in page."""
        response = client.get("/")
        html = response.data.decode()
        assert "function prettifyMarkdown" in html

    def test_render_markdown_function_present(self, client, populated_db):
        """Markdown render function is included in page."""
        response = client.get("/")
        html = response.data.decode()
        assert "function renderMarkdown" in html

    def test_detail_page_has_data_markdown_attribute(self, client, db):
        """Detail page uses data-markdown attribute for content."""
        # Create seed with content
        seed = Seed(
            id="seed-test",
            title="Test",
            content="# Header\n\nSome content with **bold** text."
        )
        db.create_seed(seed)

        response = client.get("/seed/seed-test")
        html = response.data.decode()
        assert 'data-markdown' in html
