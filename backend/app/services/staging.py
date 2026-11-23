"""Holds a job's results in memory and writes them to the database only when the whole job has finished.

A scrape (stages 2-3) or an analysis (stage 4) used to write each stage's rows as soon as that stage ended, so a run
stopped half-way left half-new data behind. ``StagedRepository`` wraps the real repository for one job:

  * result writes (``replace_*``, ``update_source``, ``update_ecommerce_product``, a ``gap_count`` patch) are kept in
    memory, and reads of the same rows return the kept rows, so stage 3 sees what stage 2 just read;
  * progress writes (the pipeline state, the project's running status) go through at once, so the screen can show
    progress, but only under ``jobs.guard``, so nothing is written after a cancel;
  * the pipeline state that marks the LAST stage complete is held too, so the screen never says "done" before the
    data is really saved;
  * ``commit()`` writes everything, in the original order, inside ``jobs.guard``.
"""
from __future__ import annotations

from typing import Any

from app.services import jobs

#: replace_X writes rows that list_X reads back.
_READ_OF = {
    "replace_sources": "list_sources",
    "replace_ecommerce_products": "list_ecommerce_products",
    "replace_ecommerce_product_images": "list_ecommerce_product_images",
    "replace_ecommerce_product_price_tiers": "list_ecommerce_product_price_tiers",
    "replace_ecommerce_product_suppliers": "list_ecommerce_product_suppliers",
    "replace_website_pages": "list_website_pages",
    "replace_website_page_images": "list_website_page_images",
    "replace_instagram_posts": "list_instagram_posts",
    "replace_instagram_post_media": "list_instagram_post_media",
    "replace_instagram_post_comments": "list_instagram_post_comments",
    "replace_instagram_chunks": "list_instagram_chunks",
    "replace_gaps": "list_gaps",
}
_ROW_UPDATES = {"update_source": "list_sources", "update_ecommerce_product": "list_ecommerce_products"}
#: Extras that thin the result when they cannot be saved, but do not fail it (same rule as before staging).
_OPTIONAL = {
    "replace_ecommerce_product_images", "replace_ecommerce_product_price_tiers", "replace_ecommerce_product_suppliers",
    "replace_website_page_images", "replace_instagram_post_media", "replace_instagram_post_comments",
    "replace_instagram_chunks", "update_source", "update_ecommerce_product",
}
#: Project fields that are results, not progress.
_RESULT_FIELDS = {"gap_count"}


class StagedRepository:
    def __init__(self, real: Any, project_id: str, last_stage: int):
        self._real, self._project_id, self._last_stage = real, project_id, last_stage
        self._writes: list[tuple[str, tuple, dict]] = []
        self._rows: dict[str, list[dict[str, Any]]] = {}
        self._final_state: dict[str, Any] | None = None

    # ------------------------------------------------------------------ held writes
    def __getattr__(self, name: str) -> Any:
        if name in _READ_OF:
            def replace(project_id: str, rows: list[dict[str, Any]]) -> None:
                self._writes.append((name, (project_id, rows), {}))
                self._rows[_READ_OF[name]] = [dict(r) for r in rows]
            return replace
        if name in _ROW_UPDATES:
            def update(project_id: str, row_id: str, patch: dict[str, Any]) -> dict[str, Any]:
                self._writes.append((name, (project_id, row_id, patch), {}))
                for row in self._rows.get(_ROW_UPDATES[name], []):
                    if row.get("id") == row_id:
                        row.update(patch)
                        return dict(row)
                return {"id": row_id, **patch}
            return update
        if name in self._rows_readers():
            held = self._rows[name]
            return lambda project_id, *a, **k: [dict(r) for r in held]
        return getattr(self._real, name)

    def _rows_readers(self) -> set[str]:
        return set(self._rows)

    # ------------------------------------------------------------------ progress
    def update_project(self, project_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        result = {k: v for k, v in patch.items() if k in _RESULT_FIELDS}
        progress = {k: v for k, v in patch.items() if k not in _RESULT_FIELDS}
        if result:
            self._writes.append(("update_project", (project_id, result), {}))
        if progress:
            with jobs.guard(self._project_id):
                return self._real.update_project(project_id, progress)
        return {}

    def save_pipeline(self, project_id: str, state: dict[str, Any]) -> None:
        last = (state.get("stages") or {}).get(str(self._last_stage)) or {}
        if last.get("status") == "complete":
            self._final_state = state            # "done" is shown only once the data is saved
            return
        with jobs.guard(self._project_id):
            self._real.save_pipeline(project_id, state)

    # ------------------------------------------------------------------ the one write
    def commit(self, extra: list[tuple[str, tuple, dict]] | None = None) -> list[str]:
        """Writes every held result in order (already inside ``jobs.guard``), then the final pipeline state.

        Returns warnings for extras that could not be saved. A main result that cannot be saved raises, with the
        database's own reason. (Supabase's REST API has no transaction across tables, so if the database itself
        fails half-way, the rows already written stay; a cancel or a scraping failure never writes anything.)
        """
        warnings: list[str] = []
        for name, args, kwargs in [*self._writes, *(extra or [])]:
            try:
                getattr(self._real, name)(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - optional extras only warn
                label = name.replace("replace_", "").replace("update_", "").replace("_", " ")
                if name in _OPTIONAL:
                    warnings.append(f"{label.capitalize()} could not be saved ({type(exc).__name__}).")
                    continue
                raise RuntimeError(f"The scraped {label} could not be saved: {exc}") from exc
        if self._final_state is not None:
            self._real.save_pipeline(self._project_id, self._final_state)
        self._writes.clear()
        return warnings
