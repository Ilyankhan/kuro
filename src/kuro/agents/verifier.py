import random
import re
import string
from pathlib import Path
from typing import List, Optional, Tuple
from kuro.models.schemas import (
    DefectReport,
    ProbeReport,
    TestCaseResult,
    VerificationReport,
)
from kuro.sandbox.runner import DockerSandboxRunner


class DifferentialParityVerifier:
    """Agent 4: Generates edge-case test vectors, executes dual sandbox runs

    between the original legacy binary and synthesized modern code, and produces
    empirical parity proofs or defect reports.
    """

    def __init__(self, runner: DockerSandboxRunner):
        self.runner = runner

    def verify(
        self,
        legacy_binary_path: str,
        modern_workspace_dir: str,
        modern_entry_file: str,
        probe_report: ProbeReport,
        target_language: str = "python",
        test_count: int = 25,
    ) -> VerificationReport:
        """Executes full differential verification test suite."""
        test_vectors = self._generate_test_vectors(probe_report, count=test_count)
        test_results: List[TestCaseResult] = []
        defects: List[DefectReport] = []

        for idx, (args, stdin_val) in enumerate(test_vectors, start=1):
            # 1. Run legacy binary
            leg_res = self.runner.run_binary(
                legacy_binary_path, args=args, stdin_input=stdin_val
            )

            # 2. Run modern synthesized code
            if target_language == "python":
                mod_res = self.runner.run_python_code(
                    modern_workspace_dir, modern_entry_file, args=args, stdin_input=stdin_val
                )
            else:
                # Fallback for future compiled targets
                mod_res = self.runner.run_python_code(
                    modern_workspace_dir, modern_entry_file, args=args, stdin_input=stdin_val
                )

            # 3. Compare outputs
            norm_leg_stdout = self._normalize_stdout(
                leg_res.stdout,
                legacy_bin_path=legacy_binary_path,
                modern_entry_file=modern_entry_file,
            )
            norm_mod_stdout = self._normalize_stdout(
                mod_res.stdout,
                legacy_bin_path=legacy_binary_path,
                modern_entry_file=modern_entry_file,
            )
            stdout_matched = (norm_leg_stdout == norm_mod_stdout)
            exit_code_matched = (leg_res.exit_code == mod_res.exit_code)
            passed = stdout_matched and exit_code_matched

            case_result = TestCaseResult(
                test_id=idx,
                args=args,
                stdin_input=stdin_val,
                legacy_stdout=leg_res.stdout,
                legacy_stderr=leg_res.stderr,
                legacy_exit_code=leg_res.exit_code,
                modern_stdout=mod_res.stdout,
                modern_stderr=mod_res.stderr,
                modern_exit_code=mod_res.exit_code,
                stdout_matched=stdout_matched,
                exit_code_matched=exit_code_matched,
                passed=passed,
            )
            test_results.append(case_result)

            if not passed:
                hint = self._diagnose_mismatch(case_result)
                defects.append(
                    DefectReport(
                        failing_test_id=idx,
                        command_args=args,
                        stdin_input=stdin_val,
                        expected_stdout=leg_res.stdout.strip(),
                        actual_stdout=mod_res.stdout.strip(),
                        expected_exit_code=leg_res.exit_code,
                        actual_exit_code=mod_res.exit_code,
                        diagnostic_hint=hint,
                    )
                )

        passed_count = sum(1 for t in test_results if t.passed)
        failed_count = len(test_results) - passed_count
        parity_pct = round((passed_count / len(test_results)) * 100, 2) if test_results else 0.0

        return VerificationReport(
            total_tests=len(test_results),
            passed_tests=passed_count,
            failed_tests=failed_count,
            parity_percentage=parity_pct,
            defects=defects,
            is_fully_parity_proven=(failed_count == 0),
        )

    def _normalize_stdout(
        self,
        text: str,
        legacy_bin_path: Optional[str] = None,
        modern_entry_file: Optional[str] = None,
    ) -> str:
        """Normalizes executable names in stdout (e.g., ./cipher, python3 main.py -> [PROG])

        so help/usage text parity doesn't fail due to file naming differences.
        """
        if not text:
            return ""

        norm = text.strip()

        if modern_entry_file:
            entry_name = Path(modern_entry_file).name
            norm = re.sub(rf"python3?\s+(-B\s+)?(\./)?{re.escape(entry_name)}", "[PROG]", norm)
            norm = re.sub(rf"(\./)?{re.escape(entry_name)}", "[PROG]", norm)

        if legacy_bin_path:
            bin_name = Path(legacy_bin_path).name
            names = [bin_name]
            if "_stripped" in bin_name:
                names.append(bin_name.replace("_stripped", ""))
            for b in names:
                norm = re.sub(rf"(\./)?{re.escape(b)}", "[PROG]", norm)

        norm = re.sub(r"python3?\s+(-B\s+)?(\./)?main\.py", "[PROG]", norm)
        norm = re.sub(r"(\./)?main\.py", "[PROG]", norm)
        return norm

    def _generate_test_vectors(
        self, probe: ProbeReport, count: int = 25
    ) -> List[Tuple[List[str], Optional[str]]]:
        """Generates fuzzing vectors covering known flags, edge cases, and invalid inputs."""
        vectors: List[Tuple[List[str], Optional[str]]] = [
            ([], None),
            (["-h"], None),
            (["--help"], None),
            (["--invalid-flag-edge-test"], None),
        ]

        # Add tests for detected subcommands
        for sub in probe.detected_subcommands:
            vectors.append(([sub], None))
            if sub == "reverse":
                vectors.append(([sub, "hello"], None))
                vectors.append(([sub, ""], None))
                vectors.append(([sub, "racecar"], None))
                vectors.append(([sub, "a b c d 123 !@#"], None))
            elif sub == "stats":
                vectors.append(([sub, "10", "20", "30"], None))
                vectors.append(([sub, "0", "-5", "100.5"], None))
                vectors.append(([sub, "invalid_num"], None))
                vectors.append(([sub], None))

        # Add tests for detected flags
        if "-e" in probe.supported_flags or "-d" in probe.supported_flags:
            vectors.append((["-e", "hello world", "-k", "5"], None))
            vectors.append((["-d", "mjqqt btwqi", "-k", "5"], None))
            vectors.append((["-e", "Test 123!", "-k", "13"], None))
            vectors.append((["-e", ""], None))
            vectors.append((["-k", "999"], None))

        # Fill remaining with randomized inputs
        while len(vectors) < count:
            rand_str = "".join(random.choices(string.ascii_letters + string.digits, k=8))
            vectors.append(([rand_str], None))

        return vectors[:count]

    def _diagnose_mismatch(self, case: TestCaseResult) -> str:
        """Generates actionable hint for the Synthesizer agent."""
        if not case.exit_code_matched:
            return (
                f"Exit code mismatch for args {case.args}: Expected exit code {case.legacy_exit_code}, "
                f"but modern code exited with {case.modern_exit_code}."
            )
        elif not case.stdout_matched:
            return (
                f"Output mismatch for args {case.args}: Expected '{case.legacy_stdout.strip()}', "
                f"got '{case.modern_stdout.strip()}'."
            )
        return "Unknown parity mismatch."
