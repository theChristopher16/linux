#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only OR MIT
"""Exercise actual reset functions with single-threaded synthetic callbacks."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--cc", default="clang")
    args = parser.parse_args()
    compiler = shutil.which(args.cc)
    if not compiler:
        parser.error("C compiler not found")
    template = Path(__file__).with_name("fixture.c.in").read_text()
    if template.count("@ACTUAL_FUNCTIONS@") != 1:
        raise RuntimeError("bad template marker")
    results = []
    with tempfile.TemporaryDirectory(prefix="pvr-reset-host-") as tmp:
        env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TMPDIR": tmp}
        for kind, path in (("baseline", args.baseline), ("candidate", args.candidate)):
            raw = path.read_bytes()
            functions = []
            for name in ("pvr_power_get_clear", "pvr_power_reset"):
                pattern = rf"^(?:static )?int\n{name}\(.*?^\}}"
                found = re.findall(pattern, raw.decode(), re.M | re.S)
                if len(found) != 1:
                    raise RuntimeError("ambiguous source extraction: " + name)
                functions.append(found[0])
            extracted = "\n\n".join(functions)
            unit = Path(tmp) / f"{kind}.c"
            unit.write_text(template.replace("@ACTUAL_FUNCTIONS@", extracted))
            modes = (("optimized", ["-O2"]), ("asan-ubsan", [
                "-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]))
            for mode, flags in modes:
                binary = Path(tmp) / f"{kind}-{mode}"
                command = [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                           "-DCANDIDATE=" + str(int(kind == "candidate")),
                           *flags, str(unit), "-o", str(binary)]
                build = subprocess.run(command, env=env, capture_output=True,
                                       text=True, timeout=40)
                if build.returncode:
                    raise RuntimeError(f"{kind} {mode} compile failed:\n{build.stderr}")
                run = subprocess.run([str(binary)], env=env, capture_output=True,
                                     text=True, timeout=8)
                label = "candidate" if kind == "candidate" else "baseline characterization"
                expected = f"{label}: 17 synthetic reset scenarios passed\n"
                if run.returncode or run.stdout != expected or run.stderr:
                    raise RuntimeError(f"{kind} {mode}: {run.stdout}{run.stderr}")
                results.append({"kind": kind, "mode": mode, "cases": 17,
                                "result": "pass",
                                "source_sha256": hashlib.sha256(raw).hexdigest(),
                                "function_sha256": hashlib.sha256(extracted.encode()).hexdigest()})
    print(json.dumps({"hardware_used": False, "results": results}, indent=2))


if __name__ == "__main__":
    main()
