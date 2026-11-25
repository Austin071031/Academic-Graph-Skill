#!/usr/bin/env python3
"""Prove a native SVG edit preserves every undeclared ID, attribute, text and subtree."""
import argparse
import hashlib
import json
import pathlib
import sys
import xml.etree.ElementTree as ET


def local(name):
    return name.rsplit('}', 1)[-1]


def norm(value):
    return ' '.join((value or '').split())


def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def parse(path):
    root = ET.parse(path, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))).getroot()
    index = {}
    for elem in root.iter():
        ident = elem.get('id')
        if ident:
            if ident in index:
                raise ValueError('Duplicate ID: ' + ident)
            index[ident] = elem
    return root, index


def attrs(elem):
    return {local(k): v for k, v in elem.attrib.items()}


def shape(elem):
    return (local(elem.tag), tuple(shape(c) for c in list(elem)))


def masked(elem, targets):
    ident = elem.get('id')
    if ident in targets:
        return ('declared-edit', local(elem.tag), ident)
    return (local(elem.tag), tuple(sorted(attrs(elem).items())), norm(elem.text), tuple(masked(c, targets) for c in list(elem)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', required=True)
    parser.add_argument('--revised', required=True)
    parser.add_argument('--changes', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    violations, declared = [], []
    try:
        original, before = parse(args.original)
        revised, after = parse(args.revised)
        changes = json.loads(pathlib.Path(args.changes).read_text(encoding='utf-8'))
        if digest(args.original) != changes['input_sha256'] or digest(args.revised) != changes['output_sha256']:
            raise ValueError('Compared file hash differs from changes.json')
        edits = changes['changes']
        targets = {op['id'] for op in edits}
        if not targets:
            raise ValueError('No declared edits')
        if set(before) != set(after):
            violations.append({'check': 'stable_ids', 'before_only': sorted(set(before)-set(after)), 'after_only': sorted(set(after)-set(before))})
        if masked(original, targets) != masked(revised, targets):
            violations.append({'check': 'undeclared_subtree', 'detail': 'An element outside the declared target IDs changed'})
        for ident in sorted(targets):
            if ident not in before or ident not in after:
                violations.append({'element_id': ident, 'check': 'declared_target_exists', 'passed': False})
                continue
            old, new = before[ident], after[ident]
            ops = [op for op in edits if op['id'] == ident]
            attr_keys = {key for op in ops if op['operation'] == 'attrs' for key in op['value']}
            text_allowed = any(op['operation'] == 'text' for op in ops)
            allowed = set(attr_keys) | {'id'}
            differences = {key for key in set(attrs(old)) | set(attrs(new)) if attrs(old).get(key) != attrs(new).get(key)}
            unexpected = differences - allowed
            if unexpected:
                violations.append({'element_id': ident, 'check': 'declared_attributes_only', 'unexpected': sorted(unexpected)})
            if shape(old) != shape(new):
                violations.append({'element_id': ident, 'check': 'unchanged_subtree_structure'})
            old_text = (norm(old.text), tuple(norm(c.text) for c in list(old)))
            new_text = (norm(new.text), tuple(norm(c.text) for c in list(new)))
            if not text_allowed and old_text != new_text:
                violations.append({'element_id': ident, 'check': 'text_requires_text_operation'})
            if text_allowed and old.tag.rsplit('}', 1)[-1] not in ('text', 'tspan'):
                violations.append({'element_id': ident, 'check': 'text_target_is_native_text'})
            declared.append({'element_id': ident, 'operations': [{'operation': op['operation'], 'value': op['value']} for op in ops]})
        result = {'status': 'passed' if not violations else 'failed', 'original_sha256': changes['input_sha256'],
                  'revised_sha256': changes['output_sha256'], 'preserved_id_count': len(set(before)-targets),
                  'declared_edits': declared, 'violations': violations,
                  'scope': 'Semantic XML subtree comparison; scientific correctness and visual review still required.'}
    except Exception as exc:
        result = {'status': 'failed', 'error': str(exc), 'violations': violations}
    pathlib.Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
