#!/usr/bin/env python3
"""
Python script to automatically inject trace logging hooks into VTM source code.
Applies cleanly to VTM-16.0 / VTM-18.0 / VTM-20.0+ TrQuant.cpp and TrQuant.h.
"""

import os
import sys

def patch_vtm_source(vtm_root):
    trquant_cpp_path = os.path.join(vtm_root, "source", "Lib", "CommonLib", "TrQuant.cpp")
    trquant_h_path = os.path.join(vtm_root, "source", "Lib", "CommonLib", "TrQuant.h")
    
    if not os.path.exists(trquant_cpp_path):
        print(f"Error: {trquant_cpp_path} does not exist.")
        sys.exit(1)

    print(f"Injecting TraceLogger into: {trquant_cpp_path}")
    
    with open(trquant_cpp_path, "r", encoding="utf-8", errors="ignore") as f:
        cpp_content = f.read()

    # Check if already patched
    if "TraceLogger.h" in cpp_content:
        print("TrQuant.cpp is already patched.")
        return

    # Add include at top of TrQuant.cpp
    include_hook = '#include "TraceLogger.h"\n#include "UnitTools.h"\n'
    cpp_content = include_hook + cpp_content

    # Inject logging logic in transformNxN (Forward Transform)
    forward_target = "void TrQuant::transformNxN("
    forward_patch = """
void TrQuant::transformNxN(TransformUnit &tu, const ComponentID &compID, const QpParam &cQP, TrMode &trMode, const bool &loadTr)
{
  // Trace Extraction Hook - Forward
  {
    uint32_t poc = tu.cu->slice->getPOC();
    char sliceType = (tu.cu->slice->getSliceType() == I_SLICE) ? 'I' : ((tu.cu->slice->getSliceType() == P_SLICE) ? 'P' : 'B');
    uint32_t ctuAddr = tu.cu->slice->getPPS()->getRealCtuAddr(tu.cu->lumaPos().x >> tu.cu->cs->pcv->maxCUWidthLog2, tu.cu->lumaPos().y >> tu.cu->cs->pcv->maxCUHeightLog2);
    uint16_t tuX = tu.blocks[compID].x;
    uint16_t tuY = tu.blocks[compID].y;
    uint8_t tuW = (uint8_t)tu.blocks[compID].width;
    uint8_t tuH = (uint8_t)tu.blocks[compID].height;
    
    std::string compStr = (compID == COMPONENT_Y) ? "Y" : ((compID == COMPONENT_Cb) ? "Cb" : "Cr");
    std::string trHor = (tu.transformSkip[compID] ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : "MTS")));
    std::string trVer = trHor;
    std::string treeType = tu.cu->treeType == TREE_D ? "DUAL_TREE_LUMA" : (tu.cu->treeType == TREE_C ? "DUAL_TREE_CHROMA" : "SINGLE_TREE");
    std::string predMode = (tu.cu->predMode == MODE_INTRA) ? "MODE_INTRA" : ((tu.cu->predMode == MODE_INTER) ? "MODE_INTER" : "MODE_IBC");
    uint8_t bitDepth = (uint8_t)tu.cu->slice->clpRng(compID).bd;
    uint8_t cbfVal = (uint8_t)TU::getCbf(tu, compID);

    VtmTraceLogger::getInstance().log(poc, sliceType, ctuAddr, tuX, tuY, tuW, tuH, tuW, tuH, compStr, trHor, trVer, "FWD", "ENC_FWD", cbfVal, bitDepth, treeType, predMode);
  }
"""
    if forward_target in cpp_content:
        # Find opening brace
        pos = cpp_content.find(forward_target)
        brace_pos = cpp_content.find("{", pos)
        if brace_pos != -1:
            cpp_content = cpp_content[:pos] + forward_patch + cpp_content[brace_pos + 1:]
            print("Successfully patched forward transformNxN hook.")

    # Inject logging logic in invTransformNxN (Inverse Transform)
    inv_target = "void TrQuant::invTransformNxN("
    inv_patch = """
void TrQuant::invTransformNxN(TransformUnit &tu, const ComponentID &compID, PelBuf &pResi, const QpParam &cQP)
{
  // Trace Extraction Hook - Inverse
  {
    uint32_t poc = tu.cu->slice->getPOC();
    char sliceType = (tu.cu->slice->getSliceType() == I_SLICE) ? 'I' : ((tu.cu->slice->getSliceType() == P_SLICE) ? 'P' : 'B');
    uint32_t ctuAddr = tu.cu->slice->getPPS()->getRealCtuAddr(tu.cu->lumaPos().x >> tu.cu->cs->pcv->maxCUWidthLog2, tu.cu->lumaPos().y >> tu.cu->cs->pcv->maxCUHeightLog2);
    uint16_t tuX = tu.blocks[compID].x;
    uint16_t tuY = tu.blocks[compID].y;
    uint8_t tuW = (uint8_t)tu.blocks[compID].width;
    uint8_t tuH = (uint8_t)tu.blocks[compID].height;
    
    std::string compStr = (compID == COMPONENT_Y) ? "Y" : ((compID == COMPONENT_Cb) ? "Cb" : "Cr");
    std::string trHor = (tu.transformSkip[compID] ? "TS" : (tu.mtsIdx[compID] == MTS_DCT2_DCT2 ? "DCT2" : (tu.mtsIdx[compID] == MTS_SKIP ? "TS" : "MTS")));
    std::string trVer = trHor;
    std::string treeType = tu.cu->treeType == TREE_D ? "DUAL_TREE_LUMA" : (tu.cu->treeType == TREE_C ? "DUAL_TREE_CHROMA" : "SINGLE_TREE");
    std::string predMode = (tu.cu->predMode == MODE_INTRA) ? "MODE_INTRA" : ((tu.cu->predMode == MODE_INTER) ? "MODE_INTER" : "MODE_IBC");
    uint8_t bitDepth = (uint8_t)tu.cu->slice->clpRng(compID).bd;
    uint8_t cbfVal = (uint8_t)TU::getCbf(tu, compID);

    VtmTraceLogger::getInstance().log(poc, sliceType, ctuAddr, tuX, tuY, tuW, tuH, tuW, tuH, compStr, trHor, trVer, "INV", "ENC_RECON", cbfVal, bitDepth, treeType, predMode);
  }
"""
    if inv_target in cpp_content:
        pos = cpp_content.find(inv_target)
        brace_pos = cpp_content.find("{", pos)
        if brace_pos != -1:
            cpp_content = cpp_content[:pos] + inv_patch + cpp_content[brace_pos + 1:]
            print("Successfully patched inverse invTransformNxN hook.")

    with open(trquant_cpp_path, "w", encoding="utf-8") as f:
        f.write(cpp_content)

    print("VTM instrumentation patch complete!")

if __name__ == "__main__":
    vtm_dir = sys.argv[1] if len(sys.argv) > 1 else "vtm_src"
    patch_vtm_source(vtm_dir)
