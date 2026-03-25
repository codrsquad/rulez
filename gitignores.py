"""Ick rule: ensure .gitignore at repo root contains __pycache__ and *.pyc entries."""
import re
import sys
from pathlib import Path

REQUIRED_EXACT = ['__pycache__/']
REQUIRED_PATTERNS = [re.compile(r'^(\*\*/)?(\*\.py\[?c[do\]]*)$')]


def _line_matches_any_pattern(line: str) -> bool:
    return any(p.match(line) for p in REQUIRED_PATTERNS)


def check(root: Path) -> int:
    gitignore = root / '.gitignore'
    lines = gitignore.read_text().splitlines(True) if gitignore.exists() else []
    stripped = [l.rstrip('\n') for l in lines]

    missing = []
    for line in REQUIRED_EXACT:
        if line not in stripped:
            missing.append(line + "\n")
    if not any(_line_matches_any_pattern(l) for l in stripped):
        missing.append('*.pyc\n')

    if missing:
        with gitignore.open('a') as f:
            if lines and not lines[-1].endswith('\n'):
                f.write('\n')
            f.writelines(missing)

    return 0


def main():
    sys.exit(check(Path('.')))


if __name__ == '__main__':
    main()
