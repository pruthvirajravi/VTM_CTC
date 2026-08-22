#pragma once
#include <fstream>
#include <mutex>
#include <string>
#include <cstdint>
#include <cstdlib>
#include <iostream>

class VtmTraceLogger {
private:
    std::ofstream m_traceFile;
    std::mutex m_mutex;
    uint64_t m_taskId;

    VtmTraceLogger() : m_taskId(0) {}

public:
    static VtmTraceLogger& getInstance() {
        static VtmTraceLogger instance;
        return instance;
    }

    void init(const std::string& filename = "") {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (!m_traceFile.is_open()) {
            std::string outPath = filename;
            if (outPath.empty()) {
                const char* envPath = std::getenv("VTM_TRACE_FILE");
                outPath = (envPath && envPath[0] != '\0') ? std::string(envPath) : "vtm_trace.csv";
            }
            m_traceFile.open(outPath, std::ios::out | std::ios::app);
            if (m_traceFile.is_open()) {
                m_traceFile.seekp(0, std::ios::end);
                if (m_traceFile.tellp() == 0) {
                    m_traceFile << "task_id,poc,slice_type,ctu_addr,tu_x,tu_y,tu_w,tu_h,"
                                << "tr_eff_w,tr_eff_h,comp,tr_type_hor,tr_type_ver,"
                                << "direction,stage,cbf,bit_depth,tree_type,pred_mode\n";
                }
                m_traceFile.flush();
            }
        }
    }

    void log(uint32_t poc, char sliceType, uint32_t ctuAddr,
             uint16_t tuX, uint16_t tuY, uint8_t tuW, uint8_t tuH,
             uint8_t trEffW, uint8_t trEffH, const std::string& comp,
             const std::string& trHor, const std::string& trVer,
             const std::string& dir, const std::string& stage,
             uint8_t cbf, uint8_t bitDepth, const std::string& treeType,
             const std::string& predMode) {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (!m_traceFile.is_open()) {
            const char* envPath = std::getenv("VTM_TRACE_FILE");
            std::string outPath = (envPath && envPath[0] != '\0') ? std::string(envPath) : "vtm_trace.csv";
            m_traceFile.open(outPath, std::ios::out | std::ios::app);
            if (m_traceFile.is_open()) {
                m_traceFile.seekp(0, std::ios::end);
                if (m_traceFile.tellp() == 0) {
                    m_traceFile << "task_id,poc,slice_type,ctu_addr,tu_x,tu_y,tu_w,tu_h,"
                                << "tr_eff_w,tr_eff_h,comp,tr_type_hor,tr_type_ver,"
                                << "direction,stage,cbf,bit_depth,tree_type,pred_mode\n";
                }
            }
        }
        if (m_traceFile.is_open()) {
            m_traceFile << m_taskId++ << ","
                        << poc << ","
                        << sliceType << ","
                        << ctuAddr << ","
                        << tuX << "," << tuY << ","
                        << (int)tuW << "," << (int)tuH << ","
                        << (int)trEffW << "," << (int)trEffH << ","
                        << comp << ","
                        << trHor << "," << trVer << ","
                        << dir << "," << stage << ","
                        << (int)cbf << "," << (int)bitDepth << ","
                        << treeType << "," << predMode << "\n";
            m_traceFile.flush();
        }
    }

    void close() {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_traceFile.is_open()) {
            m_traceFile.flush();
            m_traceFile.close();
        }
    }
};
