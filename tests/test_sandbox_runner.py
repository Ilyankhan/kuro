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
