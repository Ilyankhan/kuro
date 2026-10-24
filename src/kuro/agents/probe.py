import re
from typing import List, Set, Tuple
from kuro.models.schemas import InspectionReport, ProbeReport, ProbeExecutionResult
from kuro.sandbox.runner import DockerSandboxRunner


class DynamicRuntimeProbe:
    """Agent 2: Interactively probes a binary inside the Docker sandbox to infer

    CLI contracts, subcommands, flags, and exit behavior.
    """

    COMMON_PROBE_ARGS = [
        [],
        ["-h"],
        ["--help"],
        ["help"],
        ["-v"],
        ["--version"],
        ["version"],
    ]

    def __init__(self, runner: DockerSandboxRunner):
        self.runner = runner

    def probe(self, binary_path: str, inspection: InspectionReport) -> ProbeReport:
        """Executes exploratory probes and compiles a structured ProbeReport."""
        sample_runs: List[ProbeExecutionResult] = []
        detected_flags: Set[str] = set()
        detected_subcommands: Set[str] = set()
        help_text: str = ""
        version_text: str = ""

        # 1. Standard probe commands
        for args in self.COMMON_PROBE_ARGS:
            res = self.runner.run_binary(binary_path, args=args)
            sample_runs.append(res)
            full_output = f"{res.stdout}\n{res.stderr}".strip()

            if any(h in args for h in ("-h", "--help", "help")) and res.exit_code in (0, 1):
                if full_output and not help_text:
                    help_text = full_output
            elif any(v in args for v in ("-v", "--version", "version")) and res.exit_code == 0:
                if full_output and not version_text:
                    version_text = full_output

        # 2. Extract flags and subcommands from strings found by Inspector
        heuristic_flags = self._extract_flags_from_strings(inspection.extracted_strings)
        for flag in heuristic_flags:
            detected_flags.add(flag)
            # Try running with flag
            res = self.runner.run_binary(binary_path, args=[flag])
            sample_runs.append(res)
            if res.exit_code == 0 or "Usage" in res.stdout or "Error" in res.stderr:
                detected_flags.add(flag)

        # 3. Parse help text if available
        if help_text:
            parsed_flags, parsed_subs = self._parse_help_text(help_text)
            detected_flags.update(parsed_flags)
            detected_subcommands.update(parsed_subs)

        # 4. Probe Go functions for subcommands
        for fn in inspection.functions:
            clean_name = fn.name.replace("main.", "").lower()
            if clean_name in ("reverse", "stats", "sum", "calc", "encrypt", "decrypt", "cipher"):
                detected_subcommands.add(clean_name)
                # Try running subcommand
                res = self.runner.run_binary(binary_path, args=[clean_name])
                sample_runs.append(res)

        summary = f"Binary accepts flags: {list(detected_flags)} and subcommands: {list(detected_subcommands)}."

        return ProbeReport(
            detected_subcommands=sorted(list(detected_subcommands)),
            supported_flags=sorted(list(detected_flags)),
            help_text=help_text if help_text else None,
            version_text=version_text if version_text else None,
            sample_runs=sample_runs,
            inferred_usage_summary=summary,
        )

    def _extract_flags_from_strings(self, strings: List[str]) -> List[str]:
        """Extracts candidate flags like -e, --input from extracted binary strings."""
        flags = set()
        flag_pattern = re.compile(r"^(--?[a-zA-Z0-9_-]+)")
        for s in strings:
            words = s.split()
            for word in words:
                match = flag_pattern.match(word)
                if match:
                    flag = match.group(1)
                    if len(flag) <= 16:
                        flags.add(flag)
        return list(flags)

    def _parse_help_text(self, help_text: str) -> Tuple[Set[str], Set[str]]:
        """Parses flags (-x, --foo) and subcommands from help messages."""
        flags = set()
        subcommands = set()

        # Find flags: -f, --flag
        flag_matches = re.findall(r"(--?[a-zA-Z0-9_-]+)", help_text)
        for f in flag_matches:
            if len(f) <= 16:
                flags.add(f)

        # Find subcommands in lines like "  command  Description"
        for line in help_text.splitlines():
            line_strip = line.strip()
            if line_strip.startswith(("-", "Usage:", "Options:", "Commands:")):
                continue
            parts = line_strip.split()
            if len(parts) >= 2 and parts[0].isalpha() and len(parts[0]) < 15:
                subcommands.add(parts[0])

        return flags, subcommands
