import subprocess
from pathlib import Path
import pytest
from kuro.models.schemas import InspectionReport, ArchitectureType, BinaryLanguageOrigin


def test_c_benchmark_exists_and_runs():
    cipher_path = Path("/home/ilyan/random/kuro/benchmarks/c_cipher/cipher")
    assert cipher_path.exists()
    assert cipher_path.is_file()

    # Test encryption
    proc = subprocess.run(
        [str(cipher_path), "-e", "helloworld", "-k", "5"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == "mjqqtbtwqi"

    # Test decryption
    proc = subprocess.run(
        [str(cipher_path), "-d", "mjqqtbtwqi", "-k", "5"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == "helloworld"


def test_go_benchmark_exists_and_runs():
    calc_path = Path("/home/ilyan/random/kuro/benchmarks/go_calc/aegis_sample")
    assert calc_path.exists()
    assert calc_path.is_file()

    # Test reverse
    proc = subprocess.run(
        [str(calc_path), "reverse", "kuro"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == "oruk"

    # Test stats
    proc = subprocess.run(
        [str(calc_path), "stats", "10", "20"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "count: 2" in proc.stdout
    assert "sum: 30.00" in proc.stdout


def test_schema_serialization():
    report = InspectionReport(
        binary_path="/test/path",
        architecture=ArchitectureType.X86_64,
        inferred_origin=BinaryLanguageOrigin.C_CPP,
        extracted_strings=["Usage: %s", "hello world"],
    )
    dumped = report.model_dump()
    assert dumped["architecture"] == "x86_64"
    assert dumped["inferred_origin"] == "c_cpp"
    assert len(dumped["extracted_strings"]) == 2
