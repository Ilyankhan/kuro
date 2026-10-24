from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class ArchitectureType(str, Enum):
    X86_64 = "x86_64"
    AARCH64 = "aarch64"
    X86 = "x86"
    ARM = "arm"
    UNKNOWN = "unknown"


class BinaryLanguageOrigin(str, Enum):
    C_CPP = "c_cpp"
    GO = "go"
    RUST = "rust"
    UNKNOWN = "unknown"


class FunctionSymbol(BaseModel):
    name: str
    address: Optional[str] = None
    size: Optional[int] = None
    is_exported: bool = False
    disassembly_preview: Optional[str] = None
    call_references: List[str] = Field(default_factory=list)


class InspectionReport(BaseModel):
    """Output from Agent 1 (Inspector & Symbol Extractor)."""
    binary_path: str
    format: str = "ELF"
    architecture: ArchitectureType = ArchitectureType.X86_64
    inferred_origin: BinaryLanguageOrigin = BinaryLanguageOrigin.UNKNOWN
    is_stripped: bool = False
    entry_point: Optional[str] = None
    functions: List[FunctionSymbol] = Field(default_factory=list)
    extracted_strings: List[str] = Field(default_factory=list)
    go_package_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProbeExecutionResult(BaseModel):
    command_args: List[str]
    stdin_input: Optional[str] = None
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_ms: float = 0.0


class ProbeReport(BaseModel):
    """Output from Agent 2 (Dynamic Runtime Probe)."""
    detected_subcommands: List[str] = Field(default_factory=list)
    supported_flags: List[str] = Field(default_factory=list)
    help_text: Optional[str] = None
    version_text: Optional[str] = None
    sample_runs: List[ProbeExecutionResult] = Field(default_factory=list)
    inferred_usage_summary: str = ""


class SynthesizedFile(BaseModel):
    path: str
    content: str
    description: Optional[str] = None
    imports: List[str] = Field(default_factory=list)


class SynthesizedProject(BaseModel):
    """Output from Agent 3 (Modern Code Synthesizer)."""
    target_language: str # 'python' or 'go'
    entry_point_file: str # e.g. 'main.py' or 'main.go'
    files: List[SynthesizedFile] = Field(default_factory=list)
    architecture_overview: str = ""


class TestCaseResult(BaseModel):
    test_id: int
    args: List[str]
    stdin_input: Optional[str] = None
    legacy_stdout: str
    legacy_stderr: str
    legacy_exit_code: int
    modern_stdout: str
    modern_stderr: str
    modern_exit_code: int
    stdout_matched: bool
    exit_code_matched: bool
    passed: bool


class DefectReport(BaseModel):
    failing_test_id: int
    command_args: List[str]
    stdin_input: Optional[str] = None
    expected_stdout: str
    actual_stdout: str
    expected_exit_code: int
    actual_exit_code: int
    diagnostic_hint: str


class VerificationReport(BaseModel):
    """Output from Agent 4 (Differential Parity Verifier)."""
    total_tests: int
    passed_tests: int
    failed_tests: int
    parity_percentage: float
    defects: List[DefectReport] = Field(default_factory=list)
    is_fully_parity_proven: bool = False
