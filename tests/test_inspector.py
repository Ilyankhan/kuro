from pathlib import Path
from kuro.agents.inspector import BinaryInspector
from kuro.models.schemas import ArchitectureType, BinaryLanguageOrigin


def test_inspector_on_c_binary():
    bin_path = "/home/ilyan/random/kuro/benchmarks/c_cipher/cipher"
    inspector = BinaryInspector(bin_path)
    report = inspector.inspect()

    assert report.architecture == ArchitectureType.X86_64
    assert report.inferred_origin == BinaryLanguageOrigin.C_CPP
    assert report.is_stripped is False
    assert any("Usage:" in s for s in report.extracted_strings)

    # Functions extracted
    fn_names = [f.name for f in report.functions]
    assert "main" in fn_names
    assert "transform" in fn_names
    assert "print_usage" in fn_names


def test_inspector_on_go_binary():
    bin_path = "/home/ilyan/random/kuro/benchmarks/go_calc/aegis_sample"
    inspector = BinaryInspector(bin_path)
    report = inspector.inspect()

    assert report.architecture == ArchitectureType.X86_64
    assert report.inferred_origin == BinaryLanguageOrigin.GO

    # Verify that Go runtime noise is filtered out
    fn_names = [f.name for f in report.functions]
    for name in fn_names:
        assert not name.startswith("runtime.")
        assert not name.startswith("internal/")

    # Domain functions must be identified
    assert any("main.ComputeStats" in f or "ComputeStats" in f for f in fn_names)
    assert any("main.ReverseString" in f or "ReverseString" in f for f in fn_names)
