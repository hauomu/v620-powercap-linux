#!/usr/bin/env python3
"""Patch Linux amdgpu so an exact Radeon Pro V620 exposes a lower PPT minimum.

This does not raise the firmware maximum power limit.
SPDX-License-Identifier: GPL-2.0-only
"""
from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
from pathlib import Path

RELATIVE_SOURCE = Path("drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c")
BACKUP_SUFFIX = ".v620-ppt-stock"
BEGIN = "/* V620_PPT_OVERRIDE_BEGIN */"
END = "/* V620_PPT_OVERRIDE_END */"

INIT_RE = re.compile(
    r"""
    (?P<indent>^[ \t]*)
    ret[ \t]*=[ \t]*smu_get_asic_power_limits\(
        [ \t]*smu,[ \t]*\n
        [ \t]*&smu->current_power_limit,[ \t]*\n
        [ \t]*&smu->default_power_limit,[ \t]*\n
        [ \t]*&smu->max_power_limit,[ \t]*\n
        [ \t]*&smu->min_power_limit
    [ \t]*\);[ \t]*\n
    (?P=indent)if[ \t]*\([ \t]*ret[ \t]*\)[ \t]*\{[ \t]*\n
    (?P<body>.*?)
    (?P=indent)\}[ \t]*\n
    """,
    re.MULTILINE | re.DOTALL | re.VERBOSE,
)


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def locate_source(tree: Path) -> Path:
    source = tree.expanduser().resolve() / RELATIVE_SOURCE
    if not source.is_file():
        die(f"kernel source file not found: {source}\nPass the root of a complete Linux kernel source tree.")
    return source


def make_injection(indent: str, min_w: int) -> str:
    i, t = indent, indent + "\t"
    return (
        f"\n{i}{BEGIN}\n"
        f"{i}/*\n"
        f"{i} * Radeon Pro V620 host-PPT minimum override.\n"
        f"{i} * Exact PCI identity: 1002:73a1, subsystem 1002:0e34.\n"
        f"{i} * Preserve firmware current/default/max values. Only lower the\n"
        f"{i} * driver's cached minimum when the requested floor is below the\n"
        f"{i} * firmware-reported minimum and does not exceed the maximum.\n"
        f"{i} */\n"
        f"{i}if (adev->pdev->vendor == 0x1002 &&\n"
        f"{i}    adev->pdev->device == 0x73a1 &&\n"
        f"{i}    adev->pdev->subsystem_vendor == 0x1002 &&\n"
        f"{i}    adev->pdev->subsystem_device == 0x0e34 &&\n"
        f"{i}    smu->min_power_limit > {min_w} &&\n"
        f"{i}    smu->max_power_limit >= {min_w}) {{\n"
        f"{t}smu->min_power_limit = {min_w};\n"
        f"{t}dev_info(adev->dev,\n"
        f"{t}\t \"V620 PPT: host minimum overridden to {min_w} W (firmware max %u W)\\n\",\n"
        f"{t}\t smu->max_power_limit);\n"
        f"{i}}}\n"
        f"{i}{END}\n"
    )


def patch_text(original: str, min_w: int) -> str:
    if BEGIN in original or END in original:
        die("tree is already patched; use --check or --revert first")
    matches = list(INIT_RE.finditer(original))
    if len(matches) != 1:
        die(f"expected exactly one SMU power-limit initialization block, found {len(matches)}. Source was not modified.")
    m = matches[0]
    body = m.group("body")
    if "Failed to get asic power limits!" not in body or "return ret;" not in body:
        die("candidate initialization block lacked expected error handling. Source was not modified.")
    return original[:m.end()] + make_injection(m.group("indent"), min_w) + original[m.end():]


def check(source: Path) -> int:
    text = source.read_text()
    bc, ec = text.count(BEGIN), text.count(END)
    print(f"source: {source}")
    if bc == 1 and ec == 1:
        block = text.split(BEGIN, 1)[1].split(END, 1)[0]
        m = re.search(r"smu->min_power_limit\s*=\s*(\d+)\s*;", block)
        print("status: PATCHED")
        if m:
            print(f"configured driver minimum: {m.group(1)} W")
        return 0
    if bc == 0 and ec == 0:
        print("status: NOT PATCHED")
        return 1
    print("status: INCONSISTENT MARKERS")
    return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kernel_tree", type=Path, help="root of Linux kernel source tree")
    ap.add_argument("--min-w", type=int, default=175,
                    help="driver-visible V620 minimum in watts (default: 175)")
    ap.add_argument("--dry-run", action="store_true", help="print diff; do not write")
    ap.add_argument("--check", action="store_true", help="report patch status")
    ap.add_argument("--revert", action="store_true", help="restore saved stock source")
    args = ap.parse_args()

    if args.min_w < 1:
        die("--min-w must be at least 1 W")
    source = locate_source(args.kernel_tree)
    backup = source.with_name(source.name + BACKUP_SUFFIX)

    if args.check:
        return check(source)
    if args.revert:
        if not backup.is_file():
            die(f"backup not found: {backup}")
        shutil.copy2(backup, source)
        print(f"restored: {source}")
        return 0

    old = source.read_text()
    new = patch_text(old, args.min_w)
    diff = "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=str(source) + ".stock", tofile=str(source)))
    if args.dry_run:
        print(diff, end="")
        return 0

    if backup.exists():
        die(f"backup already exists: {backup}\nRefusing to overwrite it.")
    shutil.copy2(source, backup)
    source.write_text(new)
    print(f"patched: {source}")
    print(f"backup:  {backup}")
    print(f"V620 driver-side PPT minimum: {args.min_w} W")
    print(f"Review: diff -u {backup} {source}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
