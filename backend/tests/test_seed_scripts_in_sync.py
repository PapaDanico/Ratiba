"""Guard: backend/scripts/ must stay byte-identical to the repo-root scripts/.

The ratiba-api Docker image builds from the ``backend/`` context and ships
``backend/scripts/``, while local/dev tooling and docs use the repo-root
``scripts/``. If the two drift, a seed edited in one place silently misses the
deployed image — which once shipped without the Jetways seed, leaving
``officer@jetways.example.aero`` unseeded (a clean 401 at login). This test
fails loudly if they ever diverge again.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ROOT_SCRIPTS = _REPO_ROOT / "scripts"
_BACKEND_SCRIPTS = _REPO_ROOT / "backend" / "scripts"

_SHARED_FILES = ["seed.py", "seed_jetways.py", "generate_sample_om_a.py"]


@pytest.mark.parametrize("name", _SHARED_FILES)
def test_seed_script_copies_match(name: str) -> None:
    root_file = _ROOT_SCRIPTS / name
    backend_file = _BACKEND_SCRIPTS / name
    assert root_file.exists(), f"missing {root_file}"
    assert backend_file.exists(), (
        f"missing {backend_file} — the API image ships backend/scripts/, "
        "so this file must exist there too."
    )
    assert root_file.read_bytes() == backend_file.read_bytes(), (
        f"{name} differs between scripts/ and backend/scripts/. "
        "Keep them in sync — the ratiba-api Docker image ships backend/scripts/."
    )
