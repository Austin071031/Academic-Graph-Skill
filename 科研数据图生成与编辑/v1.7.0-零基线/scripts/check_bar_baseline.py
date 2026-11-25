#!/usr/bin/env python3
"""Fail when a bar axis drops zero. Reads export_checks.json written by charts.py."""
import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checks', required=True)
    args = parser.parse_args()
    try:
        report = json.loads(open(args.checks, encoding='utf-8').read())
        issues = [item for item in report.get('issues', []) if item.get('kind') == 'bar_baseline_truncated']
        ok = not issues
        print(json.dumps({'status': 'passed' if ok else 'failed', 'issues': issues}, ensure_ascii=False))
        return 0 if ok else 1
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
