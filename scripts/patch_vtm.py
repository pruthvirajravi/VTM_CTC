#!/usr/bin/env python3
"""
Python script to:
1. Safely remove -Werror / warnings-as-errors without breaking CMake multi-line syntax.
2. Inject thread-safe trace extraction hooks into VTM TrQuant.cpp.
"""

import os
import sys

def disable_all_warnings_and_errors(vtm_root):
    # 1. Patch CMakeLists.txt safely (only remove the string "warnings-as-errors")
    cmakelists_path = os.path.join(vtm_root, "CMakeLists.txt")
    if os.path.exists(cmakelists_path):
        with open(cmakelists_path, "r", encoding="utf-8") as f:
            c = f.read()
        c = c.replace("warnings-as-errors", "")
        with open(cmakelists_path, "w", encoding="utf-8") as f:
            f.write(c)
        print("Patched CMakeLists.txt to remove warnings-as-errors.")

    # 2. Patch BBuildEnv.cmake safely
    bbuildenv_path = os.path.join(vtm_root, "cmake", "CMakeBuild", "cmake", "modules", "BBuildEnv.cmake")
    if os.path.exists(bbuildenv_path):
        with open(bbuildenv_path, "r", encoding="utf-8") as f:
            b = f.read()
        b = b.replace('list( APPEND _warning_flags "-Werror" )', '# no werror')
        b = b.replace('"-Werror"', '""')
        b = b.replace('warnings-as-errors', '')
        with open(bbuildenv_path, "w", encoding="utf-8") as f:
            f.write(b)
        print("Patched BBuildEnv.cmake to neutralize -Werror.")

def patch_vtm_source(vtm_root):
    disable_all_warnings_and_errors(vtm_root)

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
  // Trace Logger Hook - Inverse
  {
    uint32_t poc = tu.cs->slice->getPOC();
    char sliceType = (tu.cs->slice->getSliceType() == I_SLICE) ? 'I' : ((tu.cs->slice->getSliceType() == P_SLICE) ? 'P' : 'B');
    uint32_t ctuAddr = (uint32_t)(tu.cu->lumaPos().x / tu.cs->pcv->maxCUWidth + (tu.cu->lumaPos().y / tu.cs->pcv->maxCUHeight) * tu.cs->pcv->widthInCtus);
    uint16_t tuX = (uint16_t)area.x;
    uint16_t tuY = (uint16_t)area.y;
    uint8_t tuW = (uint8_t)area.width;
    uint8_t tuH = (uint8_t)area.height;
    std::string compStr = (compID == COMPONENT_Y) ? "Y" : ((compID == COMPONENT_Cb) ? "Cb" : "Cr");
    std::string trHor = (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_DST7_DST7 || tu.mtsIdx[compID] == MTS_DST7_DCT8 ? "DST7" : "DCT8")));
    std::string trVer = (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_DST7_DST7 || tu.mtsIdx[compID] == MTS_DCT8_DST7 ? "DST7" : "DCT8")));
    std::string treeType = (tu.cu->treeType == TREE_D ? "DUAL_TREE_LUMA" : (tu.cu->treeType == TREE_C ? "DUAL_TREE_CHROMA" : "SINGLE_TREE"));
    std::string predMode = (tu.cu->predMode == MODE_INTRA ? "MODE_INTRA" : (tu.cu->predMode == MODE_INTER ? "MODE_INTER" : "MODE_IBC"));
    uint8_t bitDepth = (uint8_t)tu.cs->sps->getBitDepth(toChannelType(compID));
    uint8_t cbfVal = (uint8_t)tu.cbf[compID];
    VtmTraceLogger::getInstance().log(poc, sliceType, ctuAddr, tuX, tuY, tuW, tuH, tuW, tuH, compStr, trHor, trVer, "INV", "ENC_RECON", cbfVal, bitDepth, treeType, predMode);
  }
"""

    fwd_hook = """
  // Trace Logger Hook - Forward
  {
    uint32_t poc = cs.slice->getPOC();
    char sliceType = (cs.slice->getSliceType() == I_SLICE) ? 'I' : ((cs.slice->getSliceType() == P_SLICE) ? 'P' : 'B');
    uint32_t ctuAddr = (uint32_t)(tu.cu->lumaPos().x / cs.pcv->maxCUWidth + (tu.cu->lumaPos().y / cs.pcv->maxCUHeight) * cs.pcv->widthInCtus);
    uint16_t tuX = (uint16_t)rect.x;
    uint16_t tuY = (uint16_t)rect.y;
    uint8_t tuW = (uint8_t)rect.width;
    uint8_t tuH = (uint8_t)rect.height;
    std::string compStr = (compID == COMPONENT_Y) ? "Y" : ((compID == COMPONENT_Cb) ? "Cb" : "Cr");
    std::string trHor = (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_DST7_DST7 || tu.mtsIdx[compID] == MTS_DST7_DCT8 ? "DST7" : "DCT8")));
    std::string trVer = (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_DST7_DST7 || tu.mtsIdx[compID] == MTS_DCT8_DST7 ? "DST7" : "DCT8")));
    std::string treeType = (tu.cu->treeType == TREE_D ? "DUAL_TREE_LUMA" : (tu.cu->treeType == TREE_C ? "DUAL_TREE_CHROMA" : "SINGLE_TREE"));
    std::string predMode = (tu.cu->predMode == MODE_INTRA ? "MODE_INTRA" : (tu.cu->predMode == MODE_INTER ? "MODE_INTER" : "MODE_IBC"));
    uint8_t bitDepth = (uint8_t)sps.getBitDepth(toChannelType(compID));
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
            print("Injected inverse transform hook.")

        if "void TrQuant::transformNxN( TransformUnit& tu, const ComponentID& compID, const QpParam& cQP, TCoeff& uiAbsSum" in line or \
           "void TrQuant::transformNxN(TransformUnit &tu, const ComponentID &compID, const QpParam &cQP, TCoeff &uiAbsSum" in line:
            in_fwd = True
        elif in_fwd and "{" in line:
            new_lines.append(fwd_hook)
            in_fwd = False
            print("Injected forward transform hook.")

    with open(trquant_cpp_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print("VTM patch complete!")

if __name__ == "__main__":
    vtm_dir = sys.argv[1] if len(sys.argv) > 1 else "vtm_src"
    patch_vtm_source(vtm_dir)
