"""Atomic single-file replacement shared by all export formats."""

import os
import tempfile
from pathlib import Path


def write_atomic(path: str | Path, data: bytes) -> None:
    """Finish and sync a sibling temporary file before replacing the destination."""
    target = Path(path)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
