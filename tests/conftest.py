from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path() -> Path:
    """Use a repo-local temp folder on Windows setups with locked system temp dirs."""
    path = Path("pytest_tmp_local") / uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    return path.resolve()
