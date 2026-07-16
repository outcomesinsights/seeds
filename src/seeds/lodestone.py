"""Pure text helpers for writing lodestones (no filesystem access).

The ``seeds lodestone`` verb writes a one-line principle into a managed section
of a durable context file (e.g. CLAUDE.md / README). The section
find-or-create + append logic lives here as a pure ``text_in -> text_out``
function so it is unit-testable without touching the disk.
"""

from __future__ import annotations


def append_to_managed_section(text: str, section_heading: str, bullet: str) -> str:
    """Return ``text`` with ``bullet`` appended under ``section_heading``.

    If ``section_heading`` already exists (exact match after stripping
    surrounding whitespace), ``bullet`` is inserted after the last non-blank
    line of that section -- i.e. after any existing bullets and before the next
    heading -- without duplicating the heading. If the heading is absent, a new
    section (heading, blank line, then the bullet) is appended to the end,
    separated from any prior content by a blank line.

    Pure and filesystem-free. Always returns text ending in a single newline.
    """
    heading = section_heading.strip()
    lines = text.splitlines()

    heading_idx: int | None = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            heading_idx = i
            break

    if heading_idx is None:
        body = list(lines)
        while body and not body[-1].strip():
            body.pop()
        section = [heading, "", bullet]
        if body:
            return "\n".join([*body, "", *section]) + "\n"
        return "\n".join(section) + "\n"

    # Find the end of this section: the next heading line, or end of text.
    section_end = len(lines)
    for j in range(heading_idx + 1, len(lines)):
        if lines[j].lstrip().startswith("#"):
            section_end = j
            break

    # Insert after the last non-blank line within the section, or -- if the
    # section is still empty -- immediately after the heading itself.
    insert_at = heading_idx
    for j in range(heading_idx + 1, section_end):
        if lines[j].strip():
            insert_at = j

    new_lines = [*lines[: insert_at + 1], bullet, *lines[insert_at + 1 :]]
    return "\n".join(new_lines) + "\n"
