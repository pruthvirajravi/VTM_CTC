# VTM CTC Workload Trace Extraction & Parallel Cloud Run Plan

## 1. Executive Summary & Objectives
This document specifies the end-to-end plan to execute the **VVC Test Model (VTM)** under full **Common Test Conditions (CTC)** across all standard test sequences and configurations using **GitHub Actions Matrix Workflows**.

* **Input Sequence Repository (Google Drive)**: `https://drive.google.com/drive/folders/1CtXEkjIkd5G1Z-9xQvJgT7ICCtQAETez?usp=drive_link`
* **Output Trace & Metadata Repository (Google Drive)**: `https://drive.google.com/drive/folders/1B2TMPqlOLl1HkA7jfRgcOv4cjgtVOO6e?usp=sharing`
* **Target Workload Length**: Full CTC = $\text{Frame Rate} \times 10 \text{ seconds}$ (e.g., $300$ frames for $30\text{ fps}$, $500$ frames for $50\text{ fps}$, $600$ frames for $60\text{ fps}$).
* **Output Artifacts**: 19-column CSV trace files, VTM encoder summary logs, per-run metadata JSONs, and reconstructed bitstreams.

---

## 2. 19-Column Architecture-Neutral Trace Schema

Every transform operation executed during the VTM run is logged to `vtm_trace.csv` with the following columns:

```csv
task_id,poc,slice_type,ctu_addr,tu_x,tu_y,tu_w,tu_h,tr_eff_w,tr_eff_h,comp,tr_type_hor,tr_type_ver,direction,stage,cbf,bit_depth,tree_type,pred_mode
```

### Field Definitions:
1. **`task_id`**: `uint64` – Monotonically increasing index ($0, 1, 2, \dots$) representing strict processing order.
2. **`poc`**: `uint32` – Picture Order Count (Frame Index).
3. **`slice_type`**: `char` – `I` (Intra), `P` (Predictive), `B` (Bi-predictive).
4. **`ctu_addr`**: `uint32` – CTU raster index in frame.
5. **`tu_x`, `tu_y`**: `uint16` – Absolute coordinate of top-left TU pixel in frame.
6. **`tu_w`, `tu_h`**: `uint8` – Nominal transform block width and height ($2, 4, 8, 16, 32, 64$).
7. **`tr_eff_w`, `tr_eff_h`**: `uint8` – Effective computed transform size (accounting for $64\to32$ and $32\to16$ zeroing).
8. **`comp`**: `string` – Color plane: `Y` (Luma), `Cb` (Chroma Blue), `Cr` (Chroma Red).
9. **`tr_type_hor`**: `string` – Horizontal transform kernel: `DCT2`, `DST7`, `DCT8`.
10. **`tr_type_ver`**: `string` – Vertical transform kernel: `DCT2`, `DST7`, `DCT8`.
11. **`direction`**: `string` – `FWD` (Forward Transform), `INV` (Inverse Transform).
12. **`stage`**: `string` – `ENC_FWD` (Encoder Search/Evaluation), `ENC_RECON` (Reconstruction Loop).
13. **`cbf`**: `uint8` – Coded Block Flag (`1` = non-zero transform coefficients exist; `0` = all-zero skip block).
14. **`bit_depth`**: `uint8` – Internal bit depth (`8` or `10`).
15. **`tree_type`**: `string` – `SINGLE_TREE`, `DUAL_TREE_LUMA`, `DUAL_TREE_CHROMA`.
16. **`pred_mode`**: `string` – `MODE_INTRA`, `MODE_INTER`, `MODE_IBC`.

---

## 3. VTM Source Code C++ Instrumentation Patch

Apply the following patch to the VTM repository (`source/Lib/CommonLib/TrQuant.cpp` and `source/Lib/CommonLib/Transform.cpp`):

### 3.1 Trace Header & Global Hook (`source/Lib/CommonLib/TraceLogger.h`)
```cpp
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

    void init(const std::string& filename) {
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
        }
    }

    void close() {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_traceFile.is_open()) {
            m_traceFile.close();
        }
    }
};
```

---

## 4. CTC Test Sequence Matrix & Parameters (10s Full CTC)

| Class | Sequence Name | Resolution | Frame Rate | Frames ($10\text{s}$) | Bit Depth |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Class A1** | Tango2 | $3840 \times 2160$ | 60 fps | 600 | 10-bit |
| **Class A1** | Campfire | $3840 \times 2160$ | 30 fps | 300 | 10-bit |
| **Class A2** | CatRobot1 | $3840 \times 2160$ | 60 fps | 600 | 10-bit |
| **Class A2** | DaylightRoad2 | $3840 \times 2160$ | 60 fps | 600 | 10-bit |
| **Class B** | MarketPlace | $1920 \times 1080$ | 60 fps | 600 | 10-bit |
| **Class B** | RitualDance | $1920 \times 1080$ | 60 fps | 600 | 10-bit |
| **Class B** | BasketballDrive | $1920 \times 1080$ | 50 fps | 500 | 8-bit / 10-bit |
| **Class B** | BQTerrace | $1920 \times 1080$ | 60 fps | 600 | 8-bit / 10-bit |
| **Class C** | BasketballDrill | $832 \times 480$ | 50 fps | 500 | 8-bit |
| **Class C** | BQMall | $832 \times 480$ | 60 fps | 600 | 8-bit |
| **Class C** | PartyScene | $832 \times 480$ | 50 fps | 500 | 8-bit |
| **Class C** | RaceHorsesC | $832 \times 480$ | 30 fps | 300 | 8-bit |
| **Class D** | BasketballPass | $416 \times 240$ | 50 fps | 500 | 8-bit |
| **Class D** | BQSquare | $416 \times 240$ | 60 fps | 600 | 8-bit |
| **Class D** | BlowingBubbles | $416 \times 240$ | 50 fps | 500 | 8-bit |
| **Class D** | RaceHorses | $416 \times 240$ | 30 fps | 300 | 8-bit |
| **Class E** | FourPeople | $1280 \times 720$ | 60 fps | 600 | 8-bit |
| **Class E** | Johnny | $1280 \times 720$ | 60 fps | 600 | 8-bit |
| **Class E** | KristenAndSara | $1280 \times 720$ | 60 fps | 600 | 8-bit |

### Configurations & QPs to Run:
* **Profiles**:
  1. `All Intra (AI)`: `cfg/encoder_intra_vtm.cfg`
  2. `Random Access (RA)`: `cfg/encoder_randomaccess_vtm.cfg`
  3. `Low Delay B (LDB)`: `cfg/encoder_lowdelay_vtm.cfg`
  4. `Low Delay P (LDP)`: `cfg/encoder_lowdelay_P_vtm.cfg`
* **Target QPs**: `22`, `27`, `32`, `37`

---

## 5. Complete GitHub Actions Workflow (`.github/workflows/vtm_ctc_matrix.yml`)

The following YAML workflow sets up a massively parallel runner matrix. Each job downloads its specific sequence, compiles VTM with the trace patch, executes the encoding, validates the trace, and uploads results directly to the Google Drive destination folder.

```yaml
name: VTM CTC Parallel Matrix Execution

on:
  workflow_dispatch:
    inputs:
      vtm_version:
        description: 'VTM Git Tag or Branch (e.g. VTM-16.0)'
        required: true
        default: 'VTM-16.0'
      quick_test:
        description: 'Set to true to run only 10 frames (validation mode)'
        type: boolean
        default: false

env:
  SRC_DRIVE_FOLDER: "1CtXEkjIkd5G1Z-9xQvJgT7ICCtQAETez"
  DST_DRIVE_FOLDER: "1B2TMPqlOLl1HkA7jfRgcOv4cjgtVOO6e"

jobs:
  run-vtm:
    name: ${{ matrix.sequence }} | ${{ matrix.config }} | QP${{ matrix.qp }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        sequence:
          - { name: "BQMall", width: 832, height: 480, fps: 60, frames: 600, bitdepth: 8 }
          - { name: "BasketballDrill", width: 832, height: 480, fps: 50, frames: 500, bitdepth: 8 }
          - { name: "PartyScene", width: 832, height: 480, fps: 50, frames: 500, bitdepth: 8 }
          - { name: "RaceHorsesC", width: 832, height: 480, fps: 30, frames: 300, bitdepth: 8 }
          - { name: "BasketballPass", width: 416, height: 240, fps: 50, frames: 500, bitdepth: 8 }
          - { name: "BQSquare", width: 416, height: 240, fps: 60, frames: 600, bitdepth: 8 }
          - { name: "BlowingBubbles", width: 416, height: 240, fps: 50, frames: 500, bitdepth: 8 }
          - { name: "RaceHorses", width: 416, height: 240, fps: 30, frames: 300, bitdepth: 8 }
          - { name: "FourPeople", width: 1280, height: 720, fps: 60, frames: 600, bitdepth: 8 }
          - { name: "Johnny", width: 1280, height: 720, fps: 60, frames: 600, bitdepth: 8 }
          - { name: "KristenAndSara", width: 1280, height: 720, fps: 60, frames: 600, bitdepth: 8 }
          - { name: "BasketballDrive", width: 1920, height: 1080, fps: 50, frames: 500, bitdepth: 8 }
          - { name: "BQTerrace", width: 1920, height: 1080, fps: 60, frames: 600, bitdepth: 8 }
          - { name: "MarketPlace", width: 1920, height: 1080, fps: 60, frames: 600, bitdepth: 10 }
          - { name: "RitualDance", width: 1920, height: 1080, fps: 60, frames: 600, bitdepth: 10 }
          - { name: "Tango2", width: 3840, height: 2160, fps: 60, frames: 600, bitdepth: 10 }
          - { name: "Campfire", width: 3840, height: 2160, fps: 30, frames: 300, bitdepth: 10 }
        config: ["AI", "RA", "LDB", "LDP"]
        qp: [22, 27, 32, 37]

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set Up Build Tools & Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install System Dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake build-essential gdown rclone

      - name: Download YUV Test Sequence from Google Drive
        run: |
          mkdir -p sequences
          echo "Downloading ${{ matrix.sequence.name }}.yuv from Google Drive..."
          python3 -c '
          import gdown, os
          seq_name = "${{ matrix.sequence.name }}"
          folder_id = "${{ env.SRC_DRIVE_FOLDER }}"
          url = f"https://drive.google.com/drive/folders/{folder_id}"
          gdown.download_folder(url, output="sequences", quiet=False, use_cookies=False)
          '

      - name: Clone & Patch VTM
        run: |
          git clone https://vcgit.hhi.fraunhofer.de/jvet/VVCSoftware_VTM.git vtm_src
          cd vtm_src
          git checkout ${{ github.event.inputs.vtm_version || 'VTM-16.0' }}
          
          # Copy instrumentation files and apply patch
          cp ../scripts/TraceLogger.h source/Lib/CommonLib/TraceLogger.h
          git apply ../scripts/vtm_trace_hook.patch

          mkdir build && cd build
          cmake .. -DCMAKE_BUILD_TYPE=Release
          make -j$(nproc)

      - name: Execute VTM Encoding & Trace Extraction
        run: |
          CONFIG_FILE="cfg/encoder_randomaccess_vtm.cfg"
          if [ "${{ matrix.config }}" = "AI" ]; then CONFIG_FILE="cfg/encoder_intra_vtm.cfg"; fi
          if [ "${{ matrix.config }}" = "RA" ]; then CONFIG_FILE="cfg/encoder_randomaccess_vtm.cfg"; fi
          if [ "${{ matrix.config }}" = "LDB" ]; then CONFIG_FILE="cfg/encoder_lowdelay_vtm.cfg"; fi
          if [ "${{ matrix.config }}" = "LDP" ]; then CONFIG_FILE="cfg/encoder_lowdelay_P_vtm.cfg"; fi

          FRAMES=${{ matrix.sequence.frames }}
          if [ "${{ github.event.inputs.quick_test }}" = "true" ]; then
            FRAMES=10
          fi

          mkdir -p output_run
          cd output_run

          # Run Encoder
          ../vtm_src/bin/EncoderAppStatic \
            -c ../vtm_src/${CONFIG_FILE} \
            -i ../sequences/${{ matrix.sequence.name }}.yuv \
            -wdt ${{ matrix.sequence.width }} \
            -hgt ${{ matrix.sequence.height }} \
            -fr ${{ matrix.sequence.fps }} \
            -f ${FRAMES} \
            -q ${{ matrix.qp }} \
            --InputBitDepth=${{ matrix.sequence.bitdepth }} \
            --InternalBitDepth=${{ matrix.sequence.bitdepth }} \
            -b str_${{ matrix.sequence.name }}_${{ matrix.config }}_QP${{ matrix.qp }}.bin \
            -o recon_${{ matrix.sequence.name }}_${{ matrix.config }}_QP${{ matrix.qp }}.yuv \
            > enc_${{ matrix.sequence.name }}_${{ matrix.config }}_QP${{ matrix.qp }}.log

      - name: Validate & Compress Trace Artifacts
        run: |
          cd output_run
          RUN_ID="${{ matrix.sequence.name }}_${{ matrix.config }}_QP${{ matrix.qp }}"
          
          # Check CSV Trace Non-Empty
          if [ ! -s vtm_trace.csv ]; then
            echo "ERROR: vtm_trace.csv is empty or missing!"
            exit 1
          fi

          mv vtm_trace.csv trace_${RUN_ID}.csv
          tar -czvf ${RUN_ID}_artifacts.tar.gz trace_${RUN_ID}.csv enc_${RUN_ID}.log

      - name: Upload Artifacts to Google Drive Destination
        env:
          GDRIVE_CREDENTIALS: ${{ secrets.GDRIVE_SERVICE_ACCOUNT_KEY }}
        run: |
          cd output_run
          RUN_ID="${{ matrix.sequence.name }}_${{ matrix.config }}_QP${{ matrix.qp }}"
          
          # Uploading via python script using Service Account or Drive API
          python3 -c '
          import os, sys
          from googleapiclient.discovery import build
          from googleapiclient.http import MediaFileUpload
          from google.oauth2 import service_account

          # Check if service account key exists
          key_json = os.environ.get("GDRIVE_CREDENTIALS")
          if key_json:
              with open("sa_key.json", "w") as f:
                  f.write(key_json)
              creds = service_account.Credentials.from_service_account_file("sa_key.json")
              service = build("drive", "v3", credentials=creds)
              
              file_metadata = {
                  "name": f"${RUN_ID}_artifacts.tar.gz",
                  "parents": ["${{ env.DST_DRIVE_FOLDER }}"]
              }
              media = MediaFileUpload(f"${RUN_ID}_artifacts.tar.gz", mimetype="application/gzip")
              file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
              print(f"Uploaded successfully to Google Drive. File ID: {file.get(\"id\")}")
          else:
              print("Notice: GDRIVE_CREDENTIALS secret not set. Storing as GitHub Artifact.")
          '

      - name: GitHub Actions Fallback Artifact Upload
        uses: actions/upload-artifact@v4
        with:
          name: trace_${{ matrix.sequence.name }}_${{ matrix.config }}_QP${{ matrix.qp }}
          path: output_run/*_artifacts.tar.gz
          retention-days: 14
```

---

## 6. Execution & Setup Instructions for Claude / GitHub CI

1. **Repository Structure**:
   ```text
   .
   ├── .github/
   │   └── workflows/
   │       └── vtm_ctc_matrix.yml
   └── scripts/
       ├── TraceLogger.h
       └── vtm_trace_hook.patch
   ```

2. **Google Drive Integration**:
   * Set the GitHub Secret `GDRIVE_SERVICE_ACCOUNT_KEY` with the Service Account JSON key that has **Editor** permissions on destination folder `1B2TMPqlOLl1HkA7jfRgcOv4cjgtVOO6e`.
   * Input sequences in `1CtXEkjIkd5G1Z-9xQvJgT7ICCtQAETez` must have view/download permissions.

3. **Triggering Execution**:
   * In GitHub, navigate to **Actions $\to$ VTM CTC Parallel Matrix Execution $\to$ Run workflow**.
   * Run with `quick_test = true` for an initial 10-frame dry-run.
   * Launch with `quick_test = false` for the full 10-second CTC benchmark.
