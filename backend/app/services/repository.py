"""Storage.

Two interchangeable backends behind one interface:

  * ``MemoryRepository``, process-local dicts, seeded with the demo project.
    Used in demo mode and by the tests. Lets the whole API run with no database.

  * ``SupabaseRepository``. Postgres through the Supabase client, every call
    carrying the caller's JWT so row-level security is what enforces ownership.
    Application code never adds an ``owner_id`` filter; the database does it,
    and cannot be talked out of it by a forgotten WHERE clause.

Rows are stored snake_case (matching the Postgres columns in db/schema.sql) and
serialised to camelCase by the Pydantic models at the edge.
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.supabase import get_service_client, get_user_client
from app.services import demo_data

logger = logging.getLogger("optistratix.repository")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ============================================================== in-memory ====


class MemoryRepository:
    """Process-local store. Seeded once with the demo project.

    A class-level lock guards mutation because FastAPI serves requests from a
    thread pool, and the background pipeline worker writes from another thread.
    """

    _lock = threading.RLock()
    _seeded = False

    #: Shared across instances so every request sees the same data. Rebind
    #: these through the class, never through `self`. `self._gaps = [...]`
    #: would create an instance attribute that shadows the shared one, and a
    #: write from the background worker would never be seen by a request.
    _projects: list[dict[str, Any]] = []
    _competitors: list[dict[str, Any]] = []
    _sources: list[dict[str, Any]] = []
    _gaps: list[dict[str, Any]] = []
    _strategies: list[dict[str, Any]] = []
    _reviews: list[dict[str, Any]] = []
    _documents: list[dict[str, Any]] = []
    _suggestions: list[dict[str, Any]] = []
    _ecommerce_products: list[dict[str, Any]] = []
    _ecommerce_product_images: list[dict[str, Any]] = []
    _ecommerce_product_price_tiers: list[dict[str, Any]] = []
    _ecommerce_product_suppliers: list[dict[str, Any]] = []
    _integrations: list[dict[str, Any]] = []
    _pipelines: dict[str, dict[str, Any]] = {}
    _contact: list[dict[str, Any]] = []

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self._seed()

    @classmethod
    def _seed(cls) -> None:
        with cls._lock:
            if cls._seeded:
                return
            cls._projects = [demo_data.demo_project()]
            cls._competitors = demo_data.demo_competitors()
            cls._integrations = demo_data.demo_integrations()

            # The demo project is pre-run up to the first checkpoint: sources
            # and gaps exist, and it is parked at stage 5 waiting on a human.
            competitors = cls._competitors
            sources = demo_data.build_sources(demo_data.DEMO_PROJECT_ID, competitors)
            cls._sources = sources
            gaps = demo_data.build_gaps(demo_data.DEMO_PROJECT_ID, sources)
            cls._gaps = gaps
            cls._pipelines = {
                demo_data.DEMO_PROJECT_ID: demo_data.demo_pipeline_state(
                    demo_data.DEMO_PROJECT_ID, len(sources), len(gaps)
                )
            }
            cls._seeded = True
            logger.info("Memory repository seeded with the demo project")

    @classmethod
    def reset(cls) -> None:
        """Test helper: wipe and re-seed."""
        with cls._lock:
            cls._seeded = False
            cls._projects = []
            cls._competitors = []
            cls._sources = []
            cls._gaps = []
            cls._strategies = []
            cls._reviews = []
            cls._documents = []
            cls._suggestions = []
            cls._integrations = []
            cls._pipelines = {}
            cls._contact = []
            cls._ecommerce_products = []
            cls._ecommerce_product_images = []
            cls._ecommerce_product_price_tiers = []
            cls._ecommerce_product_suppliers = []
        cls._seed()

    # ------------------------------------------------------------- projects

    def list_projects(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._projects]

    def get_project(self, project_id: str) -> dict[str, Any]:
        for row in self._projects:
            if row["id"] == project_id:
                return dict(row)
        raise NotFoundError("That project does not exist, or you do not have access to it.")

    def insert_project(self, project: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._projects.insert(0, project)
        return dict(project)

    def update_project(self, project_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            for row in self._projects:
                if row["id"] == project_id:
                    row.update(patch)
                    row["updated_at"] = demo_data.iso()
                    return dict(row)
        raise NotFoundError("That project does not exist, or you do not have access to it.")

    def delete_project(self, project_id: str) -> None:
        with self._lock:
            MemoryRepository._projects = [row for row in self._projects if row["id"] != project_id]
            MemoryRepository._competitors = [r for r in self._competitors if r["project_id"] != project_id]
            MemoryRepository._sources = [r for r in self._sources if r["project_id"] != project_id]
            MemoryRepository._gaps = [r for r in self._gaps if r["project_id"] != project_id]
            MemoryRepository._strategies = [r for r in self._strategies if r["project_id"] != project_id]
            MemoryRepository._reviews = [r for r in self._reviews if r["project_id"] != project_id]
            MemoryRepository._documents = [r for r in self._documents if r["project_id"] != project_id]
            MemoryRepository._suggestions = [r for r in self._suggestions if r["project_id"] != project_id]
            MemoryRepository._ecommerce_products = [
                r for r in self._ecommerce_products if r["project_id"] != project_id
            ]
            MemoryRepository._ecommerce_product_images = [
                r for r in self._ecommerce_product_images if r["project_id"] != project_id
            ]
            MemoryRepository._ecommerce_product_price_tiers = [
                r for r in self._ecommerce_product_price_tiers if r["project_id"] != project_id
            ]
            MemoryRepository._ecommerce_product_suppliers = [
                r for r in self._ecommerce_product_suppliers if r["project_id"] != project_id
            ]
            self._pipelines.pop(project_id, None)

    # ---------------------------------------------------------- competitors

    def list_competitors(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._competitors if r["project_id"] == project_id]

    def insert_competitors(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with self._lock:
            self._competitors.extend(rows)
        return [dict(row) for row in rows]

    # -------------------------------------------------------------- sources

    def list_sources(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._sources if r["project_id"] == project_id]

    def replace_sources(self, project_id: str, rows: list[dict[str, Any]]) -> None:
        with self._lock:
            MemoryRepository._sources = [r for r in self._sources if r["project_id"] != project_id]
            self._sources.extend(rows)

    # --------------------------------------------- e-commerce products

    def list_ecommerce_products(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._ecommerce_products if r["project_id"] == project_id]

    def replace_ecommerce_products(self, project_id: str, rows: list[dict[str, Any]]) -> None:
        with self._lock:
            MemoryRepository._ecommerce_products = [
                r for r in self._ecommerce_products if r["project_id"] != project_id
            ]
            # Mirrors the ON DELETE CASCADE from images, tiers and suppliers to
            # products in Postgres.
            MemoryRepository._ecommerce_product_images = [
                r for r in self._ecommerce_product_images if r["project_id"] != project_id
            ]
            MemoryRepository._ecommerce_product_price_tiers = [
                r for r in self._ecommerce_product_price_tiers if r["project_id"] != project_id
            ]
            MemoryRepository._ecommerce_product_suppliers = [
                r for r in self._ecommerce_product_suppliers if r["project_id"] != project_id
            ]
            self._ecommerce_products.extend(rows)

    def list_ecommerce_product_images(self, project_id: str) -> list[dict[str, Any]]:
        rows = [dict(r) for r in self._ecommerce_product_images if r["project_id"] == project_id]
        return sorted(rows, key=lambda row: (row["product_id"], row["position"]))

    def replace_ecommerce_product_images(
        self, project_id: str, rows: list[dict[str, Any]]
    ) -> None:
        with self._lock:
            MemoryRepository._ecommerce_product_images = [
                r for r in self._ecommerce_product_images if r["project_id"] != project_id
            ]
            self._ecommerce_product_images.extend(rows)

    def list_ecommerce_product_price_tiers(self, project_id: str) -> list[dict[str, Any]]:
        rows = [dict(r) for r in self._ecommerce_product_price_tiers if r["project_id"] == project_id]
        return sorted(rows, key=lambda row: (row["product_id"], row["position"]))

    def replace_ecommerce_product_price_tiers(
        self, project_id: str, rows: list[dict[str, Any]]
    ) -> None:
        with self._lock:
            MemoryRepository._ecommerce_product_price_tiers = [
                r for r in self._ecommerce_product_price_tiers if r["project_id"] != project_id
            ]
            self._ecommerce_product_price_tiers.extend(rows)

    def list_ecommerce_product_suppliers(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._ecommerce_product_suppliers if r["project_id"] == project_id]

    def replace_ecommerce_product_suppliers(
        self, project_id: str, rows: list[dict[str, Any]]
    ) -> None:
        with self._lock:
            MemoryRepository._ecommerce_product_suppliers = [
                r for r in self._ecommerce_product_suppliers if r["project_id"] != project_id
            ]
            self._ecommerce_product_suppliers.extend(rows)

    def update_ecommerce_product(
        self, project_id: str, product_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        with self._lock:
            for row in self._ecommerce_products:
                if row["id"] == product_id and row["project_id"] == project_id:
                    row.update(patch)
                    return dict(row)
        raise NotFoundError(f"Product {product_id} was not found")

    # ----------------------------------------------------------------- gaps

    def list_gaps(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._gaps if r["project_id"] == project_id]

    def replace_gaps(self, project_id: str, rows: list[dict[str, Any]]) -> None:
        with self._lock:
            MemoryRepository._gaps = [r for r in self._gaps if r["project_id"] != project_id]
            self._gaps.extend(rows)

    def update_gap(self, project_id: str, gap_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            for row in self._gaps:
                if row["id"] == gap_id and row["project_id"] == project_id:
                    row.update({k: v for k, v in patch.items() if v is not None})
                    return dict(row)
        raise NotFoundError("That gap does not exist on this project.")

    # ----------------------------------------------------------- strategies

    def get_strategy(self, project_id: str) -> dict[str, Any] | None:
        matches = [r for r in self._strategies if r["project_id"] == project_id]
        return dict(max(matches, key=lambda r: r["version"])) if matches else None

    def insert_strategy(self, strategy: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._strategies.append(strategy)
        return dict(strategy)

    def update_strategy(self, strategy_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            for row in self._strategies:
                if row["id"] == strategy_id:
                    row.update(patch)
                    return dict(row)
        raise NotFoundError("That strategy does not exist.")

    def clear_strategies(self, project_id: str) -> None:
        with self._lock:
            MemoryRepository._strategies = [r for r in self._strategies if r["project_id"] != project_id]

    # -------------------------------------------------------------- reviews

    def list_reviews(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._reviews if r["project_id"] == project_id]

    def insert_review(self, review: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._reviews.append(review)
        return dict(review)

    # ------------------------------------------------------------ documents

    def get_document(self, project_id: str) -> dict[str, Any] | None:
        matches = [r for r in self._documents if r["project_id"] == project_id]
        return dict(matches[-1]) if matches else None

    def insert_document(self, document: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            MemoryRepository._documents = [r for r in self._documents if r["project_id"] != document["project_id"]]
            self._documents.append(document)
        return dict(document)

    # ---------------------------------------------------------- suggestions

    def list_suggestions(self, project_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._suggestions if r["project_id"] == project_id]

    def replace_suggestions(self, project_id: str, rows: list[dict[str, Any]]) -> None:
        with self._lock:
            MemoryRepository._suggestions = [r for r in self._suggestions if r["project_id"] != project_id]
            self._suggestions.extend(rows)

    def update_suggestion(
        self, project_id: str, suggestion_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        with self._lock:
            for row in self._suggestions:
                if row["id"] == suggestion_id and row["project_id"] == project_id:
                    row.update({k: v for k, v in patch.items() if v is not None})
                    return dict(row)
        raise NotFoundError("That content suggestion does not exist on this project.")

    # ------------------------------------------------------------- pipeline

    def get_pipeline(self, project_id: str) -> dict[str, Any] | None:
        found = self._pipelines.get(project_id)
        return dict(found) if found else None

    def save_pipeline(self, project_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            self._pipelines[project_id] = state

    # --------------------------------------------------------- integrations

    def list_integrations(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._integrations]

    def update_integration(self, integration_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            for row in self._integrations:
                if row["id"] == integration_id:
                    row.update(patch)
                    return dict(row)
        raise NotFoundError("That integration does not exist.")

    # -------------------------------------------------------------- contact

    def insert_contact(self, submission: dict[str, Any]) -> None:
        with self._lock:
            self._contact.append(submission)


# =============================================================== supabase ====


class SupabaseRepository:
    """Postgres via Supabase. RLS enforces ownership on every call.

    ``service`` is used only by the background pipeline worker, which runs after
    the originating request has returned and therefore has no JWT to carry.
    """

    def __init__(self, user_id: str, token: str, *, service: bool = False) -> None:
        self.user_id = user_id
        self.client = get_service_client() if service else get_user_client(token)

    # ------------------------------------------------------------- projects

    def list_projects(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("projects").select("*").order("updated_at", desc=True).execute()
        )
        return result.data or []

    def get_project(self, project_id: str) -> dict[str, Any]:
        result = self.client.table("projects").select("*").eq("id", project_id).execute()
        rows = result.data or []
        if not rows:
            raise NotFoundError("That project does not exist, or you do not have access to it.")
        return rows[0]

    def insert_project(self, project: dict[str, Any]) -> dict[str, Any]:
        result = self.client.table("projects").insert(project).execute()
        return (result.data or [project])[0]

    def update_project(self, project_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        payload = {**patch, "updated_at": demo_data.iso()}
        result = self.client.table("projects").update(payload).eq("id", project_id).execute()
        rows = result.data or []
        if not rows:
            raise NotFoundError("That project does not exist, or you do not have access to it.")
        return rows[0]

    def delete_project(self, project_id: str) -> None:
        # Child rows go with it via ON DELETE CASCADE (see db/schema.sql).
        self.client.table("projects").delete().eq("id", project_id).execute()

    # ---------------------------------------------------------- competitors

    def list_competitors(self, project_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("competitors").select("*").eq("project_id", project_id).execute()
        )
        return result.data or []

    def insert_competitors(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        result = self.client.table("competitors").insert(rows).execute()
        return result.data or rows

    # -------------------------------------------------------------- sources

    def list_sources(self, project_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("scraped_sources").select("*").eq("project_id", project_id).execute()
        )
        return result.data or []

    def replace_sources(self, project_id: str, rows: list[dict[str, Any]]) -> None:
        self.client.table("scraped_sources").delete().eq("project_id", project_id).execute()
        if rows:
            self.client.table("scraped_sources").insert(rows).execute()

    # --------------------------------------------- e-commerce products

    def list_ecommerce_products(self, project_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("ecommerce_products")
            .select("*")
            .eq("project_id", project_id)
            # Own first, so callers that want the baseline do not have to sort.
            .order("role")
            .execute()
        )
        return result.data or []

    def replace_ecommerce_products(self, project_id: str, rows: list[dict[str, Any]]) -> None:
        """A re-run replaces the whole set: a half-old, half-new pair of
        listings would produce a comparison of two different moments in time."""
        self.client.table("ecommerce_products").delete().eq("project_id", project_id).execute()
        if rows:
            self.client.table("ecommerce_products").insert(rows).execute()

    def list_ecommerce_product_images(self, project_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("ecommerce_product_images")
            .select("*")
            .eq("project_id", project_id)
            .order("product_id")
            .order("position")
            .execute()
        )
        return result.data or []

    def replace_ecommerce_product_images(
        self, project_id: str, rows: list[dict[str, Any]]
    ) -> None:
        """Usually a no-op delete: replacing the products already cascaded the
        old images away. Kept explicit so this never relies on call order."""
        self.client.table("ecommerce_product_images").delete().eq("project_id", project_id).execute()
        if rows:
            self.client.table("ecommerce_product_images").insert(rows).execute()

    def list_ecommerce_product_price_tiers(self, project_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("ecommerce_product_price_tiers")
            .select("*")
            .eq("project_id", project_id)
            .order("product_id")
            .order("position")
            .execute()
        )
        return result.data or []

    def replace_ecommerce_product_price_tiers(
        self, project_id: str, rows: list[dict[str, Any]]
    ) -> None:
        """Usually a no-op delete: replacing the products cascaded the old tiers."""
        self.client.table("ecommerce_product_price_tiers").delete().eq("project_id", project_id).execute()
        if rows:
            self.client.table("ecommerce_product_price_tiers").insert(rows).execute()

    def list_ecommerce_product_suppliers(self, project_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("ecommerce_product_suppliers")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        return result.data or []

    def replace_ecommerce_product_suppliers(
        self, project_id: str, rows: list[dict[str, Any]]
    ) -> None:
        """Usually a no-op delete: replacing the products cascaded the old profiles."""
        self.client.table("ecommerce_product_suppliers").delete().eq("project_id", project_id).execute()
        if rows:
            self.client.table("ecommerce_product_suppliers").insert(rows).execute()

    def update_ecommerce_product(
        self, project_id: str, product_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        result = (
            self.client.table("ecommerce_products")
            .update(patch)
            .eq("id", product_id)
            .eq("project_id", project_id)
            .execute()
        )
        if not result.data:
            raise NotFoundError(f"Product {product_id} was not found")
        return result.data[0]

    # ----------------------------------------------------------------- gaps

    def list_gaps(self, project_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("gaps_opportunities")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        return result.data or []

    def replace_gaps(self, project_id: str, rows: list[dict[str, Any]]) -> None:
        self.client.table("gaps_opportunities").delete().eq("project_id", project_id).execute()
        if rows:
            self.client.table("gaps_opportunities").insert(rows).execute()

    def update_gap(self, project_id: str, gap_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        payload = {k: v for k, v in patch.items() if v is not None}
        result = (
            self.client.table("gaps_opportunities")
            .update(payload)
            .eq("id", gap_id)
            .eq("project_id", project_id)
            .execute()
        )
        rows = result.data or []
        if not rows:
            raise NotFoundError("That gap does not exist on this project.")
        return rows[0]

    # ----------------------------------------------------------- strategies

    def get_strategy(self, project_id: str) -> dict[str, Any] | None:
        result = (
            self.client.table("strategies")
            .select("*")
            .eq("project_id", project_id)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def insert_strategy(self, strategy: dict[str, Any]) -> dict[str, Any]:
        result = self.client.table("strategies").insert(strategy).execute()
        return (result.data or [strategy])[0]

    def update_strategy(self, strategy_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        result = self.client.table("strategies").update(patch).eq("id", strategy_id).execute()
        rows = result.data or []
        if not rows:
            raise NotFoundError("That strategy does not exist.")
        return rows[0]

    def clear_strategies(self, project_id: str) -> None:
        self.client.table("strategies").delete().eq("project_id", project_id).execute()

    # -------------------------------------------------------------- reviews

    def list_reviews(self, project_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("hitl_reviews")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at")
            .execute()
        )
        return result.data or []

    def insert_review(self, review: dict[str, Any]) -> dict[str, Any]:
        result = self.client.table("hitl_reviews").insert(review).execute()
        return (result.data or [review])[0]

    # ------------------------------------------------------------ documents

    def get_document(self, project_id: str) -> dict[str, Any] | None:
        result = (
            self.client.table("strategy_documents")
            .select("*")
            .eq("project_id", project_id)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None

    def insert_document(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.client.table("strategy_documents").insert(document).execute()
        return (result.data or [document])[0]

    # ---------------------------------------------------------- suggestions

    def list_suggestions(self, project_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("content_suggestions")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        return result.data or []

    def replace_suggestions(self, project_id: str, rows: list[dict[str, Any]]) -> None:
        self.client.table("content_suggestions").delete().eq("project_id", project_id).execute()
        if rows:
            self.client.table("content_suggestions").insert(rows).execute()

    def update_suggestion(
        self, project_id: str, suggestion_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        payload = {k: v for k, v in patch.items() if v is not None}
        result = (
            self.client.table("content_suggestions")
            .update(payload)
            .eq("id", suggestion_id)
            .eq("project_id", project_id)
            .execute()
        )
        rows = result.data or []
        if not rows:
            raise NotFoundError("That content suggestion does not exist on this project.")
        return rows[0]

    # ------------------------------------------------------------- pipeline

    def get_pipeline(self, project_id: str) -> dict[str, Any] | None:
        result = (
            self.client.table("pipeline_states")
            .select("*")
            .eq("project_id", project_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0]["state"] if rows else None

    def save_pipeline(self, project_id: str, state: dict[str, Any]) -> None:
        self.client.table("pipeline_states").upsert(
            {"project_id": project_id, "state": state, "updated_at": demo_data.iso()},
            on_conflict="project_id",
        ).execute()

    # --------------------------------------------------------- integrations

    def list_integrations(self) -> list[dict[str, Any]]:
        result = self.client.table("integrations").select("*").execute()
        return result.data or []

    def update_integration(self, integration_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        result = (
            self.client.table("integrations").update(patch).eq("id", integration_id).execute()
        )
        rows = result.data or []
        if not rows:
            raise NotFoundError("That integration does not exist.")
        return rows[0]

    # -------------------------------------------------------------- contact

    def insert_contact(self, submission: dict[str, Any]) -> None:
        self.client.table("contact_submissions").insert(submission).execute()


Repository = MemoryRepository | SupabaseRepository


def get_repository(user_id: str, token: str) -> Repository:
    """Picks the backend for a request path."""
    if settings.is_demo:
        return MemoryRepository(user_id)
    return SupabaseRepository(user_id, token)


def get_worker_repository(user_id: str) -> Repository:
    """Backend for the background pipeline worker.

    Uses the service role because the request that started the run has already
    returned and its JWT is gone. Never call this from a request handler.
    """
    if settings.is_demo:
        return MemoryRepository(user_id)
    return SupabaseRepository(user_id, token="", service=True)
