"""Read-only Git credential scan. Reports locations, never credential values."""

import collections
import json
import math
from pathlib import Path
import re
import subprocess


PATTERN = re.compile(rb"(?:gsk_|sk-(?:proj-)?)[A-Za-z0-9_-]{25,}")


def candidates(data: bytes):
    if b"\0" in data:
        return []
    found = []
    for match in PATTERN.finditer(data):
        token = match.group()
        if re.match(rb"(?:gsk_|sk-)(?:YOUR|your|test|fake|example|dummy|mock)[_-]", token):
            continue
        counts = collections.Counter(token)
        entropy = -sum(amount / len(token) * math.log2(amount / len(token)) for amount in counts.values())
        if entropy >= 3.5:
            found.append(token)
    return found


def git(*args, input=None):
    return subprocess.check_output(["git", *args], input=input)


def main():
    root = Path(git("rev-parse", "--show-toplevel").decode().strip())
    findings = []
    paths = git("ls-files", "-z", "--cached", "--others", "--exclude-standard").decode().split("\0")
    for name in sorted(set(paths) - {""}):
        path = root / name
        if path.is_file() and path.stat().st_size < 2_000_000 and candidates(path.read_bytes()):
            findings.append({"scope": "worktree", "path": name})
    objects = git("rev-list", "--objects", "--all").decode().splitlines()
    names = {line.split(" ", 1)[0]: line.split(" ", 1)[1] for line in objects if " " in line}
    checks = git("cat-file", "--batch-check", input=("\n".join(names) + "\n").encode()).decode().splitlines()
    ids = [line.split()[0] for line in checks if len(line.split()) == 3 and line.split()[1] == "blob" and int(line.split()[2]) < 2_000_000]
    batch = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for object_id in ids:
        batch.stdin.write((object_id + "\n").encode())
        batch.stdin.flush()
        header = batch.stdout.readline().split()
        data = batch.stdout.read(int(header[2]))
        batch.stdout.read(1)
        if candidates(data):
            findings.append({"scope": "history", "blob": object_id, "path": names[object_id]})
    batch.stdin.close()
    batch.wait()
    print(json.dumps({"candidate_files": len(set(paths) - {""}), "historical_blobs": len(ids), "findings": findings}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
