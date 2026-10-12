"""Static checks for operational shell scripts (no Docker or cluster required)."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_docker_images_script_fails_fast_without_sibling_repos(tmp_path: Path) -> None:
    """The build helper should exit before invoking docker when engine sources are missing."""
    script = ROOT / "scripts" / "build-docker-images.sh"
    fake_root = tmp_path / "orchestration"
    fake_scripts = fake_root / "scripts"
    fake_scripts.mkdir(parents=True)
    fake_script = fake_scripts / "build-docker-images.sh"
    fake_script.write_text(script.read_text(encoding="utf-8"), encoding="utf-8")
    fake_script.chmod(0o755)

    result = subprocess.run(
        [str(fake_script)],
        cwd=fake_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "ml-trading-app-cpp" in output or "Dockerfile.prod not found" in output


def test_build_docker_images_script_uses_release_build_for_engine() -> None:
    """Production engine images must be built with the Release CMake configuration."""
    script = (ROOT / "scripts" / "build-docker-images.sh").read_text(encoding="utf-8")
    assert "set -e" in script.splitlines()[0] or "set -e" in script
    assert "--build-arg CMAKE_BUILD_TYPE=Release" in script


def test_deploy_script_namespace_matches_manifest() -> None:
    """deploy.sh and namespace.yaml must agree on the target namespace name."""
    deploy = (ROOT / "k8s/deploy.sh").read_text(encoding="utf-8")
    namespace = (ROOT / "k8s/base/namespace.yaml").read_text(encoding="utf-8")
    match = re.search(r'NAMESPACE="([^"]+)"', deploy)
    assert match is not None
    assert f"name: {match.group(1)}" in namespace


def test_setup_test_db_requires_password_before_psql() -> None:
    """Local DB bootstrap must refuse to run without POSTGRES_PASSWORD."""
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "setup_test_db.sh")],
        cwd=ROOT,
        env={"PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "POSTGRES_PASSWORD" in result.stderr
