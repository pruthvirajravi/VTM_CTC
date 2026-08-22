#!/usr/bin/env python3
"""
Python script to:
1. Safely remove -Werror / warnings-as-errors from VTM build scripts.
2. Inject Post-RDO final transform extraction hooks into VTM CABACWriter.cpp.
"""

import os
import sys

def disable_all_warnings_and_errors(vtm_root):
    cmakelists_path = os.path.join(vtm_root, "CMakeLists.txt")
    if os.path.exists(cmakelists_path):
        with open(cmakelists_path, "r", encoding="utf-8") as f:
            c = f.read()
        c = c.replace("warnings-as-errors", "")
        with open(cmakelists_path, "w", encoding="utf-8") as f:
            f.write(c)

    bbuildenv_path = os.path.join(vtm_root, "cmake", "CMakeBuild", "cmake", "modules", "BBuildEnv.cmake")
    if os.path.exists(bbuildenv_path):
        with open(bbuildenv_path, "r", encoding="utf-8") as f:
            b = f.read()
        b = b.replace('list( APPEND _warning_flags "-Werror" )', '# no werror')
        b = b.replace('"-Werror"', '""')
        b = b.replace('warnings-as-errors', '')
        with open(bbuildenv_path, "w", encoding="utf-8") as f:
            f.write(b)

def patch_cabac_writer(vtm_root):
    cabac_cpp_path = os.path.join(vtm_root, "source", "Lib", "EncoderLib", "CABACWriter.cpp")
    if not os.path.exists(cabac_cpp_path):
        print(f"Error: {cabac_cpp_path} does not exist.")
        sys.exit(1)

    with open(cabac_cpp_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if "TraceLogger.h" in content:
        print("CABACWriter.cpp is already patched.")
        return

    # Add header include
    content = '#include "TraceLogger.h"\n' + content

    target_signature = "void CABACWriter::transform_unit( const TransformUnit& tu, CUCtx& cuCtx, Partitioner& partitioner, const int subTuCounter)"
    if target_signature not in content:
        print(f"Error: Could not find {target_signature} in CABACWriter.cpp")
        sys.exit(1)

    hook_code = """
  // =========================================================================
  // POST-RDO FINAL WINNING TRANSFORM LOGGING HOOK (1-to-1 Hardware Stream)
  // =========================================================================
  {
    uint32_t poc = cs.slice->getPOC();
    char sliceType = (cs.slice->getSliceType() == I_SLICE) ? 'I' : ((cs.slice->getSliceType() == P_SLICE) ? 'P' : 'B');
    uint32_t ctuAddr = (uint32_t)(cu.lumaPos().x / cs.pcv->maxCUWidth + (cu.lumaPos().y / cs.pcv->maxCUHeight) * cs.pcv->widthInCtus);
    std::string treeType = (cu.treeType == TREE_D ? "DUAL_TREE_LUMA" : (cu.treeType == TREE_C ? "DUAL_TREE_CHROMA" : "SINGLE_TREE"));
    std::string predMode = (cu.predMode == MODE_INTRA ? "MODE_INTRA" : (cu.predMode == MODE_INTER ? "MODE_INTER" : "MODE_IBC"));

    int maxComp = lumaOnly ? 1 : 3;
    for (int comp = 0; comp < maxComp; comp++)
    {
      ComponentID compID = (ComponentID)comp;
      if (!tu.blocks[compID].valid()) continue;
      
      const CompArea &area = tu.blocks[compID];
      uint16_t tuX = (uint16_t)area.x;
      uint16_t tuY = (uint16_t)area.y;
      uint8_t tuW = (uint8_t)area.width;
      uint8_t tuH = (uint8_t)area.height;
      uint8_t bitDepth = (uint8_t)cs.sps->getBitDepth(toChannelType(compID));
      uint8_t cbfVal = (uint8_t)(cbf[compID] ? 1 : 0);
      std::string compStr = (compID == COMPONENT_Y) ? "Y" : ((compID == COMPONENT_Cb) ? "Cb" : "Cr");
      
      std::string trHor = (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_DST7_DST7 || tu.mtsIdx[compID] == MTS_DST7_DCT8 ? "DST7" : "DCT8")));
      std::string trVer = (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_DST7_DST7 || tu.mtsIdx[compID] == MTS_DCT8_DST7 ? "DST7" : "DCT8")));
      
      // Calculate Effective Dimensions applying VVC High-Frequency Zeroing Rules
      uint8_t trEffW = tuW;
      uint8_t trEffH = tuH;
      if (trHor == "DCT2") trEffW = std::min((uint8_t)tuW, (uint8_t)32);
      else if (trHor == "DST7" || trHor == "DCT8") trEffW = std::min((uint8_t)tuW, (uint8_t)16);
      
      if (trVer == "DCT2") trEffH = std::min((uint8_t)tuH, (uint8_t)32);
      else if (trVer == "DST7" || trVer == "DCT8") trEffH = std::min((uint8_t)tuH, (uint8_t)16);

      // 1. Log Forward Transform
      VtmTraceLogger::getInstance().log(poc, sliceType, ctuAddr, tuX, tuY, tuW, tuH, trEffW, trEffH, compStr, trHor, trVer, "FWD", "ENC_FWD", cbfVal, bitDepth, treeType, predMode);
      
      // 2. Log Inverse Transform for Reconstruction (if CBF == 1)
      if (cbfVal == 1) {
        VtmTraceLogger::getInstance().log(poc, sliceType, ctuAddr, tuX, tuY, tuW, tuH, trEffW, trEffH, compStr, trHor, trVer, "INV", "ENC_RECON", cbfVal, bitDepth, treeType, predMode);
      }
    }
  }
"""

    # Inject at end of CABACWriter::transform_unit before DTRACE_COND
    split_target = "DTRACE_COND( ( isEncoding() ), g_trace_ctx, D_DQP"
    pos = content.find(target_signature)
    pos_dtrace = content.find(split_target, pos)
    if pos_dtrace != -1:
        content = content[:pos_dtrace] + hook_code + "\n  " + content[pos_dtrace:]
        print("Successfully injected post-RDO logging hook into CABACWriter::transform_unit.")
    else:
        # Fallback to function end
        print("Notice: Injecting before closing brace.")
        brace_pos = content.find("void CABACWriter::cu_qp_delta", pos)
        if brace_pos != -1:
            last_brace = content.rfind("}", pos, brace_pos)
            content = content[:last_brace] + hook_code + "\n" + content[last_brace:]

    with open(cabac_cpp_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("CABACWriter.cpp patched successfully.")

def patch_vtm_source(vtm_root):
    disable_all_warnings_and_errors(vtm_root)
    patch_cabac_writer(vtm_root)

if __name__ == "__main__":
    vtm_dir = sys.argv[1] if len(sys.argv) > 1 else "vtm_src"
    patch_vtm_source(vtm_dir)
