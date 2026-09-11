#!/usr/bin/env python3
"""Bounded genuine-source pilot. Never creates substitute video or empty traces."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import numpy as np
from verify_payloads import matrices, verify

SOURCE = {'sequence': 'BasketballPass', 'filename': 'D4_BasketballPass_416x240_50.yuv',
          'drive_id': '17Z4zKzsrPT5dIsTUqcjjYxbUClWf7e8J', 'width': 416, 'height': 240,
          'fps': 50, 'input_bit_depth': 8, 'format': 'planar_yuv420',
          'provenance': 'User-provided Drive folder; no authoritative publisher checksum supplied'}
CONFIGS = {'AI': 'encoder_intra_vtm.cfg', 'LDP': 'encoder_lowdelay_P_vtm.cfg',
           'LDB': 'encoder_lowdelay_vtm.cfg', 'RA': 'encoder_randomaccess_vtm.cfg'}
CASES = [('AI',22,2), ('AI',37,2), ('LDP',32,8), ('LDB',32,8), ('RA',32,8)]

def sha(path):
    with open(path,'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def validate_input(path, spec, frames):
    w,h,bd = spec['width'], spec['height'], spec['input_bit_depth']
    if w%2 or h%2 or bd not in (8,10):
        raise ValueError('Unsupported input format')
    frame_bytes = w*h*3//2*(1 if bd==8 else 2)
    size = Path(path).stat().st_size
    if not size or size % frame_bytes or size < frames*frame_bytes:
        raise ValueError('Input size is not complete YUV420 frames, or too short')
    sample = np.fromfile(path, dtype=np.uint8 if bd==8 else '<u2', count=w*h*3//2*frames)
    if int(sample.max()) >= 1<<bd:
        raise ValueError('Input values exceed bit depth')
    ys = sample.reshape(frames,-1)[:,:w*h]
    std = ys.std(axis=1).tolist()
    if max(std) == 0:
        raise ValueError('Pilot source contains only flat luma frames')
    return {**spec, 'size_bytes': size, 'source_frames': size//frame_bytes,
            'sha256': sha(path), 'checked_frames': frames,
            'sample_min': int(sample.min()), 'sample_max': int(sample.max()),
            'luma_stddev': std, 'distinct_checked_frames': len({x.tobytes() for x in ys})}

def execute(cmd, log, env=None):
    started = time.monotonic()
    with open(log,'w') as f:
        p = subprocess.run([str(x) for x in cmd], stdout=f, stderr=subprocess.STDOUT, env=env)
    if p.returncode:
        print(Path(log).read_text(errors='replace')[-8000:])
        raise RuntimeError(f'Command failed ({p.returncode}): {log}')
    return time.monotonic()-started

def validate_log(path, frames):
    text = Path(path).read_text(errors='strict')
    pocs = re.findall(r'^POC\s+(\d+)\s+.*?\b([IPB])-SLICE', text, re.M)
    if len(pocs) != frames or {int(p[0]) for p in pocs} != set(range(frames)):
        raise ValueError(f'Wrong encoded frame count/POCs in {path}: {len(pocs)}')
    if 'finished' not in text.lower():
        raise ValueError('Encoder completion marker missing')
    return {'frames': len(pocs), 'slice_types': dict(Counter(p[1] for p in pocs)),
            'perfect_psnr_mentions': text.count('999.9900')}

def audit_calls(prefix, frames, mats, require_finals=True):
    counts, sizes, types, pocs, predicted = Counter(), Counter(), Counter(), set(), Counter()
    samples = set()
    count = 0
    with open(str(prefix)+'_calls.csv', newline='') as f:
        for count,row in enumerate(csv.DictReader(f),1):
            if int(row['call_id']) != count-1 or row['cbf'] != 'NA':
                raise ValueError('Invalid execution identity or premature CBF')
            w,h,ew,eh = (int(row[k]) for k in ['w','h','eff_w','eff_h'])
            if not (0<ew<=w<=64 and 0<eh<=h<=64):
                raise ValueError('Invalid transform dimensions')
            if row['tr_h'] not in ('DCT2','DST7','DCT8') or row['tr_v'] not in ('DCT2','DST7','DCT8'):
                raise ValueError('Unknown actual transform type')
            counts[row['direction']] += 1
            sizes[f'{w}x{h}'] += 1
            types[row['tr_h']+'/'+row['tr_v']] += 1
            predicted[row['pred_mode']] += 1
            pocs.add(int(row['poc']))
            if row['payload']=='1': samples.add(int(row['call_id']))
    if not count or not pocs.issubset(set(range(frames))):
        raise ValueError('Empty trace or out-of-range POC')
    with open(str(prefix)+'_payloads.jsonl') as f:
        payload_rows = [json.loads(line) for line in f]
    payload_ids = [p['call_id'] for p in payload_rows]
    if set(payload_ids)!=samples or len(payload_ids)!=len(samples):
        raise ValueError('Payload references are missing or duplicated')
    payload_result = verify(str(prefix)+'_payloads.jsonl', mats)
    finals = 0
    cbfs = Counter()
    with open(str(prefix)+'_final_tus.csv', newline='') as f:
        for finals,row in enumerate(csv.DictReader(f),1):
            if int(row['final_id'])!=finals-1 or row['stage']!='FINAL_CABAC_TU':
                raise ValueError('Invalid final-TU identity/stage')
            if not 0<=int(row['quant_nonzero'])<=int(row['w'])*int(row['h']):
                raise ValueError('Impossible final nonzero count')
            cbfs[row['cbf']] += 1
    if require_finals and not finals:
        raise ValueError('No final TU observations')
    return {'actual_primary_calls': count, 'directions': dict(counts), 'sizes': dict(sizes),
            'types': dict(types), 'pred_mode_codes': dict(predicted), 'pocs_with_calls': sorted(pocs),
            'final_tu_observations': finals, 'final_cbf': dict(cbfs), 'matrix_check': payload_result}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', required=True)
    ap.add_argument('--encoder', required=True)
    ap.add_argument('--decoder', required=True)
    ap.add_argument('--vtm', required=True)
    ap.add_argument('--source', default='sequences/D4_BasketballPass_416x240_50.yuv')
    ap.add_argument('--output', default='verified_results')
    args = ap.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = Path(args.source).resolve()
    source.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        import gdown
        result = gdown.download(id=SOURCE['drive_id'], output=str(source), quiet=False, use_cookies=False)
        if not result:
            raise RuntimeError('Authentic source download failed; no substitute is allowed')
    manifest = {'schema': 2, 'purpose': 'pipeline_validation_pilot_not_full_CTC',
                'source': validate_input(source, SOURCE, 8),
                'vtm_commit': '3711eda2cff4777b28b3338d6bc4783424fc6d30',
                'workflow_commit': os.getenv('GITHUB_SHA'), 'github_run_id': os.getenv('GITHUB_RUN_ID'),
                'internal_bit_depth': 10, 'output_bit_depth': 8,
                'cases': [], 'validation_status': 'RUNNING'}
    manifest_path = output/'manifest.json'
    manifest_path.write_text(json.dumps(manifest,indent=2))
    vtm = Path(args.vtm).resolve()
    mats = matrices(vtm/'source/Lib/CommonLib/RomTr.cpp')
    shutil.copyfile(vtm/'trace_patch_manifest.json', output/'trace_patch_manifest.json')
    manifest['binary_sha256'] = {n:sha(p) for n,p in [('baseline',args.baseline),('encoder',args.encoder),('decoder',args.decoder)]}
    # Human-reviewable real source frame, no conversion or renamed substitute.
    first = np.fromfile(source, dtype=np.uint8, count=416*240)
    (output/'source_first_frame.pgm').write_bytes(b'P5\n416 240\n255\n'+first.tobytes())
    for mode,qp,frames in CASES:
        run = output/f'BasketballPass_{mode}_QP{qp}'
        run.mkdir()
        cfg = vtm/'cfg'/CONFIGS[mode]
        shutil.copyfile(cfg,run/cfg.name)
        common = ['-c', cfg, '-c', vtm/'cfg/per-sequence/BasketballPass.cfg', '-i',source,
                  '-f',str(frames), '-q',str(qp), '--InputBitDepth=8','--InternalBitDepth=10',
                  '--OutputBitDepth=8','--OutputBitDepthC=8']
        shutil.copyfile(vtm/'cfg/per-sequence/BasketballPass.cfg',run/'sequence.cfg')
        base_cmd = [args.baseline]+common+['-b',run/'baseline.bin','-o',run/'baseline.yuv']
        enc_cmd = [args.encoder]+common+['-b',run/'traced.bin','-o',run/'encoder_recon.yuv']
        env = os.environ.copy()
        env.pop('VTM_VERIFIED_TRACE',None)
        base_seconds = execute(base_cmd,run/'baseline.log',env)
        env['VTM_VERIFIED_TRACE'] = str(run/'encoder')
        enc_seconds = execute(enc_cmd,run/'encoder.log',env)
        log_result = validate_log(run/'encoder.log',frames)
        validate_log(run/'baseline.log',frames)
        if sha(run/'baseline.bin') != sha(run/'traced.bin') or sha(run/'baseline.yuv') != sha(run/'encoder_recon.yuv'):
            raise ValueError('Instrumentation changes bitstream or reconstructed samples')
        env['VTM_VERIFIED_TRACE'] = str(run/'decoder')
        dec_cmd = [args.decoder,'-b',run/'traced.bin','-o',run/'decoder_recon.yuv','--OutputBitDepth=8','--OutputBitDepthC=8']
        execute(dec_cmd,run/'decoder.log',env)
        expected_bytes = 416*240*3//2*frames
        if (run/'encoder_recon.yuv').stat().st_size != expected_bytes or sha(run/'decoder_recon.yuv')!=sha(run/'encoder_recon.yuv'):
            raise ValueError('Decoder reconstruction mismatch or incomplete output')
        item = {'id':run.name,'mode':mode,'qp':qp,'frames':frames,'commands': [[str(x) for x in c] for c in [base_cmd,enc_cmd,dec_cmd]],
                'config_sha256':sha(cfg),'log':log_result,'baseline_seconds':base_seconds,'traced_seconds':enc_seconds,
                'bitstream_match':True,'reconstruction_match':True,
                'encoder':audit_calls(run/'encoder',frames,mats),
                'decoder':audit_calls(run/'decoder',frames,mats,False)}
        (run/'validation.json').write_text(json.dumps(item,indent=2))
        manifest['cases'].append(item)
        manifest_path.write_text(json.dumps(manifest,indent=2))
        print(json.dumps(item),flush=True)
        # Preserve compressed full metadata, sampled payloads, logs and streams.
        for path in list(run.glob('*.csv')) + list(run.glob('*.jsonl')):
            with open(path,'rb') as src, gzip.open(str(path)+'.gz','wb') as dst:
                shutil.copyfileobj(src,dst)
            path.unlink()
    manifest['validation_status']='PASS'
    manifest_path.write_text(json.dumps(manifest,indent=2))
    print('VERIFIED PILOT PASS',flush=True)

if __name__=='__main__':
    main()
