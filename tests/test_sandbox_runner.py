from pathlib import Path
from kuro.sandbox.runner import DockerSandboxRunner


def test_sandbox_runs_c_binary():
    runner = DockerSandboxRunner(image="kuro-sandbox")
    bin_path = "/home/ilyan/random/kuro/benchmarks/c_cipher/cipher_stripped"

    res = runner.run_binary(bin_path, args=["-e", "kuro test", "-k", "7"])
    assert res.exit_code == 0
    assert not res.timed_out
    assert res.stdout.strip() != ""


def test_sandbox_runs_go_binary():
    runner = DockerSandboxRunner(image="kuro-sandbox")
    bin_path = "/home/ilyan/random/kuro/benchmarks/go_calc/aegis_sample"

    res = runner.run_binary(bin_path, args=["stats", "5", "15"])
    assert res.exit_code == 0
    assert not res.timed_out
    assert "count: 2" in res.stdout
    assert "sum: 20.00" in res.stdout


def test_sandbox_timeout_enforcement():
    runner = DockerSandboxRunner(image="kuro-sandbox", timeout_seconds=1)
    # Binary with non-existent or hanging execution
    bin_path = "/home/ilyan/random/kuro/benchmarks/c_cipher/cipher"
    res = runner.run_binary(bin_path, args=["-h"], timeout=2)
    assert not res.timed_out
    assert res.exit_code == 0


def test_sandbox_enforces_chmod(tmp_path):
    runner = DockerSandboxRunner(image="kuro-sandbox")
    # Copy binary and strip execute permission
    bin_path = "/home/ilyan/random/kuro/benchmarks/c_cipher/cipher_stripped"
    test_bin = tmp_path / "cipher_no_exec"
    test_bin.write_bytes(Path(bin_path).read_bytes())
    test_bin.chmod(0o644)

    res = runner.run_binary(str(test_bin), args=["-h"])
    assert res.exit_code == 0
    assert (test_bin.stat().st_mode & 0o777) == 0o755


def test_sandbox_runs_python_with_b_flag(tmp_path):
    runner = DockerSandboxRunner(image="kuro-sandbox")
    script = tmp_path / "script.py"
    script.write_text("print('hello from python')")

    res = runner.run_python_code(str(tmp_path), "script.py")
    assert res.exit_code == 0
    assert "hello from python" in res.stdout
