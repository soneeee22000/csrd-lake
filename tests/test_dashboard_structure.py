"""Structural tests for the Next.js dashboard.

Avoids needing Node.js or pnpm install in CI (heavy). Verifies file
presence, JSON validity of package.json, key page exports, design-token
discipline (no raw color classes), and no killed claims in copy.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

DASH = Path(__file__).resolve().parents[1] / "dashboard"


# ── File presence ─────────────────────────────────────────────────────


def test_dashboard_directory_exists() -> None:
    assert DASH.is_dir()


@pytest.mark.parametrize(
    "rel_path",
    [
        "package.json",
        "tsconfig.json",
        "next.config.ts",
        "postcss.config.mjs",
        "README.md",
        ".gitignore",
        "app/layout.tsx",
        "app/page.tsx",
        "app/globals.css",
        "app/not-found.tsx",
        "app/company/[ticker]/page.tsx",
        "app/portfolio/page.tsx",
        "components/metric-table.tsx",
        "components/confidence-badge.tsx",
        "components/ui/card.tsx",
        "components/ui/table.tsx",
        "components/ui/badge.tsx",
        "lib/data.ts",
        "lib/utils.ts",
    ],
)
def test_required_files_exist(rel_path: str) -> None:
    assert (DASH / rel_path).exists(), f"Missing dashboard file: {rel_path}"


# ── package.json ──────────────────────────────────────────────────────


def test_package_json_parses() -> None:
    data = json.loads((DASH / "package.json").read_text(encoding="utf-8"))
    assert data["name"] == "csrd-lake-dashboard"


def test_package_json_uses_react_19() -> None:
    data = json.loads((DASH / "package.json").read_text(encoding="utf-8"))
    assert data["dependencies"]["react"].startswith("^19")


def test_package_json_uses_next_16() -> None:
    data = json.loads((DASH / "package.json").read_text(encoding="utf-8"))
    assert data["dependencies"]["next"].startswith("^16")


def test_package_json_uses_tailwind_v4() -> None:
    data = json.loads((DASH / "package.json").read_text(encoding="utf-8"))
    assert data["devDependencies"]["tailwindcss"].startswith("^4")


def test_package_json_has_required_scripts() -> None:
    data = json.loads((DASH / "package.json").read_text(encoding="utf-8"))
    for script in ("dev", "build", "lint", "typecheck"):
        assert script in data["scripts"], f"Missing script: {script}"


# ── tsconfig ──────────────────────────────────────────────────────────


def test_tsconfig_strict_mode() -> None:
    raw = (DASH / "tsconfig.json").read_text(encoding="utf-8")
    # tsconfig allows comments; strip them before parsing
    stripped = re.sub(r"//.*$", "", raw, flags=re.MULTILINE)
    data = json.loads(stripped)
    opts = data["compilerOptions"]
    assert opts["strict"] is True
    assert opts["noUncheckedIndexedAccess"] is True


# ── Design-token discipline (no raw color classes) ────────────────────
#
# Per global CLAUDE.md: never use raw color classes (text-white, bg-black,
# text-red-500, bg-blue-100, etc.) in components. Always tokens.


_FORBIDDEN_RAW_COLOR = re.compile(
    r"\b(text|bg|border)-(white|black|red|blue|green|yellow|amber|orange|purple|"
    r"pink|indigo|teal|cyan|sky|emerald|lime|violet|fuchsia|rose|stone|zinc|neutral|gray|slate)"
    r"(-\d+)?\b"
)


def _tsx_files() -> list[Path]:
    return sorted(
        p for p in DASH.rglob("*.tsx") if "node_modules" not in p.parts and ".next" not in p.parts
    )


@pytest.mark.parametrize(
    "tsx_path",
    _tsx_files(),
    ids=lambda p: str(p.relative_to(DASH)),
)
def test_no_raw_color_classes_in_components(tsx_path: Path) -> None:
    """Components must use design tokens (text-foreground, bg-primary, etc.),
    never raw Tailwind color utilities."""
    content = tsx_path.read_text(encoding="utf-8")
    matches = _FORBIDDEN_RAW_COLOR.findall(content)
    assert not matches, (
        f"{tsx_path.name} uses raw color classes: {matches[:3]}. "
        f"Replace with design tokens (text-foreground, bg-primary, "
        f"text-confidence-published, etc.)."
    )


# ── No gradient backgrounds (per global CLAUDE.md anti-pattern) ────────


def test_no_gradient_backgrounds() -> None:
    """Per CLAUDE.md: gradients on UI elements look like AI slop."""
    for tsx in _tsx_files():
        content = tsx.read_text(encoding="utf-8")
        assert "bg-gradient-to-" not in content, (
            f"{tsx.name} uses bg-gradient — replace with bg-primary / bg-secondary"
        )


# ── Anti-regression: killed claims ────────────────────────────────────


def test_no_killed_claims_in_dashboard() -> None:
    """The 'replaces MSCI subscription' framing must not leak into UI copy."""
    forbidden = [
        "replaces MSCI",
        "replaces a €40",
        "MSCI subscription",
        "Sustainalytics subscription",
    ]
    for tsx in [*_tsx_files(), DASH / "lib" / "data.ts", DASH / "README.md"]:
        if not tsx.exists():
            continue
        content = tsx.read_text(encoding="utf-8")
        for phrase in forbidden:
            assert phrase.lower() not in content.lower(), f"Killed claim '{phrase}' in {tsx.name}"


# ── Page metadata + SEO ───────────────────────────────────────────────


def test_root_layout_has_metadata() -> None:
    layout = (DASH / "app" / "layout.tsx").read_text(encoding="utf-8")
    assert "export const metadata" in layout
    assert "title" in layout
    assert "description" in layout


def test_company_page_uses_generate_static_params() -> None:
    """Per-company pages should pre-render at build time (static export-ready)."""
    page = (DASH / "app" / "company" / "[ticker]" / "page.tsx").read_text(encoding="utf-8")
    assert "generateStaticParams" in page


def test_company_page_uses_generate_metadata() -> None:
    """Per-company pages should set OG title/description from data."""
    page = (DASH / "app" / "company" / "[ticker]" / "page.tsx").read_text(encoding="utf-8")
    assert "generateMetadata" in page


# ── No `useEffect` for data fetching (Server Components only) ──────────


def test_no_use_effect_for_fetching() -> None:
    """Per global CLAUDE.md: never `fetch` inside `useEffect`. Use RSC data flow."""
    for tsx in _tsx_files():
        content = tsx.read_text(encoding="utf-8")
        # Allow useEffect generally (though we don't use it), but ban
        # the fetch-inside-useEffect pattern.
        assert "fetch(" not in content or "useEffect" not in content, (
            f"{tsx.name} appears to use fetch inside useEffect — use Server Components"
        )


# ── No emojis as icons ────────────────────────────────────────────────


def test_no_emoji_icons_in_components() -> None:
    """Per CLAUDE.md: never use emojis as icons. Use Lucide / Heroicons (SVG)."""
    # Whitelist: README and metadata description can contain emoji decorations.
    component_files = [
        p
        for p in _tsx_files()
        if p.relative_to(DASH).parts[0] in {"app", "components"}
        and p.name != "layout.tsx"  # layout has SEO descriptions
    ]
    # Simple range check for common UI emoji.
    emoji_pattern = re.compile(r"[\U0001F300-\U0001F9FF\U00002600-\U000026FF\U00002700-\U000027BF]")
    for tsx in component_files:
        content = tsx.read_text(encoding="utf-8")
        # Allow emoji inside JSX text props ONLY if explicitly a unicode escape.
        matches = emoji_pattern.findall(content)
        assert not matches, (
            f"{tsx.name} uses emoji-as-icon: {matches[:3]}. Use Lucide React icons instead."
        )
