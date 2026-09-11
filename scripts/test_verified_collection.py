import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from run_verified_pilot import validate_input, validate_log
from verify_payloads import matrices, reference, rounded, verify

class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path('vtm_src') if Path('vtm_src').exists() else Path('vtm_ctc_corrected/vtm_src')
        cls.mats = matrices(root/'source/Lib/CommonLib/RomTr.cpp')

    def test_integer_matrices(self):
        self.assertEqual(self.mats['DCT2',4].tolist(), [[64,64,64,64],[83,36,-36,-83],[64,-64,-64,64],[36,-83,83,-36]])
        self.assertEqual(len(self.mats),14)

    def test_direct_4x4_constant(self):
        p = dict(w=4,h=4,bit_depth=10,max_log2_dynamic_range=15,direction='FWD',tr_h='DCT2',tr_v='DCT2',skip_w=0,skip_h=0,input=[1]*16)
        self.assertEqual(reference(p,self.mats),[32]+[0]*15)
        p.update(direction='INV',input=[32]+[0]*15)
        self.assertEqual(reference(p,self.mats),[1]*16)

    def test_negative_rounding(self):
        self.assertEqual(rounded(np.array([-5,-4,-3,-2,-1,0,1,2,3]),2).tolist(),[-1,-1,-1,0,0,0,0,1,1])

    def test_payload_corruption_rejected(self):
        p = dict(call_id=0,w=4,h=4,bit_depth=10,max_log2_dynamic_range=15,direction='FWD',tr_h='DCT2',tr_v='DCT2',skip_w=0,skip_h=0,input=[1]*16,output=[31]+[0]*15)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'payload.jsonl'
            path.write_text(json.dumps(p)+'\n')
            with self.assertRaises(ValueError): verify(path,self.mats)

    def test_real_input_rejections(self):
        spec={'width':4,'height':4,'input_bit_depth':8}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.yuv'
            for data in [b'',b'\x80'*24,b'\x00'*23]:
                p.write_bytes(data)
                with self.assertRaises(ValueError): validate_input(p,spec,1)
            p.write_bytes(bytes(range(24)))
            self.assertEqual(validate_input(p,spec,1)['source_frames'],1)
            p.write_bytes(b'\x80'*48)
            with self.assertRaises(ValueError): validate_input(p,{**spec,'input_bit_depth':10},1)

    def test_vtm_log_and_missing_frames(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'enc.log'
            p.write_text('POC    0 LId:  0 TId: 0 ( IDR_N_LP, I-SLICE, QP 22 ) 200 bits\n finished @ date\n')
            self.assertEqual(validate_log(p,1)['frames'],1)
            with self.assertRaises(ValueError): validate_log(p,2)
            p.write_text('Source image contains values outside the specified bit range!')
            with self.assertRaises(ValueError): validate_log(p,1)

if __name__=='__main__': unittest.main()
