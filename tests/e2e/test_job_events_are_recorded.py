"""A failed e2e test leaves behind what its job streams delivered, not only the requests.

Why: on 2026-10-31 a WebKit run started an organize (``POST /api/organize/run`` answered 200) and
the screen never showed the result. The Playwright trace records requests but not the frames
inside an event stream, so nobody could say whether the end of the job reached the page. The
recording (``e2e_support.record_job_events``) is attached to a failed test's artifacts by
``conftest.pytest_runtest_makereport``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from e2e_support import job_events_seen, save_job_events
from playwright.sync_api import Page, expect


def _run_a_job(ui: Page, library) -> None:
    """The duplicate check: the first step of an organize that runs as a job (the inventory before
    it is a plain request and opens no stream)."""
    source = library(3, name="Pictures")
    ui.fill("#org-source", str(source))
    ui.fill("#org-dest", str(source.parent / "Out"))
    ui.click("#org-preview")
    expect(ui.locator("#org-result")).to_contain_text("3 photos found")
    ui.click("#org-dedup")
    expect(ui.locator("#org-confirm [data-typed-confirm]")).to_be_visible()


def test_a_job_stream_is_recorded_from_open_to_its_end(ui: Page, library) -> None:
    _run_a_job(ui, library)

    seen = job_events_seen(ui)
    kinds = [line["kind"] for line in seen]
    assert "open" in kinds, f"no stream was recorded: {seen}"
    ended = [line for line in seen if line["kind"] == "message" and line.get("type") == "done"]
    assert ended, f"the end of the job was not recorded: {seen}"
    assert ended[-1]["status"] == "done"
    assert kinds.index("open") < kinds.index("message"), "messages recorded before the open"
    # Each line names its job, so the records of one stream can be told from another's.
    assert all(re.fullmatch(r"[0-9a-f]{32}", line["job"]) for line in seen), seen


def test_the_recording_never_carries_a_file_name_or_the_token(ui: Page, library) -> None:
    _run_a_job(ui, library)

    seen = job_events_seen(ui)
    assert seen, "nothing was recorded, so this test would pass for the wrong reason"
    text = json.dumps(seen)
    assert "IMG_" not in text, "a file name reached the recording"
    assert ".jpg" not in text, "a file name reached the recording"
    assert "token" not in text.lower(), "the session token reached the recording"


def test_the_recording_is_saved_beside_the_trace(ui: Page, library, tmp_path: Path) -> None:
    _run_a_job(ui, library)

    path = save_job_events(
        ui, tmp_path / "job-events", "tests/e2e/test_golden_path.py::test_x[webkit]"
    )

    assert path.parent == tmp_path / "job-events"
    assert path.name == "tests-e2e-test_golden_path.py-test_x-webkit.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert any(line.get("type") == "done" for line in saved)
