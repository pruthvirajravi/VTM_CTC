#!/usr/bin/env python3
"""
Python script to:
1. Safely remove -Werror / warnings-as-errors from VTM CMake and build scripts.
2. Inject 100% self-contained, thread-safe trace extraction hooks into VTM TrQuant.cpp.
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

def patch_trquant_cpp(vtm_root):
    trquant_cpp_path = os.path.join(vtm_root, "source", "Lib", "CommonLib", "TrQuant.cpp")
    if not os.path.exists(trquant_cpp_path):
        print(f"Error: {trquant_cpp_path} does not exist.")
        sys.exit(1)

    with open(trquant_cpp_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    if any("TraceLogger.h" in line for line in lines):
        print("TrQuant.cpp is already patched.")
        return

    new_lines = ['#include "TraceLogger.h"\n']

    inv_hook = """
  // Trace Logger Hook - Inverse (Self-Contained)
  {
    const CompArea &area_hook = tu.blocks[compID];
    const CodingStructure &cs_hook = *tu.cs;
    const SPS &sps_hook = *cs_hook.sps;
    uint32_t poc = cs_hook.slice->getPOC();
    char sliceType = (cs_hook.slice->getSliceType() == I_SLICE) ? 'I' : ((cs_hook.slice->getSliceType() == P_SLICE) ? 'P' : 'B');
    uint32_t ctuAddr = (uint32_t)(tu.cu->lumaPos().x / cs_hook.pcv->maxCUWidth + (tu.cu->lumaPos().y / cs_hook.pcv->maxCUHeight) * cs_hook.pcv->widthInCtus);
    uint16_t tuX = (uint16_t)area_hook.x;
    uint16_t tuY = (uint16_t)area_hook.y;
    uint8_t tuW = (uint8_t)area_hook.width;
    uint8_t tuH = (uint8_t)area_hook.height;
    std::string compStr = (compID == COMPONENT_Y) ? "Y" : ((compID == COMPONENT_Cb) ? "Cb" : "Cr");
    std::string trHor = (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_DST7_DST7 || tu.mtsIdx[compID] == MTS_DST7_DCT8 ? "DST7" : "DCT8")));
    std::string trVer = (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_DST7_DST7 || tu.mtsIdx[compID] == MTS_DCT8_DST7 ? "DST7" : "DCT8")));
    std::string treeType = (tu.cu->treeType == TREE_D ? "DUAL_TREE_LUMA" : (tu.cu->treeType == TREE_C ? "DUAL_TREE_CHROMA" : "SINGLE_TREE"));
    std::string predMode = (tu.cu->predMode == MODE_INTRA ? "MODE_INTRA" : (tu.cu->predMode == MODE_INTER ? "MODE_INTER" : "MODE_IBC"));
    uint8_t bitDepth = (uint8_t)sps_hook.getBitDepth(toChannelType(compID));
    uint8_t cbfVal = (uint8_t)tu.cbf[compID];
    VtmTraceLogger::getInstance().log(poc, sliceType, ctuAddr, tuX, tuY, tuW, tuH, tuW, tuH, compStr, trHor, trVer, "INV", "ENC_RECON", cbfVal, bitDepth, treeType, predMode);
  }
"""

    fwd_hook = """
  // Trace Logger Hook - Forward (Self-Contained)
  {
    const CompArea &area_hook = tu.blocks[compID];
    const CodingStructure &cs_hook = *tu.cs;
    const SPS &sps_hook = *cs_hook.sps;
    uint32_t poc = cs_hook.slice->getPOC();
    char sliceType = (cs_hook.slice->getSliceType() == I_SLICE) ? 'I' : ((cs_hook.slice->getSliceType() == P_SLICE) ? 'P' : 'B');
    uint32_t ctuAddr = (uint32_t)(tu.cu->lumaPos().x / cs_hook.pcv->maxCUWidth + (tu.cu->lumaPos().y / cs_hook.pcv->maxCUHeight) * cs_hook.pcv->widthInCtus);
    uint16_t tuX = (uint16_t)area_hook.x;
    uint16_t tuY = (uint16_t)area_hook.y;
    uint8_t tuW = (uint8_t)area_hook.width;
    uint8_t tuH = (uint8_t)area_hook.height;
    std::string compStr = (compID == COMPONENT_Y) ? "Y" : ((compID == COMPONENT_Cb) ? "Cb" : "Cr");
    std::string trHor = (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_DST7_DST7 || tu.mtsIdx[compID] == MTS_DST7_DCT8 ? "DST7" : "DCT8")));
    std::string trVer = (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_DST7_DST7 || tu.mtsIdx[compID] == MTS_DCT8_DST7 ? "DST7" : "DCT8")));
    std::string treeType = (tu.cu->treeType == TREE_D ? "DUAL_TREE_LUMA" : (tu.cu->treeType == TREE_C ? "DUAL_TREE_CHROMA" : "SINGLE_TREE"));
    std::string predMode = (tu.cu->predMode == MODE_INTRA ? "MODE_INTRA" : (tu.cu->predMode == MODE_INTER ? "MODE_INTER" : "MODE_IBC"));
    uint8_t bitDepth = (uint8_t)sps_hook.getBitDepth(toChannelType(compID));
    uint8_t cbfVal = (uint8_t)tu.cbf[compID];
    VtmTraceLogger::getInstance().log(poc, sliceType, ctuAddr, tuX, tuY, tuW, tuH, tuW, tuH, compStr, trHor, trVer, "FWD", "ENC_FWD", cbfVal, bitDepth, treeType, predMode);
  }
"""

    in_inv = False
    in_fwd = False

    for line in lines:
        new_lines.append(line)
        if "void TrQuant::invTransformNxN(" in line:
            in_inv = True
        elif in_inv and "{" in line:
            new_lines.append(inv_hook)
            in_inv = False
            print("Injected self-contained inverse transform hook.")

        if "void TrQuant::transformNxN( TransformUnit& tu, const ComponentID& compID, const QpParam& cQP, TCoeff& uiAbsSum" in line or \
           "void TrQuant::transformNxN(TransformUnit &tu, const ComponentID &compID, const QpParam &cQP, TCoeff &uiAbsSum" in line:
            in_fwd = True
        elif in_fwd and "{" in line:
            new_lines.append(fwd_hook)
            in_fwd = False
            print("Injected self-contained forward transform hook.")

    with open(trquant_cpp_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print("TrQuant.cpp successfully patched with self-contained hooks.")

def patch_vtm_source(vtm_root):
    disable_all_warnings_and_errors(vtm_root)
    patch_trquant_cpp(vtm_root)

if __name__ == "__main__":
    vtm_dir = sys.argv[1] if len(sys.argv) > 1 else "vtm_src"
    patch_vtm_source(vtm_dir)
