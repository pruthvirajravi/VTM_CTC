#!/usr/bin/env python3
"""Independent dense-matrix evaluation; no VTM fast-transform code is used."""
import ast
import json
from pathlib import Path
import re
import numpy as np

def matrices(source):
    text = Path(source).read_text()
    result = {}
    for match in re.finditer(r'#define DEFINE_(DCT2|DST7|DCT8)_P(\d+)_MATRIX\(([^)]*)\)\s*\\\n(.*?)(?=\n\s*\n)', text, re.S):
        kind, size, params, body = match.groups()
        name = 'DEFINE_' + kind + '_P' + size + '_MATRIX'
        # The last numeric invocation is the normal-precision matrix. The
        # workflow explicitly builds normal forward precision and 16-bit Pel.
        values = re.findall(name + r'\(([\d,\s]+)\)', text)[-1]
        mapping = dict(zip([x.strip() for x in params.split(',')], [x.strip() for x in values.split(',')]))
        body = body.replace('\\', '').replace('{', '[').replace('}', ']')
        body = re.sub(r'\b[A-Za-z]+\b', lambda m: mapping[m[0]], body)
        matrix = np.array(ast.literal_eval(body.strip()), dtype=np.int64)
        if matrix.shape != (int(size), int(size)):
            raise ValueError('Malformed matrix ' + name)
        result[kind, int(size)] = matrix
    if len(result) != 14:
        raise ValueError('Expected 14 complete transform matrices')
    return result

def rounded(a, shift):
    if shift < 0:
        raise ValueError('Negative shift')
    return a if shift == 0 else (a + (1 << (shift - 1))) >> shift

def reference(p, mats):
    w, h, bd, dr = (p[k] for k in ['w', 'h', 'bit_depth', 'max_log2_dynamic_range'])
    ew, eh = w-p['skip_w'], h-p['skip_h']
    a = np.array(p['input'], dtype=np.int64).reshape(h,w)
    mh = mats[p['tr_h'], w] if w > 1 else None
    mv = mats[p['tr_v'], h] if h > 1 else None
    if p['direction'] == 'FWD':
        if w > 1 and h > 1:
            tmp = rounded(a @ mh.T, w.bit_length()-1 + bd + 6 - dr)
            tmp[:, ew:] = 0
            out = rounded(mv @ tmp, h.bit_length()-1 + 6)
            out[eh:, :] = 0
            out[:, ew:] = 0
        else:
            n = max(w,h)
            out = rounded(a @ mh.T if h==1 else mv @ a, n.bit_length()-1+bd+6-dr)
            out[eh:, :] = 0
            out[:, ew:] = 0
    else:
        a[eh:, :] = 0
        a[:, ew:] = 0
        if w > 1 and h > 1:
            tmp = np.clip(rounded(mv.T @ a, 7), -(1<<dr), (1<<dr)-1)
            out = np.clip(rounded(tmp @ mh, 6+dr-1-bd), -32768, 32767)
        else:
            out = np.clip(rounded(a @ mh if h==1 else mv.T @ a, 6+dr-bd), -32768, 32767)
    return out.reshape(-1).tolist()

def verify(path, mats):
    count = values = 0
    with open(path) as f:
        for line in f:
            p = json.loads(line)
            expected = reference(p, mats)
            if expected != p['output']:
                bad = next(i for i, pair in enumerate(zip(expected, p['output'])) if pair[0] != pair[1])
                raise ValueError(f'{path}: call {p["call_id"]}, index {bad}: expected {expected[bad]}, got {p["output"][bad]}')
            count += 1
            values += len(expected)
    if not count:
        raise ValueError('No payload samples: ' + str(path))
    return {'payloads': count, 'values': values, 'mismatches': 0}
