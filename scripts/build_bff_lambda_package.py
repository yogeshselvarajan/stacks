# scripts/build_bff_lambda_package.py
"""Builds the BFF's Lambda deployment .zip (Lambda Function URL target,
arm64/Python 3.13, matching the agent's own build_deployment_package.py
platform choice). Copies bff/, src/stacks, and lambda_handler.py into the
package root alongside the installed dependencies, then zips the result.

    python scripts/build_bff_lambda_package.py
"""
from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = REPO_ROOT / "build" / "bff_lambda_package"
ZIP_PATH = REPO_ROOT / "build" / "bff_lambda_package.zip"

DEPENDENCIES = [
    "fastapi>=0.135",
    "pydantic>=2.7",
    "boto3>=1.40",
    "bedrock-agentcore>=1.15",
    "PyJWT[crypto]>=2.10",
    "mangum>=0.19",
    # Not used directly by the BFF's own logic, but stacks.hooks.audit_log
    # (imported transitively for its AuditLogSink type) also imports
    # strands.hooks at module load time, so it is a real, unavoidable
    # import-time dependency of this package, not an unused one.
    "strands-agents",
]


def main() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    if shutil.which("uv") is None:
        raise RuntimeError("uv is required to build this deployment package (see build_deployment_package.py's own comment).")

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
    shutil.copytree(REPO_ROOT / "bff", BUILD_DIR / "bff")
    shutil.copy(REPO_ROOT / "lambda_handler.py", BUILD_DIR / "lambda_handler.py")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in BUILD_DIR.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(BUILD_DIR))

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"Built {ZIP_PATH} ({size_mb:.1f} MB).")
    if size_mb > 250:
        raise RuntimeError("deployment package exceeds Lambda's 250 MB unzipped limit")


if __name__ == "__main__":
    main()
