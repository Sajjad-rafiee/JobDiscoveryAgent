"""Build the wheel and exercise the installed artifact, not the source tree.

The project `.venv` holds an editable install that puts the repository root on
`sys.path`, so importing from it would pass even with a broken wheel. These
tests install the built wheel into a separate virtualenv and import from there
with the source tree kept off `sys.path`.

The wheel is installed with `--no-deps`; its third-party dependencies are made
visible by adding the test environment's site-packages as a plain path entry.
Python does not process `.pth` files found in such a path entry, so the editable
install hook that points at the source tree stays inactive. No network access
is needed beyond what `uv build` needs for the build backend.
"""

import json
import os
import shutil
import subprocess
import sys
import sysconfig
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_PACKAGES = {"agent", "api", "models", "tools", "utils"}
RUNTIME_MODULES = ("agent.graph", "api.client", "tools.job_search", "utils.config")

UV = os.environ.get("UV") or shutil.which("uv")

pytestmark = pytest.mark.skipif(UV is None, reason="uv is required to build the wheel")


def _run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        args, cwd=cwd, env=env, capture_output=True, text=True, timeout=300
    )
    assert completed.returncode == 0, (
        f"command failed: {' '.join(args)}\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    return completed.stdout


@pytest.fixture(scope="module")
def wheel_path(tmp_path_factory) -> Path:
    out_dir = tmp_path_factory.mktemp("dist")
    _run(UV, "build", "--wheel", "--out-dir", str(out_dir), cwd=PROJECT_ROOT)
    wheels = list(out_dir.glob("*.whl"))
    assert len(wheels) == 1, wheels
    return wheels[0]


def _wheel_names(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as archive:
        return archive.namelist()


def test_wheel_contains_all_runtime_packages(wheel_path):
    names = _wheel_names(wheel_path)

    for package in RUNTIME_PACKAGES:
        assert f"{package}/__init__.py" in names, f"{package} missing from wheel"
    for module in RUNTIME_MODULES + ("models.job",):
        assert module.replace(".", "/") + ".py" in names, f"{module} missing from wheel"


def test_wheel_contains_no_private_or_local_files(wheel_path):
    names = _wheel_names(wheel_path)
    top_level = {name.split("/", 1)[0] for name in names}
    dist_info = {entry for entry in top_level if entry.endswith(".dist-info")}

    assert len(dist_info) == 1
    assert top_level - dist_info == RUNTIME_PACKAGES
    assert not [name for name in names if name.endswith(".md")]
    assert not [name for name in names if Path(name).name.startswith(".env")]


def test_installed_wheel_imports_outside_source_tree(wheel_path, tmp_path):
    venv = tmp_path / "venv"
    _run(UV, "venv", "--python", sys.executable, str(venv), cwd=tmp_path)
    venv_python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    _run(
        UV, "pip", "install", "--no-deps", "--python", str(venv_python), str(wheel_path),
        cwd=tmp_path,
    )

    venv_site_packages = Path(
        _run(
            str(venv_python), "-I", "-c",
            "import sysconfig; print(sysconfig.get_path('purelib'))",
            cwd=tmp_path,
        ).strip()
    )
    dependencies = sysconfig.get_path("purelib")
    (venv_site_packages / "zz_test_dependencies.pth").write_text(dependencies + "\n")

    check = (
        "import importlib, json, sys\n"
        f"modules = {list(RUNTIME_MODULES)!r}\n"
        "files = {m: importlib.import_module(m).__file__ for m in modules}\n"
        "print(json.dumps({'files': files, 'sys_path': sys.path}))\n"
    )
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
    # -I: isolated mode, so neither the cwd nor PYTHONPATH is added to sys.path.
    output = _run(str(venv_python), "-I", "-c", check, cwd=tmp_path, env=env)
    report = json.loads(output.strip().splitlines()[-1])

    assert str(PROJECT_ROOT) not in report["sys_path"]
    for module, file in report["files"].items():
        path = Path(file).resolve()
        assert venv_site_packages.resolve() in path.parents, f"{module} imported from {path}"
        assert PROJECT_ROOT not in path.parents, f"{module} imported from source tree"
