from kuro.agents.inspector import BinaryInspector
from kuro.agents.probe import DynamicRuntimeProbe
from kuro.sandbox.runner import DockerSandboxRunner


def test_probe_on_c_cipher():
    runner = DockerSandboxRunner(image="kuro-sandbox")
    inspector = BinaryInspector("/home/ilyan/random/kuro/benchmarks/c_cipher/cipher")
    inspection_report = inspector.inspect()

    probe = DynamicRuntimeProbe(runner)
    probe_report = probe.probe("/home/ilyan/random/kuro/benchmarks/c_cipher/cipher", inspection_report)

    assert "-e" in probe_report.supported_flags
    assert "-d" in probe_report.supported_flags
    assert "-k" in probe_report.supported_flags
    assert probe_report.help_text is not None
    assert "Usage:" in probe_report.help_text


def test_probe_on_go_calc():
    runner = DockerSandboxRunner(image="kuro-sandbox")
    inspector = BinaryInspector("/home/ilyan/random/kuro/benchmarks/go_calc/aegis_sample")
    inspection_report = inspector.inspect()

    probe = DynamicRuntimeProbe(runner)
    probe_report = probe.probe("/home/ilyan/random/kuro/benchmarks/go_calc/aegis_sample", inspection_report)

    assert "reverse" in probe_report.detected_subcommands or "stats" in probe_report.detected_subcommands
    assert probe_report.help_text is not None
    assert "aegis_sample" in probe_report.help_text


def test_probe_defaults_stdin_to_empty_string():
    runner = DockerSandboxRunner(image="kuro-sandbox")
    inspector = BinaryInspector("/home/ilyan/random/kuro/benchmarks/c_cipher/cipher")
    inspection_report = inspector.inspect()

    probe = DynamicRuntimeProbe(runner)
    probe_report = probe.probe("/home/ilyan/random/kuro/benchmarks/c_cipher/cipher", inspection_report)

    assert len(probe_report.sample_runs) > 0
    for run in probe_report.sample_runs:
        assert run.stdin_input == ""
        assert not run.timed_out
