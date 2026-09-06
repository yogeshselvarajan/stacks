# scripts/build_deployment_package.py
"""Builds the AgentCore Runtime direct-code-deployment .zip. AgentCore
Runtime's code_configuration path is arm64/aarch64 Linux only, regardless
of this script's own host OS -- pip's --platform/--only-binary flags
download prebuilt wheels for that target, no cross compilation needed.
Copies src/stacks and main.py into the package root alongside the
installed dependencies, then zips the result. Run manually:

    python scripts/build_deployment_package.py
"""
from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = REPO_ROOT / "build" / "deployment_package"
ZIP_PATH = REPO_ROOT / "build" / "deployment_package.zip"

# Mirrors pyproject.toml's own dependency list. Kept as an explicit list
# here (rather than parsing pyproject.toml) so this script has no extra
# parsing dependency of its own.
DEPENDENCIES = [
    "pydantic>=2.7",
    "strands-agents",
    "boto3>=1.40",
    "bedrock-agentcore>=1.15",
    "PyJWT[crypto]>=2.10",
]


def main() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    # Deliberately uv, not pip, for this cross-platform install -- found
    # by direct execution (Task 6), not assumed: plain "pip install
    # --platform manylinux2014_aarch64 --python-version 3.13
    # --only-binary=:all:" downloads wheels for the right target, but
    # pip's resolver still evaluates environment markers (such as mcp's
    # "pywin32>=310; sys_platform == 'win32'") against THIS HOST's own
    # sys_platform, not the target platform's. On a Windows build host
    # that marker looks satisfied, pip goes looking for a pywin32 wheel
    # for aarch64 Linux (which does not exist and never will), and its
    # backtracking resolver silently downgrades strands-agents all the
    # way down to 1.1.0 (pulling in mcp 1.10.1) to find a version whose
    # metadata does not carry that marker at all -- with no error, no
    # warning naming strands-agents, just a badly outdated package
    # actually written to BUILD_DIR. That is a materially different
    # Strands SDK version than the one this whole codebase was built and
    # SDK-introspection-verified against (1.32.0+, see agent.py and
    # overdue_sequencer.py's own verification notes) -- HITL
    # interrupt/resume and S3SessionManager's read_agent/create_agent/
    # update_agent API are not guaranteed to exist or behave the same way
    # at 1.1.0. uv's "--python-platform" flag sets a full target marker
    # environment (not just wheel-tag matching), so it resolves markers
    # correctly for the actual deployment target and was confirmed by
    # direct side-by-side testing to resolve strands-agents to its
    # current release with a compatible mcp, no pywin32 detour. Fails
    # loudly if uv is not installed, rather than silently falling back to
    # the broken pip path above.
    if shutil.which("uv") is None:
        raise RuntimeError(
            "uv is required to build this deployment package (pip's cross-platform "
            "resolver mis-evaluates sys_platform-gated markers like mcp's pywin32 "
            "requirement against this host, not the aarch64 Linux target -- see this "
            "function's own comment). Install uv: https://docs.astral.sh/uv/getting-started/installation/"
        )

    subprocess.run(
        [
            "uv", "pip", "install",
            "--python-platform", "aarch64-manylinux2014",
            "--python-version", "3.13",
            "--target", str(BUILD_DIR),
            "--only-binary=:all:",
            *DEPENDENCIES,
        ],
        check=True,
    )

    shutil.copytree(REPO_ROOT / "src" / "stacks", BUILD_DIR / "stacks")
    shutil.copy(REPO_ROOT / "main.py", BUILD_DIR / "main.py")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in BUILD_DIR.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(BUILD_DIR))

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"Built {ZIP_PATH} ({size_mb:.1f} MB). AgentCore Runtime's own limit is 250 MB zipped.")
    if size_mb > 250:
        raise RuntimeError("deployment package exceeds AgentCore Runtime's 250 MB zipped limit")


if __name__ == "__main__":
    main()
