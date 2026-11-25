#!/usr/bin/env python3
"""Require every rendered bar panel to have an explicit passing zero-baseline check."""
import argparse
import json
import pathlib
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checks', required=True)
    args = parser.parse_args()
    try:
        report = json.loads(pathlib.Path(args.checks).read_text(encoding='utf-8'))
        zero = [c for c in report.get('checks', []) if c.get('check') == 'bar_zero_baseline']
        issues = [i for i in report.get('issues', []) if i.get('kind') == 'bar_baseline_truncated']
        ok = bool(zero) and all(c['passed'] for c in zero) and not issues
        result = {'status': 'passed' if ok else 'failed', 'zero_baseline_checks': zero, 'issues': issues}
        print(json.dumps(result, ensure_ascii=False))
        return 0 if ok else 1
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
