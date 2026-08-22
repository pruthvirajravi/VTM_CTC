#pragma once
#include <fstream>
#include <mutex>
#include <string>
#include <cstdint>

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

    void init(const std::string& filename = "vtm_trace.csv") {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (!m_traceFile.is_open()) {
            m_traceFile.open(filename, std::ios::out);
            m_traceFile << "task_id,poc,slice_type,ctu_addr,tu_x,tu_y,tu_w,tu_h,"
                        << "tr_eff_w,tr_eff_h,comp,tr_type_hor,tr_type_ver,"
                        << "direction,stage,cbf,bit_depth,tree_type,pred_mode\n";
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
            init();
        }
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
    }

    void close() {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_traceFile.is_open()) {
            m_traceFile.close();
        }
    }
};
