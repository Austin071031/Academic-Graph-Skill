#!/usr/bin/env python3
"""Mechanically compare two native SVG files at stable-ID object granularity.

This tool checks XML structure and declared edits only. It does not assess
scientific/semantic correctness, render appearance, or native Office files.
No network requests are made.
"""
import argparse
import hashlib
import json
import os
import pathlib
import sys
import urllib.parse
import xml.etree.ElementTree as ET


RASTER_EXTENSIONS = {
    '.avif', '.bmp', '.gif', '.jpeg', '.jpg', '.pbm', '.pgm', '.png',
    '.pnm', '.ppm', '.tif', '.tiff', '.webp',
}
LIMITATIONS = [
    'Only native SVG XML is compared; native Office/PPTX and other formats are not covered.',
    'Elements without stable IDs have no independent before/after identity; anonymous content is visible only within its nearest identified ancestor.',
    'An ID absent from either file cannot prove preservation; missing original IDs and undeclared additions are failures.',
    'ID-scoped comparison cannot establish preservation of unidentifiable document-level content or certify complete visual equivalence.',
    'XML digests do not certify scientific, semantic, or visual correctness; source and rendered reviews remain necessary.',
    'Image checks classify references and measure local relative href existence only; linked content equivalence is not checked and no network fetching is performed.',
]


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    return sha256_bytes(path.read_bytes())


def local_name(tag):
    return tag.rsplit('}', 1)[-1]


def text_token(value, significant_whitespace):
    if value is None:
        return None
    if not significant_whitespace and not value.strip():
        return None
    return {'text': value}


def scoped_content(element):
    """Encode local content, stopping at child elements that own a stable ID.

    Thus editing an identified tspan does not also mark its identified text or
    group ancestors changed. Anonymous tspans, geometry and content remain in
    the nearest identified object's digest. Ordered text/tspan tokens are kept.
    Text whitespace is preserved inside text/tspan; indentation elsewhere is
    ignored so XML pretty-printing alone does not create an object difference.
    """
    text_context = local_name(element.tag) in ('text', 'tspan')

    def encode_children(parent, in_text):
        result = []
        token = text_token(parent.text, in_text)
        if token is not None:
            result.append(token)
        for child in parent:
            child_id = child.get('id')
            if child_id:
                result.append({'id_reference': child_id, 'tag': child.tag})
            else:
                child_text_context = in_text or local_name(child.tag) in ('text', 'tspan')
                result.append({
                    'element': {
                        'tag': child.tag,
                        'attributes': sorted(child.attrib.items()),
                        'content': encode_children(child, child_text_context),
                    }
                })
            token = text_token(child.tail, in_text)
            if token is not None:
                result.append(token)
        return result

    return encode_children(element, text_context)


def object_representation(element):
    return {
        'tag': element.tag,
        'attributes': sorted(element.attrib.items()),
        'content': scoped_content(element),
    }


def representation_digest(element):
    encoded = json.dumps(
        object_representation(element), ensure_ascii=False,
        sort_keys=True, separators=(',', ':'),
    ).encode('utf-8')
    return sha256_bytes(encoded)


def inventory(root):
    objects = {}
    for element in root.iter():
        ident = element.get('id')
        if not ident:
            continue
        objects.setdefault(ident, []).append(element)
    return objects


def object_digest(entries):
    # Lists retain occurrence information, so duplicate IDs cannot disappear
    # from the comparison merely because a dictionary indexed them.
    values = [representation_digest(element) for element in entries]
    encoded = json.dumps(values, separators=(',', ':')).encode('utf-8')
    return sha256_bytes(encoded)


def compare_objects(before_objects, after_objects, declared):
    records = {}
    actual_changed = set()
    missing = set()
    duplicates_before = set()
    duplicates_after = set()
    all_ids = sorted(set(before_objects) | set(after_objects))
    for ident in all_ids:
        before_entries = before_objects.get(ident, [])
        after_entries = after_objects.get(ident, [])
        before_digest = object_digest(before_entries) if before_entries else None
        after_digest = object_digest(after_entries) if after_entries else None
        differs = before_digest != after_digest
        duplicate_before = len(before_entries) > 1
        duplicate_after = len(after_entries) > 1
        if duplicate_before:
            duplicates_before.add(ident)
        if duplicate_after:
            duplicates_after.add(ident)
        if not before_entries:
            status = 'added'
        elif not after_entries:
            status = 'missing'
        elif duplicate_before or duplicate_after:
            status = 'duplicate_id'
        else:
            status = 'changed' if differs else 'unchanged'
        if differs:
            actual_changed.add(ident)
        if before_entries and not after_entries:
            missing.add(ident)
        records[ident] = {
            'declared': ident in declared,
            'status': status,
            'before_occurrences': len(before_entries),
            'after_occurrences': len(after_entries),
            'before_tag': before_entries[0].tag if before_entries else None,
            'after_tag': after_entries[0].tag if after_entries else None,
            'before_digest': before_digest,
            'after_digest': after_digest,
            'actually_differs': differs,
        }
    return records, actual_changed, missing, duplicates_before, duplicates_after


def load_declarations(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(value, list):
        entries = value
        supplied_hash = None
        root_kind = 'list'
    elif isinstance(value, dict) and isinstance(value.get('changes'), list):
        entries = value['changes']
        supplied_hash = value.get('input_sha256')
        root_kind = 'changes_object'
    else:
        raise ValueError('Change log must be a list of ID entries or an object with a changes list')
    declared = []
    errors = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not entry['id']:
            errors.append('Change entry %d has no non-empty string id' % index)
        else:
            declared.append(entry['id'])
    duplicates = sorted({ident for ident in declared if declared.count(ident) > 1})
    if duplicates:
        errors.append('Duplicate IDs in change declarations: ' + ', '.join(duplicates))
    return declared, supplied_hash, root_kind, errors


def image_references(after_path, root):
    references = []
    warnings = []
    for element in root.iter():
        if local_name(element.tag) != 'image':
            continue
        href = element.get('href')
        if href is None:
            href = element.get('{http://www.w3.org/1999/xlink}href')
        ident = element.get('id')
        item = {
            'id': ident,
            'href': href,
            'kind': 'missing_href',
            'raster': None,
            'local_relative_path': None,
            'local_relative_exists': None,
            'local_relative_is_file': None,
            'network_fetch_performed': False,
        }
        if href is None or not href.strip():
            warnings.append('SVG image %s has no href' % (ident or '(no ID)'))
            references.append(item)
            continue
        href = href.strip()
        item['href'] = href
        parsed = urllib.parse.urlsplit(href)
        suffix = pathlib.Path(parsed.path).suffix.lower()
        raster_by_suffix = suffix in RASTER_EXTENSIONS
        if parsed.scheme.lower() == 'data':
            media_type = parsed.path.split(',', 1)[0].split(';', 1)[0].lower()
            is_svg = media_type in ('image/svg+xml', 'text/xml', 'application/xml')
            item['kind'] = 'embedded_svg' if is_svg else 'embedded_raster'
            item['raster'] = not is_svg
            warnings.append('Embedded image %s (%s); embedded content is not independently editable' % (ident or '(no ID)', media_type or 'unknown media type'))
        elif href.startswith('//') or parsed.scheme.lower() in ('http', 'https', 'ftp'):
            item['kind'] = 'external_remote'
            item['raster'] = raster_by_suffix if suffix else None
            warnings.append('External remote image %s: %s; not fetched' % (ident or '(no ID)', href))
        elif parsed.scheme:
            item['kind'] = 'external_uri'
            item['raster'] = raster_by_suffix if suffix else None
            warnings.append('External URI image %s: %s; not fetched' % (ident or '(no ID)', href))
        elif parsed.path.startswith('/'):
            item['kind'] = 'external_absolute_path'
            item['raster'] = raster_by_suffix if suffix else None
            warnings.append('External absolute-path image %s: %s' % (ident or '(no ID)', href))
        elif not parsed.path:
            item['kind'] = 'fragment_or_empty_reference'
            item['raster'] = None
            warnings.append('Non-file image reference %s: %s' % (ident or '(no ID)', href))
        else:
            item['kind'] = 'local_relative_raster' if raster_by_suffix else 'local_relative_linked'
            item['raster'] = raster_by_suffix if suffix else None
            relative = urllib.parse.unquote(parsed.path)
            target = after_path.parent / relative
            item['local_relative_path'] = relative
            item['local_relative_exists'] = target.exists()
            item['local_relative_is_file'] = target.is_file()
            warnings.append('Local linked image %s: %s; exists=%s, is_file=%s' % (
                ident or '(no ID)', href, item['local_relative_exists'],
                item['local_relative_is_file']))
        references.append(item)
    return references, warnings


def resolved(path):
    return pathlib.Path(path).expanduser().resolve()


def same_file(first, second):
    try:
        return os.path.samefile(str(first), str(second))
    except (FileNotFoundError, OSError):
        return resolved(first) == resolved(second)


def atomic_write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp.%d' % os.getpid())
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
            encoding='utf-8',
        )
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def audit(args):
    before = pathlib.Path(args.before)
    after = pathlib.Path(args.after)
    changes = pathlib.Path(args.changes)
    out = pathlib.Path(args.out)
    errors = []
    warnings = []

    # Refuse unsafe output aliases before creating any output file.
    for label, source in [('before', before), ('after', after), ('changes', changes)]:
        if same_file(out, source):
            raise ValueError('Output must not overwrite or alias the %s input' % label)
    if same_file(before, after):
        raise ValueError('Original and revised SVG must be different files and paths')

    before_hash = file_hash(before)
    after_hash = file_hash(after)
    before_stat = before.stat()
    report = {
        'status': 'failed',
        'comparison': 'parsed_svg_xml_per_stable_id',
        'before': {'path': str(before), 'sha256': before_hash},
        'after': {'path': str(after), 'sha256': after_hash},
        'change_log': {'path': str(changes)},
        'original_ids_preserved': False,
        'changed_ids_exactly_declared': False,
        'input_sha256_matches_original': False,
        'ids': {},
        'image_references': [],
        'warnings': warnings,
        'errors': errors,
        'limitations': LIMITATIONS,
        'network_fetch_performed': False,
        'scientific_semantic_correctness': 'not_assessed',
        'native_office_preservation': 'not_covered',
    }

    declared = []
    declarations_valid = False
    try:
        declared, supplied_hash, root_kind, declaration_errors = load_declarations(changes)
        errors.extend(declaration_errors)
        declarations_valid = not declaration_errors
        report['change_log'].update({
            'root_kind': root_kind,
            'declared_ids': declared,
            'input_sha256': supplied_hash,
        })
        hash_matches = (
            isinstance(supplied_hash, str)
            and supplied_hash.lower() == before_hash
        )
        report['input_sha256_matches_original'] = hash_matches
        if supplied_hash is None:
            errors.append('Change log input_sha256 is missing; it must equal the actual original SHA256')
        elif not hash_matches:
            errors.append('Change log input_sha256 does not equal the actual original SHA256')
    except Exception as exc:
        errors.append('Cannot read change log: %s' % exc)
        report['change_log']['declared_ids'] = []

    before_objects = {}
    after_objects = {}
    try:
        before_root = ET.parse(str(before)).getroot()
        if local_name(before_root.tag) != 'svg':
            errors.append('Before file root element is not SVG')
        before_objects = inventory(before_root)
    except Exception as exc:
        errors.append('Cannot parse original SVG: %s' % exc)
    try:
        after_root = ET.parse(str(after)).getroot()
        if local_name(after_root.tag) != 'svg':
            errors.append('Revised file root element is not SVG')
        after_objects = inventory(after_root)
        references, image_warnings = image_references(after, after_root)
        report['image_references'] = references
        warnings.extend(image_warnings)
    except Exception as exc:
        errors.append('Cannot parse revised SVG: %s' % exc)

    report['id_counts'] = {
        'before_occurrences': sum(len(v) for v in before_objects.values()),
        'after_occurrences': sum(len(v) for v in after_objects.values()),
        'before_unique': len(before_objects),
        'after_unique': len(after_objects),
        'declared_unique': len(set(declared)),
    }
    if not before_objects:
        errors.append('Original SVG has no stable IDs; object-level preservation cannot be established')

    records = {}
    actual_changed = set()
    if before_objects or after_objects:
        records, actual_changed, missing, duplicates_before, duplicates_after = compare_objects(
            before_objects, after_objects, set(declared))
        report['ids'] = records
        report['original_ids_preserved'] = not missing
        for ident in sorted(missing):
            errors.append('Original ID missing in revised SVG: ' + ident)
        for ident in sorted(duplicates_before):
            errors.append('Duplicate ID in original SVG: ' + ident)
        for ident in sorted(duplicates_after):
            errors.append('Duplicate ID in revised SVG: ' + ident)

        if declarations_valid:
            declared_set = set(declared)
            undeclared = actual_changed - declared_set
            not_actually_different = declared_set - actual_changed
            for ident in sorted(undeclared):
                errors.append('Undeclared changed or added ID: ' + ident)
            for ident in sorted(not_actually_different):
                errors.append('Declared ID has no actual before/after difference: ' + ident)
            report['changed_ids_exactly_declared'] = not undeclared and not not_actually_different
        report['summary'] = {
            'actually_different_ids': sorted(actual_changed),
            'declared_ids': sorted(set(declared)),
            'changed_ids': sorted(k for k, v in records.items() if v['status'] == 'changed'),
            'unchanged_ids': sorted(k for k, v in records.items() if v['status'] == 'unchanged'),
            'added_ids': sorted(k for k, v in records.items() if v['status'] == 'added'),
            'missing_ids': sorted(k for k, v in records.items() if v['status'] == 'missing'),
        }

    # Detect accidental/external modification of the source during this audit.
    if file_hash(before) != before_hash or before.stat().st_size != before_stat.st_size:
        errors.append('Original SVG changed during the audit')
    report['original_preserved_by_audit'] = file_hash(before) == before_hash
    report['status'] = 'passed' if not errors else 'failed'
    report['mechanical_id_audit'] = report['status']
    atomic_write_json(out, report)
    return 0 if not errors else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True, help='untouched original native SVG')
    parser.add_argument('--after', required=True, help='revised native SVG')
    parser.add_argument('--changes', required=True, help='patch .changes.json or list of {id: ...} entries')
    parser.add_argument('--out', required=True, help='JSON audit report; never the original SVG')
    args = parser.parse_args(argv)
    try:
        return audit(args)
    except Exception as exc:
        print(json.dumps({
            'status': 'failed', 'tool': 'edit_audit', 'error': str(exc),
            'scientific_semantic_correctness': 'not_assessed',
        }, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
