#ifndef VTM_VERIFIED_TRACE_H
#define VTM_VERIFIED_TRACE_H
#include "UnitTools.h"
#include "CodingStructure.h"
#include <cstdlib>
#include <fstream>
#include <map>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <cstdint>

// C++11 instrumentation for VTM; unrelated to the Verilog RTL.
// xT/xIT records are actual primary-transform calls, including encoder RDO
// trials. CABAC records are final coded TU observations, NOT executions.
class VerifiedTrace {
  std::ofstream calls, finals, payloads;
  std::mutex mutex;
  uint64_t callId = 0, finalId = 0, payloadCount = 0;
  std::map<std::string, unsigned> sampleCounts;
  bool enabled = false;
  VerifiedTrace() {
    const char* prefix = std::getenv("VTM_VERIFIED_TRACE");
    if (!prefix || !*prefix) return;
    enabled = true;
    calls.exceptions(std::ios::failbit | std::ios::badbit);
    finals.exceptions(std::ios::failbit | std::ios::badbit);
    payloads.exceptions(std::ios::failbit | std::ios::badbit);
    calls.open(std::string(prefix) + "_calls.csv", std::ios::trunc);
    finals.open(std::string(prefix) + "_final_tus.csv", std::ios::trunc);
    payloads.open(std::string(prefix) + "_payloads.jsonl", std::ios::trunc);
    calls << "call_id,poc,slice_type,comp,x,y,w,h,bit_depth,pred_mode,tree_type,channel_type,mts_idx,lfnst_idx,isp_mode,sbt_info,joint_cbcr,tu_depth,cu_qp,direction,stage,tr_h,tr_v,eff_w,eff_h,cbf,payload\n";
    finals << "final_id,poc,slice_type,comp,x,y,w,h,bit_depth,pred_mode,tree_type,channel_type,mts_idx,lfnst_idx,isp_mode,sbt_info,joint_cbcr,tu_depth,cu_qp,stage,cbf,quant_nonzero,sub_tu\n";
  }
  static const char* type(int t) { return t == DCT2 ? "DCT2" : t == DST7 ? "DST7" : t == DCT8 ? "DCT8" : "UNKNOWN"; }
  static void common(std::ostream& out, const TransformUnit& tu, ComponentID c) {
    const auto& a = tu.blocks[c];
    const auto& cu = *tu.cu;
    const auto& cs = *tu.cs;
    const char slice = cs.slice->getSliceType() == I_SLICE ? 'I' : cs.slice->getSliceType() == P_SLICE ? 'P' : 'B';
    out << cs.slice->getPOC() << ',' << slice << ',' << int(c) << ','
        << a.x << ',' << a.y << ',' << a.width << ',' << a.height << ','
        << cs.sps->getBitDepth(toChannelType(c)) << ',' << int(cu.predMode) << ','
        << int(cu.treeType) << ',' << int(tu.chType) << ',' << int(tu.mtsIdx[c]) << ','
        << int(cu.lfnstIdx) << ',' << int(cu.ispMode) << ',' << int(cu.sbtInfo) << ','
        << int(tu.jointCbCr) << ',' << int(tu.depth) << ',' << int(cu.qp);
  }
  template<class T> static void array(std::ostream& out, const T* p, int stride, int w, int h) {
    out << '[';
    for (int y=0; y<h; ++y) for (int x=0; x<w; ++x) {
      if (y || x) out << ',';
      out << int64_t(p[y*stride+x]);
    }
    out << ']';
  }
public:
  static VerifiedTrace& instance() { static VerifiedTrace logger; return logger; }
  template<class A, class B> void call(const TransformUnit& tu, ComponentID c, const char* dir,
      int th, int tv, int sw, int sh, const A* input, int is, const B* output, int os) {
    if (!enabled) return;
    std::lock_guard<std::mutex> lock(mutex);
    const auto& a = tu.blocks[c];
    std::ostringstream key;
    key << dir << ':' << a.width << ':' << a.height << ':' << th << ':' << tv << ':' << sw << ':' << sh;
    const bool sample = sampleCounts[key.str()]++ < 2 && payloadCount < 512;
    const uint64_t id = callId++;
    calls << id << ',';
    common(calls, tu, c);
    calls << ',' << dir << ',' << (dir[0]=='F' ? "PRIMARY_PRE_LFNST_PRE_QUANT" : "PRIMARY_POST_DEQUANT_POST_INV_LFNST")
          << ',' << type(th) << ',' << type(tv) << ',' << a.width-sw << ',' << a.height-sh
          << ",NA," << int(sample) << '\n';
    if (sample) {
      ++payloadCount;
      payloads << "{\"call_id\":" << id << ",\"w\":" << a.width << ",\"h\":" << a.height
               << ",\"bit_depth\":" << tu.cs->sps->getBitDepth(toChannelType(c))
               << ",\"max_log2_dynamic_range\":" << tu.cs->sps->getMaxLog2TrDynamicRange(toChannelType(c))
               << ",\"direction\":\"" << dir << "\",\"tr_h\":\"" << type(th) << "\",\"tr_v\":\"" << type(tv)
               << "\",\"skip_w\":" << sw << ",\"skip_h\":" << sh << ",\"input\":";
      array(payloads, input, is, a.width, a.height);
      payloads << ",\"output\":";
      array(payloads, output, os, a.width, a.height);
      payloads << "}\n";
    }
  }
  void finalTu(const TransformUnit& tu, ChannelType channel, int subTu) {
    if (!enabled) return;
    std::lock_guard<std::mutex> lock(mutex);
    for (int i=0; i<MAX_NUM_COMPONENT; ++i) {
      const ComponentID c = ComponentID(i);
      if (!tu.blocks[c].valid()) continue;
      if (tu.cu->isSepTree() && toChannelType(c) != channel) continue;
      const auto coeff = tu.getCoeffs(c);
      unsigned nz = 0;
      for (unsigned y=0; y<coeff.height; ++y) for (unsigned x=0; x<coeff.width; ++x) nz += coeff.at(x,y) != 0;
      finals << finalId++ << ',';
      common(finals, tu, c);
      finals << ",FINAL_CABAC_TU," << int(TU::getCbfAtDepth(tu,c,tu.depth)) << ',' << nz << ',' << subTu << '\n';
    }
  }
};
#endif
