import struct
import numpy as np

def test_10bit_frame():
    w, h = 3840, 2160
    # Create rich 10-bit gradient and texture samples in valid 10-bit range [0, 1023]
    y_plane = np.zeros((h, w), dtype=np.uint16)
    for y in range(h):
        for x in range(w):
            # Gradient + high frequency blocks to trigger all TU sizes
            val = (512 + int(200 * np.sin(x / 32.0) * np.cos(y / 32.0)) + (x % 64)) % 1020
            y_plane[y, x] = max(16, min(1000, val))

    uv_h, uv_w = h // 2, w // 2
    u_plane = np.full((uv_h, uv_w), 512, dtype=np.uint16)
    v_plane = np.full((uv_h, uv_w), 512, dtype=np.uint16)

    raw_bytes = y_plane.tobytes() + u_plane.tobytes() + v_plane.tobytes()
    print(f"Single 4K 10-bit frame size: {len(raw_bytes):,} bytes")
    # Verify no value > 1023
    samples = np.frombuffer(raw_bytes, dtype=np.uint16)
    print(f"Min sample: {samples.min()}, Max sample: {samples.max()}")
    assert samples.max() <= 1023, "Sample exceeds 10-bit range!"
    print("SUCCESS: 10-bit frame perfectly in range [0, 1023]!")

if __name__ == "__main__":
    test_10bit_frame()
