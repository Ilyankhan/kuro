import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from kuro.models.schemas import (
    ArchitectureType,
    BinaryLanguageOrigin,
    FunctionSymbol,
    InspectionReport,
)


class BinaryInspector:
    """Agent 1: Ingests raw ELF binaries, extracts structural metadata, functions,

    strings, and isolates domain symbols from runtime clutter.
    """

    GO_SYSTEM_PREFIXES = (
        "runtime.",
        "internal/",
        "sync.",
        "syscall.",
        "reflect.",
        "fmt.",
        "os.",
        "time.",
        "strconv.",
        "unicode",
        "math.",
        "path.",
        "io.",
        "bufio.",
        "sort.",
        "errors.",
        "context.",
        "type..",
        "go..",
    )

    def __init__(self, binary_path: str):
        self.path = Path(binary_path).resolve()
        if not self.path.exists():
            raise FileNotFoundError(f"Binary not found: {self.path}")

    def inspect(self) -> InspectionReport:
        """Runs complete static inspection pipeline."""
        arch, bitness = self._detect_architecture()
        origin = self._detect_origin_language()
        is_stripped = self._check_if_stripped()
        entry_point = self._extract_entry_point()
        strings = self._extract_meaningful_strings(limit=100)
        functions, go_pkg = self._extract_functions(origin)

        return InspectionReport(
            binary_path=str(self.path),
            format="ELF",
            architecture=arch,
            inferred_origin=origin,
            is_stripped=is_stripped,
            entry_point=entry_point,
            functions=functions,
            extracted_strings=strings,
            go_package_name=go_pkg,
            metadata={
                "file_size_bytes": self.path.stat().st_size,
                "bitness": bitness,
            },
        )

    def _detect_architecture(self) -> Tuple[ArchitectureType, str]:
        """Inspects ELF header via readelf -h."""
        try:
            res = subprocess.run(
                ["readelf", "-h", str(self.path)],
                capture_output=True,
                text=True,
                check=True,
            )
            out = res.stdout.lower()
            if "x86-64" in out or "advanced micro devices x86-64" in out:
                return ArchitectureType.X86_64, "64-bit"
            elif "aarch64" in out or "arm aarch64" in out:
                return ArchitectureType.AARCH64, "64-bit"
            elif "intel 80386" in out or "i386" in out:
                return ArchitectureType.X86, "32-bit"
            elif "arm" in out:
                return ArchitectureType.ARM, "32-bit"
        except Exception:
            pass
        return ArchitectureType.UNKNOWN, "unknown"

    def _detect_origin_language(self) -> BinaryLanguageOrigin:
        """Detects if binary was compiled from Go, Rust, or C/C++."""
        try:
            # Check section headers
            res = subprocess.run(
                ["readelf", "-S", str(self.path)],
                capture_output=True,
                text=True,
            )
            out = res.stdout
            if ".gopclntab" in out or ".go.buildinfo" in out:
                return BinaryLanguageOrigin.GO

            # Check for strings
            str_res = subprocess.run(
                ["strings", "-a", str(self.path)],
                capture_output=True,
                text=True,
            )
            str_out = str_res.stdout
            if "Go build ID" in str_out or "runtime.gopanic" in str_out:
                return BinaryLanguageOrigin.GO
            elif "rustc" in str_out:
                return BinaryLanguageOrigin.RUST
            elif "libc.so" in str_out or "GLIBC" in str_out or "__libc_start_main" in str_out:
                return BinaryLanguageOrigin.C_CPP
        except Exception:
            pass
        return BinaryLanguageOrigin.UNKNOWN

    def _check_if_stripped(self) -> bool:
        """Determines if symbol table was stripped."""
        try:
            res = subprocess.run(
                ["readelf", "-S", str(self.path)],
                capture_output=True,
                text=True,
            )
            return ".symtab" not in res.stdout
        except Exception:
            return True

    def _extract_entry_point(self) -> Optional[str]:
        """Extracts entry point virtual address from ELF header."""
        try:
            res = subprocess.run(
                ["readelf", "-h", str(self.path)],
                capture_output=True,
                text=True,
            )
            for line in res.stdout.splitlines():
                if "Entry point address" in line:
                    return line.split(":")[-1].strip()
        except Exception:
            pass
        return None

    def _extract_meaningful_strings(self, limit: int = 100) -> List[str]:
        """Extracts ASCII/UTF-8 strings of length >= 4, filtered for useful domain indicators."""
        try:
            res = subprocess.run(
                ["strings", "-a", "-n", "4", str(self.path)],
                capture_output=True,
                text=True,
            )
            raw = res.stdout.splitlines()
            meaningful = []
            for s in raw:
                s = s.strip()
                # Skip raw memory/assembly noise
                if len(s) < 4 or len(s) > 120:
                    continue
                if s.startswith(("/lib", "/usr", "GCC:", "GLIBC_", "ld-linux")):
                    continue
                meaningful.append(s)
                if len(meaningful) >= limit:
                    break
            return meaningful
        except Exception:
            return []

    def _extract_functions(
        self, origin: BinaryLanguageOrigin
    ) -> Tuple[List[FunctionSymbol], Optional[str]]:
        """Extracts domain functions, filtering out standard runtime clutter."""
        functions: List[FunctionSymbol] = []
        go_package: Optional[str] = None

        try:
            # Attempt to extract using nm -C
            res = subprocess.run(
                ["nm", "-C", str(self.path)],
                capture_output=True,
                text=True,
            )
            lines = res.stdout.splitlines()
            for line in lines:
                parts = line.split()
                if len(parts) >= 3 and parts[1].upper() in ("T", "W"):
                    addr, sym_type, name = parts[0], parts[1], " ".join(parts[2:])

                    # Go-specific runtime filtering
                    if origin == BinaryLanguageOrigin.GO:
                        if any(name.startswith(pfx) for pfx in self.GO_SYSTEM_PREFIXES):
                            continue
                        if "." in name and not name.startswith("main."):
                            go_package = name.split(".")[0]
                    else:
                        # C/C++ filtering
                        if name.startswith(("_init", "_start", "__", "deregister_", "register_")):
                            continue

                    functions.append(
                        FunctionSymbol(
                            name=name,
                            address=addr,
                            is_exported=(sym_type == "T"),
                        )
                    )
        except Exception:
            pass

        # If binary is stripped or nm yielded zero functions, disassemble entry point
        if not functions:
            functions = self._extract_from_disassembly()

        return functions, go_package

    def _extract_from_disassembly(self) -> List[FunctionSymbol]:
        """Fallback function extractor using objdump disassembly."""
        functions: List[FunctionSymbol] = []
        try:
            res = subprocess.run(
                ["objdump", "-d", "--no-show-raw-insn", str(self.path)],
                capture_output=True,
                text=True,
            )
            # Find function headers e.g. "0000000000001149 <main>:"
            fn_regex = re.compile(r"^([0-9a-fA-F]+)\s+<([^>]+)>:")
            current_fn: Optional[FunctionSymbol] = None
            preview_lines: List[str] = []

            for line in res.stdout.splitlines():
                match = fn_regex.match(line)
                if match:
                    if current_fn:
                        current_fn.disassembly_preview = "\n".join(preview_lines[:15])
                        functions.append(current_fn)
                    addr, name = match.group(1), match.group(2)
                    if not name.startswith(("_", "deregister_", "register_")):
                        current_fn = FunctionSymbol(name=name, address=addr)
                        preview_lines = []
                    else:
                        current_fn = None
                elif current_fn and line.strip():
                    if len(preview_lines) < 15:
                        preview_lines.append(line.strip())

            if current_fn:
                current_fn.disassembly_preview = "\n".join(preview_lines[:15])
                functions.append(current_fn)
        except Exception:
            pass

        return functions
