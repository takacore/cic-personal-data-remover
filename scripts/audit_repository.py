"""Check Git objects for document payloads and author/workstation identifiers."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main() -> int:
    failures = []
    for path in git('ls-files').decode('utf-8').splitlines():
        suffix = Path(path).suffix.lower()
        if suffix in {'.pdf', '.png', '.jpg', '.jpeg', '.json', '.exe', '.pem', '.key'}:
            failures.append(f'Disallowed tracked payload: {path}')
        if path.startswith(('outputs/', 'tmp/', 'work/vendor/', 'work/tessdata/')):
            failures.append(f'Disallowed tracked directory: {path}')

    records = git('cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype)').decode().splitlines()
    user_path = re.compile(rb'(?i)[a-z]:[\\/]+Users[\\/]+[a-z0-9_.-]+')
    secrets = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    for record in records:
        sha, kind = record.split()
        if kind not in {'blob', 'commit', 'tag'}:
            continue
        content = git('cat-file', kind, sha)
        if user_path.search(content):
            failures.append(f'Absolute workstation user path in {kind} {sha[:12]}')
        if secrets.search(content):
            failures.append(f'Credential-like value in {kind} {sha[:12]}')
        if kind == 'commit':
            header = content.split(b'\n\n', 1)[0]
            for line in header.splitlines():
                if line.startswith((b'author ', b'committer ')):
                    if not line.startswith((b'author CIC Tool Contributors <contributors@example.invalid>',
                                            b'committer CIC Tool Contributors <contributors@example.invalid>')):
                        failures.append(f'Non-anonymous commit identity in {sha[:12]}')
        if kind == 'tag' and b'\ntagger ' in content:
            failures.append(f'Tag author requires manual review: {sha[:12]}')

    if failures:
        print('\n'.join(failures))
        return 1
    print(f'PASS: {len(records)} Git objects checked; document payloads, workstation paths and non-anonymous authors absent.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
