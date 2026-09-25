#!/usr/bin/env python3
"""Experimental SAP stat v5 / Unicode / 896-byte main-record reader.
Standard library only, Python >= 3.8. See README.md for evidence and limits.
"""
import argparse
import csv
import datetime as dt
import io
import json
import math
import pathlib
import re
import struct
import sys

START = '*SA*'.encode('utf-16-be')
END = '*SE*'.encode('utf-16-be')
TASKS = {3: 'S', 4: 'B', 6: 'Y', 7: 'A', 9: 'R', 11: 'G', 14: 'K', 15: 'Z', 18: '3'}
DB_TIME_OFFSETS = (0x50, 0x68, 0x80, 0x98, 0xb0, 0xc0, 0xd8, 0xf8, 0x110, 0x128)

class FormatError(ValueError):
    pass


def uint(data, offset, size):
    return int.from_bytes(data[offset:offset + size], 'big')


def number(data, offset):
    value = struct.unpack_from('>d', data, offset)[0]
    if not math.isfinite(value) or value < 0:
        raise FormatError('invalid nonnegative double at 0x%x' % offset)
    return value


def string(data, offset, size):
    return data[offset:offset + size].decode('utf-16-be').rstrip(' \0')


def read_hexdump(text):
    """Read supplied od-style hex addresses + bytes; expand '*' repeated rows.
    Address base is hexadecimal. Character-rendering lines are ignored.
    """
    out = bytearray()
    previous = None
    repeated = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip() == '*':
            if previous is None or repeated:
                raise FormatError('invalid * on dump line %d' % lineno)
            repeated = True
            continue
        match = re.fullmatch(r'([0-9a-fA-F]{7,16})\s+((?:[0-9a-fA-F]{2}\s*){1,16})\s*', line)
        final = re.fullmatch(r'([0-9a-fA-F]{7,16})\s*', line)
        if not match and not final:
            continue
        offset = int((match or final)[1], 16)
        gap = offset - len(out)
        if gap:
            if gap < 0 or not repeated or not previous or gap % len(previous):
                raise FormatError('unexplained address gap on dump line %d' % lineno)
            # Explicit limit prevents a malformed text address allocating huge memory.
            if offset > 512 * 1024 * 1024:
                raise FormatError('hexdump exceeds 512 MiB; use binary input')
            out.extend(previous * (gap // len(previous)))
        elif repeated:
            raise FormatError('* without a repeated row on line %d' % lineno)
        repeated = False
        if match:
            previous = bytes.fromhex(match[2])
            out.extend(previous)
    if repeated:
        raise FormatError('trailing * has no address to determine repeat count')
    if not out:
        raise FormatError('no hexadecimal byte lines found')
    return bytes(out)


def expand_record(data, pos, prefix):
    """Expand exactly the declared logical size; never search for end markers."""
    start = pos
    if data[pos:pos + 8] != START or pos + 10 > len(data):
        raise FormatError('missing record start at group +0x%x' % pos)
    length = uint(data, pos + 8, 2)
    if length < max(prefix, 18) or pos + prefix > len(data):
        raise FormatError('invalid/truncated logical record header')
    out = bytearray(data[pos:pos + prefix])
    pos += prefix
    while len(out) < length:
        if pos >= len(data):
            raise FormatError('truncated compressed record at +0x%x' % start)
        byte = data[pos]
        pos += 1
        if byte != 0x14:
            out.append(byte)
        else:
            if pos >= len(data):
                raise FormatError('truncated compression escape')
            opcode = data[pos]
            pos += 1
            if opcode == 0x14:
                out.append(0x14)
            elif opcode in (1, 2):
                if pos >= len(data) or data[pos] == 0:
                    raise FormatError('missing/unsupported compression run count')
                count = data[pos]
                pos += 1
                out.extend((b'\x00 ' if opcode == 1 else b'\x00') * count)
            else:
                raise FormatError('unsupported compression opcode 0x%02x' % opcode)
        if len(out) > length:
            raise FormatError('compression run exceeds declared logical length')
    if out[-8:] != END:
        raise FormatError('logical record end marker does not match')
    return bytes(out), pos


def parse_group(data, absolute_offset):
    if len(data) < 120 or data[:8] != START:
        raise FormatError('invalid main header')
    if uint(data, 8, 2) != 896 or data[10] != 0 or data[13] not in (3, 7):
        raise FormatError('unsupported main layout/flags; expected sample layout 896 / 00 / 03 or 07')
    total = uint(data, 14, 6)
    count = uint(data, 20, 2)
    if total != len(data) or count < 1 or count > (len(data) - 120) // 10:
        raise FormatError('invalid group size/count')
    main, pos = expand_record(data, 0, 120)
    records = [(0, pos, main)]
    for _ in range(count - 1):
        old = pos
        sub, pos = expand_record(data, pos, 10)
        records.append((old, pos, sub))
    trailer = data[pos:]
    if (len(trailer) != 16 or uint(trailer, 0, 4) != total or
            uint(trailer, 4, 2) != count or trailer[6:14] != END):
        raise FormatError('group trailer size/count/end marker does not match')
    # Validate next/previous type links independently of physical markers.
    for i, (_, _, rec) in enumerate(records):
        expected_next = records[i + 1][2][10] if i + 1 < count else 255
        expected_prev = records[i - 1][2][10] if i else 255
        if rec[11] != expected_next or rec[12] != expected_prev:
            raise FormatError('subrecord type chain does not match')
    return main, records, trailer[-2:].hex()


def groups(stream, warnings, audit, allow_truncated=False):
    version = stream.read(2)
    if version != b'\x00\x05':
        raise FormatError('unsupported file prefix %s; only 0005 tested' % version.hex())
    offset = 2
    while True:
        head = stream.read(22)
        if not head:
            return
        if len(head) < 22:
            if allow_truncated:
                warnings.append('Incomplete final header at 0x%x; omitted.' % offset)
                return
            raise FormatError('truncated header at 0x%x' % offset)
        if head[:8] != START:
            raise FormatError('missing start at file 0x%x' % offset)
        kind = head[10]
        if kind in (253, 254):
            length = uint(head, 8, 2)
            if length != 180:
                raise FormatError('unsupported administrative header length')
            data = head + stream.read(length - len(head))
            if len(data) != length or data[-8:] != END:
                raise FormatError('incomplete/invalid administrative header')
            audit.append({'offset': offset, 'kind': kind, 'stored_bytes': length})
            offset += length
            continue
        if kind != 0:
            raise FormatError('unsupported top-level type 0x%02x at 0x%x' % (kind, offset))
        length = uint(head, 14, 6)
        if not 136 <= length <= 64 * 1024 * 1024:
            raise FormatError('invalid/unsupported group length %d' % length)
        data = head + stream.read(length - len(head))
        if len(data) != length:
            if allow_truncated:
                warnings.append('Incomplete final group at 0x%x: %d of %d bytes; omitted.' %
                                (offset, len(data), length))
                return
            raise FormatError('incomplete final group at 0x%x; use --allow-truncated for excerpts' % offset)
        try:
            main, records, trailer_tail = parse_group(data, offset)
        except FormatError as exc:
            raise FormatError('file 0x%x: %s' % (offset, exc)) from exc
        audit.append({'offset': offset, 'stored_bytes': length,
                      'subrecords_including_main': len(records), 'trailer_tail_uninterpreted': trailer_tail,
                      'records': [{'offset': offset + a, 'stored_bytes': z - a,
                                   'logical_bytes': len(r), 'type': r[10]} for a, z, r in records]})
        yield offset, main, records
        offset += length


def decode_row(offset, main, records, timezone, server):
    start_s, start_us, end_s, end_us = struct.unpack_from('>4I', main, 40)
    if start_us >= 1000000 or end_us >= 1000000:
        raise FormatError('invalid timestamp microseconds')
    start = dt.datetime.fromtimestamp(start_s, dt.timezone.utc) + dt.timedelta(microseconds=start_us)
    elapsed_us = (end_s - start_s) * 1000000 + end_us - start_us
    raw_us, excluded_us, cpu_us, wait_us = [number(main, x) for x in (56, 64, 72, 80)]
    residual = raw_us + excluded_us - wait_us - elapsed_us
    if abs(residual) > 1:
        raise FormatError('timing identity differs by %.3f us at 0x%x; unsupported semantics' % (residual, offset))
    task_id = main[0x198]
    raw_program = string(main, 0x278, 80)
    program = {4: '(BATCH)', 6: 'Buf.Sync', 7: 'AutoABAP', 9: 'RFC'}.get(task_id, raw_program)
    db_values = []
    db_known = True
    for _, _, sub in records[1:]:
        if sub[10] == 0x12:
            if len(sub) != 312:
                db_known = False
            else:
                db_values.append({'connection': string(sub, 14, 60),
                                  'candidate_time_us': sum(number(sub, p) for p in DB_TIME_OFFSETS)})
    return {'offset': offset, 'date': start.astimezone(timezone).strftime('%Y-%m-%d'),
            'started': start.astimezone(timezone).strftime('%H:%M:%S'),
            'started_iso': start.astimezone(timezone).isoformat(),
            'server': server or '', 'transaction': None,
            'transaction_candidate': string(main, 0x2d0, 40),
            'terminal_candidate': string(main, 0x250, 40),
            'program': program, 'raw_program': raw_program,
            'task': TASKS.get(task_id, '?'), 'task_id': task_id,
            'screen': string(main, 0x2c8, 8), 'wp': uint(main, 0x194, 2),
            'user': string(main, 0x19c, 24) or 'UNKNOWN',
            'response_ms_est': (raw_us + excluded_us) / 1000,
            'time_in_wps_ms_est': (raw_us - wait_us) / 1000,
            'wait_ms': wait_us / 1000, 'cpu_ms': cpu_us / 1000,
            'db_req_ms_est': sum(v['candidate_time_us'] for v in db_values) / 1000 if db_known else None,
            'vmc_elapsed_ms': None,
            'memory_kib': number(main, 0x158) / 1024,
            'transferred_kib': uint(main, 0x134, 4) / 1024,
            'raw_response_ms': raw_us / 1000, 'excluded_interval_ms': excluded_us / 1000,
            'elapsed_ms': elapsed_us / 1000, 'timing_residual_us': residual,
            'database_candidates': db_values,
            'subrecord_types': [r[10] for _, _, r in records[1:]]}


COLUMNS = [('started', 'Started', 8), ('server', 'Server', 18), ('transaction', 'Transaction', 20),
           ('program', 'Program', 40), ('task', 'T', 1), ('screen', 'Scr.', 4), ('wp', 'WP', 3),
           ('user', 'User', 12), ('response_ms_est', 'Resp~ms', 9),
           ('time_in_wps_ms_est', 'InWP~ms', 9), ('wait_ms', 'Wait ms', 8), ('cpu_ms', 'CPU ms', 8),
           ('db_req_ms_est', 'DB~ms', 8), ('vmc_elapsed_ms', 'VMC ms', 8),
           ('memory_kib', 'Mem KiB', 9), ('transferred_kib', 'Xfer KiB', 10)]


def write_table(rows, out):
    out.write(' | '.join(title.ljust(width) for _, title, width in COLUMNS) + '\n')
    for row in rows:
        cells = []
        for key, _, width in COLUMNS:
            value = row[key]
            if value is None:
                text = '?'
            elif isinstance(value, float):
                text = ('%.1f' % value) if key == 'transferred_kib' else str(int(math.floor(value + 0.5)))
            else:
                text = str(value)
            cells.append(text.rjust(width) if isinstance(value, (int, float)) or value is None else text.ljust(width))
        out.write(' | '.join(cells) + '\n')
    out.write('\n~ = inferred STAD aggregation, not validated against matching executions; ? = not decoded.\n')


def parse_timezone(value):
    if value.upper() in ('UTC', 'Z'):
        return dt.timezone.utc
    m = re.fullmatch(r'([+-])(\d{2}):(\d{2})', value)
    if not m or int(m[2]) > 23 or int(m[3]) > 59:
        raise argparse.ArgumentTypeError('use UTC or a numeric UTC offset, e.g. +02:00')
    minutes = (int(m[2]) * 60 + int(m[3])) * (1 if m[1] == '+' else -1)
    return dt.timezone(dt.timedelta(minutes=minutes))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=pathlib.Path)
    parser.add_argument('--input-format', choices=('auto', 'binary', 'hexdump'), default='auto')
    parser.add_argument('--format', choices=('table', 'csv', 'json'), default='table')
    parser.add_argument('--output', '-o', type=pathlib.Path)
    parser.add_argument('--audit', type=pathlib.Path, help='write record boundaries and diagnostics as JSON')
    parser.add_argument('--server', help='local instance name; supplied explicitly, not guessed from RFC endpoints')
    parser.add_argument('--utc-offset', type=parse_timezone, default=dt.timezone.utc)
    parser.add_argument('--allow-truncated', action='store_true', help='omit incomplete final record with a warning')
    parser.add_argument('--user', help='exact username filter')
    parser.add_argument('--from', dest='from_time', help='inclusive displayed ISO date/time, e.g. 2026-09-23T06:00:00')
    parser.add_argument('--to', dest='to_time', help='exclusive displayed ISO date/time')
    args = parser.parse_args(argv)
    for dest in (args.output, args.audit):
        if dest and dest.resolve() == args.input.resolve():
            parser.error('output must not overwrite input')
    if args.output and args.audit and args.output.resolve() == args.audit.resolve():
        parser.error('--output and --audit must use different files')
    warnings, audit, rows = [], [], []
    try:
        with args.input.open('rb') as source:
            prefix = source.read(2)
            source.seek(0)
            is_dump = args.input_format == 'hexdump' or (args.input_format == 'auto' and prefix != b'\x00\x05')
            stream = io.BytesIO(read_hexdump(source.read().decode('utf-8-sig'))) if is_dump else source
            for offset, record, subs in groups(stream, warnings, audit, args.allow_truncated):
                rows.append(decode_row(offset, record, subs, args.utc_offset, args.server))
        parsed_count = len(rows)
        def bound(text):
            if not text:
                return None
            value = dt.datetime.fromisoformat(text)
            return value.replace(tzinfo=args.utc_offset) if value.tzinfo is None else value
        lower, upper = bound(args.from_time), bound(args.to_time)
        rows = [r for r in rows if (not args.user or r['user'] == args.user)
                and (not lower or dt.datetime.fromisoformat(r['started_iso']) >= lower)
                and (not upper or dt.datetime.fromisoformat(r['started_iso']) < upper)]
        rows.sort(key=lambda r: (r['started_iso'], r['wp'], r['offset']))
        if args.audit:
            args.audit.write_text(json.dumps({'parsed_rows': parsed_count, 'output_rows': len(rows),
                                  'warnings': warnings, 'groups': audit}, indent=2) + '\n', encoding='utf-8')
        output = args.output.open('w', encoding='utf-8', newline='') if args.output else sys.stdout
        try:
            if args.format == 'json':
                json.dump({'layout': 'experimental-v5-unicode-main896', 'warnings': warnings,
                           'limitations': ['STAD aggregation estimates require a matching export',
                                           'VMC and transaction code not decoded', 'server supplied by caller',
                                           'timestamps interpreted as Unix UTC before explicit conversion'],
                           'rows': rows}, output, indent=2)
                output.write('\n')
            elif args.format == 'csv':
                fields = [c[0] for c in COLUMNS] + ['date', 'started_iso', 'raw_program', 'task_id', 'offset',
                          'raw_response_ms', 'excluded_interval_ms', 'elapsed_ms', 'timing_residual_us']
                writer = csv.DictWriter(output, fields, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(rows)
            else:
                write_table(rows, output)
        finally:
            if args.output:
                output.close()
        for warning in warnings:
            print('WARNING: ' + warning, file=sys.stderr)
        print('%d complete main records parsed; %d rows output. Experimental sample-specific layout.' %
              (parsed_count, len(rows)), file=sys.stderr)
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
