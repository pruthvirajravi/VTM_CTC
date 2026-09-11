# Verified VTM collection

The old matrix workflow silently generated flat frames when an expected file
was absent. The old heavy workflow generated synthetic patterns under named
CTC sequence filenames. Encoder errors were ignored and missing traces replaced
with CSV headers. Those artifacts cannot establish genuine CTC performance.

The replacement workflow is a bounded **pilot**, manually dispatched. It uses
the actual BasketballPass file from the supplied Drive folder, pins official
VTM-18.0 to commit 3711eda2cff4777b28b3338d6bc4783424fc6d30, and records source,
configuration, patch and executable hashes. Source authenticity beyond the
user-provided provenance is not independently certified by an upstream checksum.

AI uses QP22/37 and two frames each. LDP, LDB and RA use QP32 and eight frames
each. These shortened tests validate the pipeline; they are not full CTC runs.
Input is 8-bit planar YUV420; codec internal precision is 10 bits; reconstruction
files are explicitly 8-bit. No substitute video or header-only success is allowed.

## Trace meanings

- `encoder_calls.csv`: actual xT/xIT primary transform invocations, including
  RDO trials. Types and effective dimensions come directly from VTM. CBF is NA
  because a current final quantization result cannot be inferred at this point.
- `encoder_final_tus.csv`: final bitstream writer TU/component observations,
  with true stored CBF and quantized nonzero counts. Raw VTM tree, channel, MTS,
  prediction, ISP, SBT and LFNST codes are preserved. These rows do not claim
  actual forward/inverse execution; root-CBF-zero CUs that never enter
  CABACWriter::transform_unit are outside this table.
- `decoder_calls.csv`: actual primary inverse transforms from decoding the
  final bitstream. This excludes encoder trials and is separately identified.
- `*_payloads.jsonl`: full row-major inputs/outputs for the first two calls
  of each direction/size/type/effective-size combination, at most 512 per
  process. All call metadata is retained, even when payload is not sampled.

Transform skip, quantization, LFNST itself, prediction and non-transform work
are not primary transform calls and are not included in primary-call totals.
Do not equate these totals with total codec work or final forward jobs. A TU's
MTS syntax alone is insufficient to derive all implicit transform types.

## Gates

The job fails for download/format/range errors, encoder or decoder errors,
missing frames, missing traces, inconsistent IDs/payloads, bitstream or
reconstruction changes due to instrumentation, or dense-matrix mismatches.
Dense-matrix checks independently evaluate the arithmetic using official
integer matrices, shifts, zeroing and clipping, rather than the fast kernel.
They validate sampled complete primary transforms, not the hardware RTL.

All-zero CBF, repeated PSNR and absent sizes are reported as observations;
no artificial minimum quota of 4x4 or other transform types is imposed.
The pilot additionally rejects wholly flat luma input because it is intended
to use the named real-video file. Hashes alone do not certify provenance.

After the pilot passes, review frame images and distributions, add authoritative
checksums where available, and expand the manifest to actual accessible
sequences, bit depths, configurations, QPs and full frame ranges. The supplied
folder does not contain verified originals for every formerly requested heavy
sequence. The heavy workflow is intentionally blocked until those are supplied;
the available Tango Y4M must not be silently relabeled Tango2 raw YUV.

This work changes only the collection pipeline. Core-A/Core-B RTL is untouched.
