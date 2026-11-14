"""Package only the modules and pinned dependencies required by solution.py."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
FILES = ("solution.py", "assistant.py", "knowledge.py", "llm.py", "schemas.py", "settings.py")
DEPENDENCIES = {"httpx", "pydantic", "python-dotenv"}
MAX_BYTES = 128_000_000


def build(output: Path) -> None:
    sources = {name: (ROOT / name).read_bytes() for name in FILES}
    pins = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    requirements = sorted(pin for pin in pins if pin.split("==")[0] in DEPENDENCIES)
    if len(requirements) != len(DEPENDENCIES) or any("==" not in pin for pin in requirements):
        raise ValueError("Missing pinned submission dependencies")
    sources["requirements.txt"] = ("\n".join(requirements) + "\n").encode("utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as archive:
            for name, source in sources.items():
                archive.writestr(name, source)
        if temporary.stat().st_size > MAX_BYTES:
            raise ValueError("Submission exceeds 128 MB")
        with ZipFile(temporary) as archive:
            if archive.namelist() != list(sources) or archive.testzip() is not None:
                raise ValueError("Invalid submission archive")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    output = parser.parse_args().output
    build(output)
    print(output.resolve())
