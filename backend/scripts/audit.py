"""
Codebase audit script. Scans for common issues and prints a clean report.

Usage (from backend/):
    python -m scripts.audit
    python -m scripts.audit --fix    # Auto-fix safe issues (trailing whitespace, etc.)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ── Terminal formatting ──────────────────────────────────────────


class Style:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def header(title: str) -> None:
    """Print a section header with visual separation."""
    width = 60
    print(f"\n{Style.BLUE}{'=' * width}{Style.RESET}")
    print(f"  {Style.BOLD}{title}{Style.RESET}")
    print(f"{Style.BLUE}{'=' * width}{Style.RESET}\n")


def subheader(title: str) -> None:
    print(f"  {Style.CYAN}{Style.BOLD}{title}{Style.RESET}")


def finding(severity: str, file: str, line: int, message: str) -> None:
    """Print a single finding with severity color."""
    colors = {"ERROR": Style.RED, "WARN": Style.YELLOW, "INFO": Style.DIM}
    icons = {"ERROR": "x", "WARN": "!", "INFO": "."}
    color = colors.get(severity, Style.DIM)
    icon = icons.get(severity, ".")

    short_file = str(file).replace(str(PROJECT_ROOT) + "/", "")
    location = f"{short_file}:{line}" if line > 0 else short_file

    print(f"    {color}{icon}{Style.RESET}  {Style.DIM}{location:<45}{Style.RESET} {message}")


def summary_line(label: str, count: int, severity: str = "INFO") -> None:
    colors = {"ERROR": Style.RED, "WARN": Style.YELLOW, "OK": Style.GREEN, "INFO": Style.DIM}
    color = colors.get(severity, Style.DIM)
    print(f"    {color}{count:>4}{Style.RESET}  {label}")


def divider() -> None:
    print(f"  {Style.DIM}{'_' * 50}{Style.RESET}")


# ── Scanners ─────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # backend/


def scan_python_files() -> list[Path]:
    """Yield all .py files in backend/, excluding caches and venvs."""
    return sorted(
        p for p in PROJECT_ROOT.rglob("*.py")
        if "__pycache__" not in str(p) and ".venv" not in str(p)
    )


def scan_for_pattern(
    files: list[Path], pattern: str,
) -> list[tuple[Path, int, str]]:
    """Scan files for a regex pattern, return (file, line_num, line_text) matches."""
    results: list[tuple[Path, int, str]] = []
    compiled = re.compile(pattern)
    for path in files:
        try:
            for i, line in enumerate(path.read_text().splitlines(), 1):
                if compiled.search(line):
                    results.append((path, i, line.strip()))
        except (UnicodeDecodeError, PermissionError):
            continue
    return results


# ── Audit checks ─────────────────────────────────────────────────


def audit_dead_code(py_files: list[Path]) -> None:
    header("Dead Code and Unused Files")

    # TODOs and FIXMEs
    subheader("Outstanding TODOs and FIXMEs")
    todos = scan_for_pattern(py_files, r"#\s*(TODO|FIXME|HACK|XXX|TEMP|BROKEN)")
    if todos:
        for path, line, text in todos[:20]:
            tag_match = re.search(r"(TODO|FIXME|HACK|XXX|TEMP|BROKEN)", text)
            tag = tag_match.group(0) if tag_match else "?"
            idx = text.index(tag)
            finding("WARN", path, line, f"{tag}: {text[idx:][:70]}")
        if len(todos) > 20:
            print(f"    {Style.DIM}... and {len(todos) - 20} more{Style.RESET}")
    else:
        print(f"    {Style.GREEN}OK{Style.RESET}  No outstanding TODOs or FIXMEs")
    print()

    # Potentially unused modules
    subheader("Potentially unused modules")
    all_imports: set[str] = set()
    for path in py_files:
        try:
            content = path.read_text()
            for match in re.finditer(r"(?:from|import)\s+([\w.]+)", content):
                parts = match.group(1).split(".")
                all_imports.add(parts[0])
                if len(parts) > 1:
                    all_imports.add(parts[1])
        except (UnicodeDecodeError, PermissionError):
            continue

    # Also count files referenced as -m module names
    module_files = [p for p in py_files if p.name != "__init__.py"]
    unused = []
    for path in module_files:
        stem = path.stem
        if stem not in all_imports and stem != "audit":
            # Double check: is it in __all__ of its parent init?
            init = path.parent / "__init__.py"
            if init.exists():
                try:
                    init_text = init.read_text()
                    if stem in init_text:
                        continue
                except (UnicodeDecodeError, PermissionError):
                    pass
            unused.append(path)

    if unused:
        for path in unused[:15]:
            finding("WARN", path, 0, "Never imported -- verify or remove")
        if len(unused) > 15:
            print(f"    {Style.DIM}... and {len(unused) - 15} more{Style.RESET}")
    else:
        print(f"    {Style.GREEN}OK{Style.RESET}  All modules appear to be imported somewhere")


def audit_code_quality(py_files: list[Path]) -> int:
    header("Code Quality Issues")

    checks = [
        ("Bare except clauses", r"except\s*:", "ERROR",
         "Catch specific exceptions (ValueError, APIError, etc.)"),
        ("Print statements (use logger)", r"^\s*print\s*\(", "WARN",
         "Replace with logger.info() / logger.debug()"),
        ("Hardcoded model names", r"['\"]gpt-4o|['\"]claude-|['\"]text-embedding", "WARN",
         "Move to config/settings.py"),
        ("Hardcoded secrets or localhost", r"sk-[a-zA-Z0-9]{10,}|127\.0\.0\.1|localhost:\d", "ERROR",
         "Use environment variables via config/settings.py"),
        ("Broad exception catches", r"except Exception\b(?!\s*as)", "WARN",
         "Prefer 'except Exception as e' for logging"),
    ]

    total_issues = 0
    for label, pattern, severity, fix_hint in checks:
        results = scan_for_pattern(py_files, pattern)
        # Filter out print statements in __main__ blocks and test assertions
        if "Print" in label:
            filtered: list[tuple[Path, int, str]] = []
            for path, line, text in results:
                try:
                    lines = path.read_text().splitlines()
                    # Check if we're in an if __name__ == "__main__" block
                    in_main = False
                    for i in range(line - 1, max(line - 60, -1), -1):
                        if i >= 0 and '__name__' in lines[i] and '__main__' in lines[i]:
                            in_main = True
                            break
                    if not in_main and "assert " not in text:
                        filtered.append((path, line, text))
                except (UnicodeDecodeError, PermissionError, IndexError):
                    filtered.append((path, line, text))
            results = filtered

        divider()
        subheader(label)
        if results:
            total_issues += len(results)
            for path, line, text in results[:10]:
                finding(severity, path, line, text[:80])
            if len(results) > 10:
                print(f"    {Style.DIM}... and {len(results) - 10} more{Style.RESET}")
            print(f"    {Style.DIM}Fix: {fix_hint}{Style.RESET}")
        else:
            print(f"    {Style.GREEN}OK{Style.RESET}  None found")

    return total_issues


def audit_consistency(py_files: list[Path]) -> None:
    header("Consistency Checks")

    # Database access patterns
    subheader("Database access pattern")
    direct_clients = scan_for_pattern(py_files, r"create_client\(")

    # Filter out the definition itself
    direct_clients = [
        (p, l, t) for p, l, t in direct_clients
        if "client.py" not in str(p)
    ]

    if direct_clients:
        finding("WARN", "", 0, f"Found {len(direct_clients)} direct create_client() calls outside db/client.py")
        for path, line, text in direct_clients[:5]:
            finding("WARN", path, line, "Should use get_client() from db.client")
    else:
        print(f"    {Style.GREEN}OK{Style.RESET}  Consistent database access via get_client()")
    print()

    # Env var access
    subheader("Environment variable access")
    direct_env = scan_for_pattern(py_files, r"os\.environ|os\.getenv")
    non_config = [
        (p, l, t) for p, l, t in direct_env
        if "settings.py" not in str(p) and "audit.py" not in str(p)
        and "health_check.py" not in str(p)
    ]
    if non_config:
        finding("WARN", "", 0, f"{len(non_config)} file(s) read env vars directly instead of config/settings.py")
        for path, line, text in non_config[:5]:
            finding("WARN", path, line, text[:70])
    else:
        print(f"    {Style.GREEN}OK{Style.RESET}  All env vars accessed through config/settings.py")
    print()

    # Import style consistency
    subheader("Import style")
    future_imports = scan_for_pattern(py_files, r"from __future__ import annotations")
    no_future = [
        p for p in py_files
        if p.name != "__init__.py"
        and not any(p == fp for fp, _, _ in future_imports)
    ]
    pct = len(future_imports) / max(len(py_files) - len([p for p in py_files if p.name == "__init__.py"]), 1) * 100
    summary_line(f"files with 'from __future__ import annotations' ({pct:.0f}%)", len(future_imports), "OK" if pct > 50 else "WARN")
    if no_future and pct < 80:
        for path in no_future[:5]:
            finding("INFO", path, 0, "Missing future annotations import")
    print()

    # Async consistency
    subheader("Async pattern consistency")
    pipeline_dir = PROJECT_ROOT / "pipeline"
    if pipeline_dir.exists():
        async_stages: set[str] = set()
        sync_stages: set[str] = set()
        for path in pipeline_dir.rglob("*.py"):
            if path.name == "__init__.py" or "__pycache__" in str(path):
                continue
            try:
                content = path.read_text()
                if "async def" in content or "await " in content:
                    async_stages.add(path.stem)
                else:
                    sync_stages.add(path.stem)
            except (UnicodeDecodeError, PermissionError):
                continue

        if async_stages and sync_stages:
            finding("INFO", "", 0, f"Mixed: async [{', '.join(sorted(async_stages))}]  sync [{', '.join(sorted(sync_stages))}]")
        else:
            pattern_type = "async" if async_stages else "sync"
            print(f"    {Style.GREEN}OK{Style.RESET}  All pipeline stages are {pattern_type}")
    print()

    # Model name references
    subheader("AI model references")
    model_refs = scan_for_pattern(
        py_files,
        r"['\"](?:gpt-4o-mini|gpt-4o|claude-sonnet|claude-haiku|text-embedding)[^'\"]*['\"]",
    )
    # Exclude config/settings.py which is the correct place
    non_config_models = [
        (p, l, t) for p, l, t in model_refs
        if "settings.py" not in str(p) and "__main__" not in t
    ]
    if non_config_models:
        # Check which ones use settings vs hardcoded
        hardcoded = []
        for path, line, text in non_config_models:
            if "settings." not in text:
                hardcoded.append((path, line, text))
        if hardcoded:
            finding("WARN", "", 0, f"{len(hardcoded)} hardcoded model name(s) outside settings.py")
            for path, line, text in hardcoded[:5]:
                finding("WARN", path, line, text[:80])
        else:
            print(f"    {Style.GREEN}OK{Style.RESET}  All model names come from settings")
    else:
        print(f"    {Style.GREEN}OK{Style.RESET}  No model name references outside settings")


def audit_type_safety(py_files: list[Path]) -> None:
    header("Type Safety and Docstrings")

    # Type annotations on functions
    subheader("Functions without return type annotations")
    untyped: list[tuple[Path, int, str]] = []
    typed = 0
    for path in py_files:
        try:
            for i, line in enumerate(path.read_text().splitlines(), 1):
                stripped = line.strip()
                if re.match(r"def\s+\w+", stripped) or re.match(r"async def\s+\w+", stripped):
                    if "->" in stripped:
                        typed += 1
                    else:
                        untyped.append((path, i, stripped))
        except (UnicodeDecodeError, PermissionError):
            continue

    total_funcs = typed + len(untyped)
    if total_funcs > 0:
        pct = typed / total_funcs * 100
        summary_line(f"typed ({pct:.0f}% of {total_funcs} functions)", typed, "OK")
        summary_line("missing return annotations", len(untyped), "WARN" if untyped else "OK")
        if untyped:
            print()
            for path, line, text in untyped[:10]:
                finding("WARN", path, line, text[:80])
            if len(untyped) > 10:
                print(f"    {Style.DIM}... and {len(untyped) - 10} more{Style.RESET}")
    print()

    # Module docstrings
    subheader("Module docstrings")
    missing = 0
    has = 0
    for path in py_files:
        if path.name == "__init__.py":
            continue
        try:
            content = path.read_text().lstrip()
            lines = [line for line in content.splitlines() if not line.startswith("#!")]
            rest = "\n".join(lines).strip()
            if rest.startswith('"""') or rest.startswith("'''"):
                has += 1
            else:
                missing += 1
                if missing <= 5:
                    finding("WARN", path, 0, "Missing module docstring")
        except (UnicodeDecodeError, PermissionError):
            continue

    total = has + missing
    if total > 0:
        pct = has / total * 100
        summary_line(f"modules with docstrings ({pct:.0f}%)", has, "OK")
        summary_line("modules missing docstrings", missing, "WARN" if missing else "OK")


def audit_file_organization() -> None:
    header("File Organization")

    root = PROJECT_ROOT.parent  # project root

    subheader("Root-level prototype/junk files")
    junk_patterns = ["*.html", "*.jsx"]
    junk_files: list[Path] = []
    for pattern in junk_patterns:
        junk_files.extend(root.glob(pattern))

    if junk_files:
        for path in junk_files:
            finding("WARN", path, 0, "Prototype file in project root -- move or delete")
    else:
        print(f"    {Style.GREEN}OK{Style.RESET}  No stray files in project root")
    print()

    subheader("Missing infrastructure files")
    checks = {
        "pyproject.toml": root / "pyproject.toml",
        ".env.example (root)": root / ".env.example",
        "tests/ (root)": root / "tests",
        "backend/tests/__init__.py": PROJECT_ROOT / "tests" / "__init__.py",
    }
    for label, path in checks.items():
        if path.exists():
            print(f"    {Style.GREEN}OK{Style.RESET}  {label}")
        else:
            finding("INFO", "", 0, f"{label} -- not found")
    print()

    subheader("Package init files")
    expected_packages = ["analysis", "clustering", "config", "db", "ingestion", "models", "pipeline", "scoring"]
    for pkg in expected_packages:
        init = PROJECT_ROOT / pkg / "__init__.py"
        if init.exists():
            content = init.read_text().strip()
            status = "exports defined" if content and content != "_" else "empty"
            icon = Style.GREEN + "OK" + Style.RESET if content and content != "_" else Style.DIM + ".." + Style.RESET
            print(f"    {icon}  {pkg}/__init__.py ({status})")
        else:
            finding("WARN", "", 0, f"{pkg}/__init__.py missing")


# ── Main ─────────────────────────────────────────────────────────


def main() -> None:
    print(f"\n{Style.BOLD}  ClearSignal -- Codebase Audit{Style.RESET}")
    print(f"  {Style.DIM}{PROJECT_ROOT}{Style.RESET}")

    py_files = scan_python_files()
    if not py_files:
        print(f"\n  {Style.RED}No Python files found in backend/{Style.RESET}")
        sys.exit(1)

    print(f"  {Style.DIM}Scanning {len(py_files)} Python files...{Style.RESET}")

    audit_dead_code(py_files)
    issues = audit_code_quality(py_files)
    audit_consistency(py_files)
    audit_type_safety(py_files)
    audit_file_organization()

    header("Summary")
    if issues > 0:
        print(f"  {Style.YELLOW}{issues} code quality issues found.{Style.RESET}")
    else:
        print(f"  {Style.GREEN}No critical code quality issues.{Style.RESET}")
    print(f"\n  Run {Style.BOLD}python -m scripts.audit{Style.RESET} again after fixes to verify.\n")


if __name__ == "__main__":
    main()
