"""The source licence is PolyForm Strict 1.0.0 (`DECISIONS.md` D22), in one text.

PEP 639 reads `license-files` relative to each package, so every package carries a copy of the
root `LICENSE`. A copy that drifts from the root, or a metadata field that names another licence,
fails here rather than shipping in a wheel.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGES = ("truestill-core", "truestill-cli", "truestill-app")


def test_every_package_licence_file_is_the_root_text() -> None:
    root = (ROOT / "LICENSE").read_bytes()
    for name in PACKAGES:
        assert (ROOT / "packages" / name / "LICENSE").read_bytes() == root, name


def test_every_package_declares_the_polyform_strict_licenseref() -> None:
    for name in PACKAGES:
        project = tomllib.loads((ROOT / "packages" / name / "pyproject.toml").read_text("utf-8"))[
            "project"
        ]
        assert project["license"] == "LicenseRef-PolyForm-Strict-1.0.0", name
        assert project["license-files"] == ["LICENSE"], name


def test_the_root_licence_is_polyform_strict_with_its_required_notices() -> None:
    lines = (ROOT / "LICENSE").read_text("utf-8").splitlines()
    assert lines[0] == "Required Notice: Copyright 2026 Dinesh Allimuthu"
    assert lines[1].startswith("Required Notice: Free for personal and other noncommercial use.")
    assert "# PolyForm Strict License 1.0.0" in lines
