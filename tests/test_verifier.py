from kuro.agents.verifier import DifferentialParityVerifier
from kuro.sandbox.runner import DockerSandboxRunner


def test_normalize_stdout():
    runner = DockerSandboxRunner()
    verifier = DifferentialParityVerifier(runner)

    # Legacy binary help text
    legacy_out = "Usage: ./cipher [-e|-d] <text> [-k <key>]\nOptions:\n  -h, --help  Show this help message"
    # Modern python help text
    modern_out = "Usage: python3 main.py [-e|-d] <text> [-k <key>]\nOptions:\n  -h, --help  Show this help message"

    norm_legacy = verifier._normalize_stdout(
        legacy_out, legacy_bin_path="/path/to/cipher", modern_entry_file="main.py"
    )
    norm_modern = verifier._normalize_stdout(
        modern_out, legacy_bin_path="/path/to/cipher", modern_entry_file="main.py"
    )

    assert norm_legacy == norm_modern
    assert "[PROG]" in norm_legacy
    assert "./cipher" not in norm_legacy
    assert "python3 main.py" not in norm_modern


def test_normalize_stdout_stripped_binary():
    runner = DockerSandboxRunner()
    verifier = DifferentialParityVerifier(runner)

    legacy_out = "Usage: ./cipher_stripped [-e|-d] <text>"
    modern_out = "Usage: python3 -B main.py [-e|-d] <text>"

    norm_legacy = verifier._normalize_stdout(
        legacy_out, legacy_bin_path="/path/to/cipher_stripped", modern_entry_file="main.py"
    )
    norm_modern = verifier._normalize_stdout(
        modern_out, legacy_bin_path="/path/to/cipher_stripped", modern_entry_file="main.py"
    )

    assert norm_legacy == norm_modern
