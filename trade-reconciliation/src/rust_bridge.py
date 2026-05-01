import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def run_rust_core(fidelity_path: Path, trades_path: Path, project_root: Path) -> dict | None:
    cargo = shutil.which("cargo")
    manifest = project_root / "rust-core" / "Cargo.toml"
    if not cargo or not manifest.exists():
        return None

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        out_path = Path(tmp.name)

    command = [
        cargo,
        "run",
        "--release",
        "--manifest-path",
        str(manifest),
        "--",
        str(fidelity_path),
        str(trades_path),
        str(out_path),
    ]
    try:
        subprocess.run(command, check=True, cwd=project_root, capture_output=True, text=True)
        return json.loads(out_path.read_text(encoding="utf-8"))
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
        return None
    finally:
        out_path.unlink(missing_ok=True)
