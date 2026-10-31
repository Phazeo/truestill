"""`repo_sources` must see the file the current commit is adding. **The whole point of it.**

⚠ **A SHAPE ASSERTION WOULD NOT BE ENOUGH, so this creates a real untracked file.** Checking that
the argument list contains `--others` proves the string is there, not that the listing widens -
and the defect being closed was precisely a listing that looked right and was blind. So a file is
written into a throwaway repository of the test's own and enumerated there (never into the real
tree: other workers read it, issue #6).

The state under test cannot be reached any other way: on a clean tree there is nothing untracked,
so a `repo_sources` with `--others` removed would pass every other test in the suite. That is why
this file exists rather than the guarantee resting on the twelve callers.
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path

import pytest

import repo_sources

#: Where the REAL tree's source files live. Only ever READ here: see the watcher test below.
_REAL_SRC = repo_sources.REPO / "packages" / "truestill-core" / "src" / "truestill_core"
_PROBE_NAME = "_census_probe.py"
_PROBE_RELATIVE = "packages/truestill-core/src/truestill_core/" + _PROBE_NAME


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway git repository with one tracked source file, standing in for the real one.

    ⚠ **Why not the real tree (issue #6).** These tests used to write their probe into
    ``packages/truestill-core/src/`` and remove it in a ``finally``. Under ``pytest -n auto`` another
    worker listing or reading that folder in the same moment saw the probe and then failed with
    ``FileNotFoundError`` when it vanished: a test that other tests can observe must not write
    where they look. ``repo_sources.REPO`` is read at call time, so pointing it at a repository of
    their own proves the same property (``--others`` widens the listing) with nothing shared.
    """
    root = tmp_path / "repo"
    source = root / "packages" / "truestill-core" / "src" / "truestill_core"
    source.mkdir(parents=True)
    (root / ".gitignore").write_text(".scratch/\n", encoding="utf-8")
    (source / "real.py").write_text("# tracked\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    monkeypatch.setattr(repo_sources, "REPO", root)
    return root


def _write_probe(tree: Path) -> Path:
    probe = tree / _PROBE_RELATIVE
    probe.write_text("# written by a test, in its own repository\n", encoding="utf-8")
    return probe


def test_an_untracked_source_file_is_in_the_listing(tree: Path) -> None:
    """The hole, closed. This file is in no index; the census must still find it."""
    probe = _write_probe(tree)

    assert _PROBE_RELATIVE in repo_sources.paths("packages/*/src/**/*.py")
    assert _PROBE_RELATIVE in repo_sources.paths()
    assert probe in repo_sources.files("packages/*/src/**/*.py")


def test_the_probe_really_was_invisible_to_the_index(tree: Path) -> None:
    """⚠ **The anti-vacuity half, and without it the test above proves nothing.**

    If the probe were somehow tracked, the assertion above would pass on a `repo_sources` that had
    never been widened at all. So the same file is checked against git's own index: it must be
    absent there and present in the listing, which is the difference this module exists for.
    """
    _write_probe(tree)

    indexed = subprocess.run(
        ["git", "ls-files", "--", _PROBE_RELATIVE],
        cwd=tree,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert indexed == [], "the probe is tracked, so this proves nothing about untracked files"
    assert _PROBE_RELATIVE in repo_sources.paths()


@pytest.mark.usefixtures("tree")
def test_a_tracked_file_is_still_listed() -> None:
    """The other half of the census: widening it did not drop what was always there."""
    assert "packages/truestill-core/src/truestill_core/real.py" in repo_sources.paths()


def test_an_ignored_file_stays_invisible(tree: Path) -> None:
    """⚠ **The cry-wolf half: a guard that went red on scratch would be worse than the hole.**

    `.gitignore` designates `.scratch/` for *"local scratch notes and throwaway files"*, and
    `--exclude-standard` is what keeps that promise. Without it every developer's scratch would
    enter twelve guards at once.
    """
    scratch = tree / ".scratch"
    scratch.mkdir()
    probe = scratch / "notes.py"
    probe.write_text("# scratch: truestill drives --init /somewhere\n", encoding="utf-8")

    assert probe.is_file(), "the probe was not written, so its absence below is free"
    assert probe.relative_to(tree).as_posix() not in repo_sources.paths()


def test_every_path_returned_can_actually_be_opened() -> None:
    """Every path handed to a caller is a readable file, so a guard can open it without guarding.

    ⚠ **This is weaker than it looks, and the weakness is stated rather than implied.** The
    filter it exercises is there for a path **staged for deletion**, and a mutation run proved
    nothing here catches that: removing the filter survives the suite, because reaching the state
    needs a staged deletion and staging one would mutate the shared index while `make check` runs
    fourteen workers against it. `repo_sources`' own docstring carries the full reason.

    This one reads the REAL tree and writes nothing to it.
    """
    listed = repo_sources.files("*.py")

    assert listed, "an empty listing would make the loop below free"
    assert all(path.is_file() for path in listed)


def test_these_tests_never_put_a_file_in_the_shared_tree(tree: Path) -> None:
    """⚠ The regression for issue #6: while the probe tests' work runs, the REAL source folder never
    holds the probe. A watcher polls it; the probe's name must never appear there.
    """
    seen = threading.Event()
    stop = threading.Event()

    def watch() -> None:
        while not stop.is_set():
            if (_REAL_SRC / _PROBE_NAME).exists():
                seen.set()
                return

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        test_an_untracked_source_file_is_in_the_listing(tree)
        test_the_probe_really_was_invisible_to_the_index(tree)
    finally:
        stop.set()
        watcher.join(timeout=5)

    assert not seen.is_set(), "a probe test wrote a file into the shared source tree"
