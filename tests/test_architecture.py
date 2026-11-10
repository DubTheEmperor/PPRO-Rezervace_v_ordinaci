"""Architektonický test: vynucuje striktně jednosměrné závislosti vrstev.

Prezentace → Byznys → Infrastruktura. Test staticky projde importy (AST)
všech modulů dané vrstvy a selže při importu zakázaného směrem.
"""
import ast
import sys
from pathlib import Path
import pytest

SRC = Path(__file__).resolve().parent.parent / "src"

FORBIDDEN = {
    # Byznys nesmí znát prezentaci ani webový framework
    "business": ("src.presentation", "fastapi", "starlette"),
    # Datová vrstva nesmí znát žádnou vyšší vrstvu ani web
    "infrastructure": ("src.business", "src.presentation", "fastapi", "starlette"),
    # Prezentace přistupuje k datům výhradně přes byznys vrstvu
    "presentation": ("src.infrastructure",),
}


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module


def _violations(layer: str):
    forbidden = FORBIDDEN[layer]
    for path in sorted((SRC / layer).rglob("*.py")):
        for lineno, module in _imports(path):
            if any(module == f or module.startswith(f + ".") for f in forbidden):
                yield f"{path.relative_to(SRC.parent)}:{lineno} importuje '{module}'"


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_dependencies_point_only_downwards(layer):
    violations = list(_violations(layer))
    assert not violations, "Porušení třívrstvé architektury:\n" + "\n".join(violations)


def test_architecture_check_detects_violation(tmp_path, monkeypatch):
    """Kontrola samotného testu – zakázaný import musí být odhalen."""
    fake_layer = tmp_path / "src" / "business"
    fake_layer.mkdir(parents=True)
    (fake_layer / "bad.py").write_text("from fastapi import HTTPException\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "SRC", tmp_path / "src")
    violations = list(_violations("business"))
    assert len(violations) == 1
    assert "bad.py:1 importuje 'fastapi'" in violations[0]
