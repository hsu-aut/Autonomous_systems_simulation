#!/usr/bin/env python3
"""Fail if any robot description contains text gazebo_ros2_control cannot pass on.

gazebo_ros2_control forwards the entire URDF to controller_manager as a
command-line parameter override, and rcl parses that value as YAML. Measured
on Humble, the following sequences anywhere in the XML text - a comment is
enough - break it:

    ": "  (colon, space)        parse error; controller_manager never starts,
    ":\\n" (colon, newline)      the spawners log "Could not contact service
                                /controller_manager/list_controllers" forever
                                and the arm hangs limp
    " #"  (space, hash)         SILENT truncation of the rest of the line
    a line starting "- "        silent truncation
    a line starting "? "        silent truncation
    a line starting "---"       silent truncation

This has bitten twice. Run it after editing any xacro that feeds a robot (in the workspace
folder):

    python3 src/neo_simulation2/scripts/check_urdf_for_ros2_control.py

It generates every robot / arm / docking-adapter combination the launch files
can produce (use_gazebo true and false) and scans each, then scans the xacro
sources themselves so an offending line in a file that no current combination
includes is still reported.
"""
import glob
import itertools
import os
import re
import sys

WS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ROBOTS = ('mpo_700', 'mpo_500', 'mp_400', 'mp_500')
ARMS = ('', 'ur5', 'ur10', 'ur5e', 'ur10e')

# (regex, what it does to rcl's parser)
BAD = [
    (re.compile(r': '), 'colon-space -> parse error'),
    (re.compile(r':\n'), 'colon-newline -> parse error'),
    (re.compile(r' #'), 'space-hash -> silently truncates the line'),
    (re.compile(r'^- ', re.M), 'line starting "- " -> silently truncated'),
    (re.compile(r'^\? ', re.M), 'line starting "? " -> silently truncated'),
    (re.compile(r'^---', re.M), 'line starting "---" -> silently truncated'),
]


def scan(text, label):
    """Return a list of (label, what, snippet) findings for one text."""
    found = []
    for rx, what in BAD:
        for m in rx.finditer(text):
            s = max(0, m.start() - 55)
            snippet = text[s:m.start() + 25].replace('\n', '\\n')
            found.append((label, what, snippet))
    return found


def generated_descriptions():
    """Yield (label, urdf_text) for every combination the launch files build."""
    import xacro
    for robot, arm, gz, dock in itertools.product(ROBOTS, ARMS, ('true', 'false'),
                                                   ('False', 'True')):
        if arm and robot not in ('mpo_700', 'mpo_500'):
            continue                     # gazebo_robot.launch.py drops the arm here
        if dock == 'True' and robot != 'mpo_700':
            continue                     # docking adapter is MPO-700 only
        path = os.path.join(WS, 'src', 'neo_simulation2', 'robots', robot,
                            robot + '.urdf.xacro')
        label = '%s arm=%s use_gazebo=%s dock=%s' % (robot, arm or 'none', gz, dock)
        try:
            urdf = xacro.process_file(path, mappings={
                'use_gazebo': gz, 'arm_type': arm, 'use_docking_adapter': dock}).toxml()
        except Exception as exc:                          # noqa: BLE001
            yield label, None, 'xacro failed: %s' % str(exc).splitlines()[0][:120]
            continue
        yield label, urdf, None


def main():
    findings, combos, failures = [], 0, []
    for label, urdf, err in generated_descriptions():
        combos += 1
        if err:
            failures.append((label, err))
            continue
        findings += scan(urdf, label)

    # Sources too: a bad line in a macro that no current combination pulls in
    # would otherwise wait for the day someone does.
    src_files = sorted(set(
        glob.glob(os.path.join(WS, 'src', 'neo_simulation2', '**', '*.xacro'), recursive=True) +
        glob.glob(os.path.join(WS, 'src', 'neo_simulation2', '**', '*.urdf'), recursive=True) +
        glob.glob(os.path.join(WS, 'src', 'ros2_robotiq_gripper', 'robotiq_description', 'urdf', '*.xacro'))))
    src_findings = []
    for f in src_files:
        text = open(f, encoding='utf-8', errors='replace').read()
        # xacro:if/unless/property blocks and $(...) are not YAML-visible after
        # processing only if they vanish; comments and literal text survive.
        # Scanning raw text over-reports xacro syntax like "${x}" harmlessly, but
        # ": " in a comment is exactly what we are after, so keep it simple.
        src_findings += scan(text, os.path.relpath(f, WS))

    print('generated %d robot descriptions, scanned %d source files' % (combos, len(src_files)))
    ok = True
    if failures:
        ok = False
        print('\nxacro could not build these combinations (fix these first):')
        for label, err in failures:
            print('  %-48s %s' % (label, err))
    if findings:
        ok = False
        seen = set()
        print('\nFAIL - generated descriptions contain sequences that break rcl:')
        for label, what, snippet in findings:
            key = (what, snippet)
            if key in seen:
                continue
            seen.add(key)
            print('  [%s]\n     %s\n     ...%s...' % (label, what, snippet))
    if src_findings:
        # Only report source hits that are NOT already explained by a generated
        # finding; these are lines in files no combination currently includes.
        gen_snips = {s for _, _, s in findings}
        extra = [(f, w, s) for f, w, s in src_findings if s not in gen_snips]
        if extra:
            ok = False
            print('\nFAIL - xacro sources contain sequences that would break rcl if included:')
            for f, w, s in extra:
                print('  %s\n     %s\n     ...%s...' % (f, w, s))
    if ok:
        print('OK - nothing that gazebo_ros2_control cannot pass to controller_manager')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
