import shutil
from pathlib import Path
from kuro.agents.inspector import BinaryInspector
from kuro.agents.probe import DynamicRuntimeProbe
from kuro.agents.synthesizer import CodeSynthesizer
from kuro.sandbox.runner import DockerSandboxRunner


def test_synthesizer_multi_file_generation_and_materialization():
    runner = DockerSandboxRunner(image="kuro-sandbox")
    inspector = BinaryInspector("/home/ilyan/random/kuro/benchmarks/c_cipher/cipher")
    inspection = inspector.inspect()

    probe = DynamicRuntimeProbe(runner)
    probe_report = probe.probe("/home/ilyan/random/kuro/benchmarks/c_cipher/cipher", inspection)

    synthesizer = CodeSynthesizer()
    project = synthesizer.synthesize(inspection, probe_report, target_language="python")

    assert project.entry_point_file == "main.py"
    assert len(project.files) >= 2
    paths = [f.path for f in project.files]
    assert "main.py" in paths
    assert "src/core.py" in paths

    # Test materialization
    target_dir = Path("/tmp/kuro_test_synth_c")
    if target_dir.exists():
        shutil.rmtree(target_dir)

    out = synthesizer.materialize(project, target_dir)
    assert (out / "main.py").exists()
    assert (out / "src/core.py").exists()

    # Test running synthesized code in sandbox
    res = runner.run_python_code(
        str(out), "main.py", args=["-e", "hello world", "-k", "5"]
    )
    assert res.exit_code == 0
    assert res.stdout.strip() == "mjqqt btwqi"

    # Cleanup
    shutil.rmtree(target_dir)


def test_synthesizer_on_go_benchmark():
    runner = DockerSandboxRunner(image="kuro-sandbox")
    inspector = BinaryInspector("/home/ilyan/random/kuro/benchmarks/go_calc/aegis_sample")
    inspection = inspector.inspect()

    probe = DynamicRuntimeProbe(runner)
    probe_report = probe.probe("/home/ilyan/random/kuro/benchmarks/go_calc/aegis_sample", inspection)

    synthesizer = CodeSynthesizer()
    project = synthesizer.synthesize(inspection, probe_report, target_language="python")

    target_dir = Path("/tmp/kuro_test_synth_go")
    if target_dir.exists():
        shutil.rmtree(target_dir)

    out = synthesizer.materialize(project, target_dir)
    assert (out / "main.py").exists()

    # Test running synthesized stats command
    res = runner.run_python_code(str(out), "main.py", args=["stats", "10", "20", "30"])
    assert res.exit_code == 0
    assert "count: 3" in res.stdout
    assert "sum: 60.00" in res.stdout

    # Cleanup
    shutil.rmtree(target_dir)


def test_clean_json_markdown_fences():
    fenced = '```json\n{"target_language": "python", "entry_point_file": "main.py", "files": [], "architecture_overview": "test"}\n```'
    cleaned = CodeSynthesizer._clean_json_markdown(fenced)
    assert not cleaned.startswith("```")
    assert not cleaned.endswith("```")
    assert '"target_language": "python"' in cleaned


def test_gemini_synthesis_error_handling(monkeypatch):
    from unittest.mock import MagicMock
    import pytest

    synthesizer = CodeSynthesizer(api_key="fake-test-key")
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("API quota exceeded")
    monkeypatch.setattr(synthesizer, "_get_client", lambda: mock_client)
    synthesizer._client = mock_client

    inspector = BinaryInspector("/home/ilyan/random/kuro/benchmarks/c_cipher/cipher")
    inspection = inspector.inspect()
    probe = DynamicRuntimeProbe(DockerSandboxRunner(image="kuro-sandbox"))
    probe_report = probe.probe("/home/ilyan/random/kuro/benchmarks/c_cipher/cipher", inspection)

    with pytest.raises(RuntimeError, match="Gemini API code synthesis failed"):
        synthesizer.synthesize(inspection, probe_report)

