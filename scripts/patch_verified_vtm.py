#!/usr/bin/env python3
"""Fail-closed, exact-source patch for official VTM-18.0 (3711eda2)."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

PIN = '3711eda2cff4777b28b3338d6bc4783424fc6d30'

def patch(root):
    root = Path(root).resolve()
    git = ['git', '-c', 'safe.directory=' + root.as_posix(), '-C', str(root)]
    sha = subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True).strip()
    if sha != PIN:
        raise ValueError('Unsupported VTM revision: ' + sha)
    paths = ['source/Lib/CommonLib/TrQuant.cpp', 'source/Lib/EncoderLib/CABACWriter.cpp']
    texts = {}
    manifest = {'vtm_commit': sha, 'files': {}}
    for name in paths:
        p = root / name
        clean = subprocess.check_output(git + ['show', 'HEAD:' + name])
        original = p.read_bytes()
        if original.replace(b'\r\n', b'\n') != clean.replace(b'\r\n', b'\n'):
            raise ValueError('Source already modified: ' + name)
        texts[name] = original.decode().replace('\r\n', '\n')
        manifest['files'][name] = {'before_sha256': hashlib.sha256(original).hexdigest()}
    tq = texts[paths[0]]
    for signature, call in [
        ('void TrQuant::xT(', '\n  VerifiedTrace::instance().call(tu, compID, "FWD", trTypeHor, trTypeVer, skipWidth, skipHeight, resi.buf, resi.stride, dstCoeff.buf, dstCoeff.stride);\n'),
        ('void TrQuant::xIT(', '\n  VerifiedTrace::instance().call(tu, compID, "INV", trTypeHor, trTypeVer, skipWidth, skipHeight, pCoeff.buf, pCoeff.stride, pResidual.buf, pResidual.stride);\n')]:
        # These source functions have a column-zero closing brace and no nested
        # column-zero braces; reject any source drift rather than guessing.
        if tq.count(signature) != 1:
            raise ValueError('Missing/duplicate transform anchor')
        start = tq.index(signature)
        end = tq.index('\n}\n', start)
        tq = tq[:end] + call + tq[end:]
    anchor = '#include "TrQuant.h"'
    if tq.count(anchor) != 1:
        raise ValueError('Missing include anchor')
    tq = tq.replace(anchor, anchor + '\n#include "VerifiedTrace.h"')
    texts[paths[0]] = tq
    cabac = texts[paths[1]]
    sig = 'void CABACWriter::transform_unit( const TransformUnit& tu, CUCtx& cuCtx, Partitioner& partitioner, const int subTuCounter)\n{'
    if cabac.count(sig) != 1:
        raise ValueError('Missing CABAC anchor')
    cabac = cabac.replace(sig, sig + '\n  if (isEncoding() && m_Bitstream != nullptr)\n    VerifiedTrace::instance().finalTu(tu, partitioner.chType, subTuCounter);')
    anchor = '#include "CABACWriter.h"'
    if cabac.count(anchor) != 1:
        raise ValueError('Missing CABAC include')
    texts[paths[1]] = cabac.replace(anchor, anchor + '\n#include "CommonLib/VerifiedTrace.h"')
    for name, content in texts.items():
        (root / name).write_text(content, encoding='utf-8', newline='\n')
        manifest['files'][name]['after_sha256'] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    header = Path(__file__).with_name('VerifiedTrace.h')
    shutil.copyfile(header, root / 'source/Lib/CommonLib/VerifiedTrace.h')
    manifest['logger_sha256'] = hashlib.sha256(header.read_bytes()).hexdigest()
    (root / 'trace_patch_manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    patch(sys.argv[1])
