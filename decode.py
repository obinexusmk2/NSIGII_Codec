import sys
import struct
import os
import zlib
from PIL import Image


HEADER_SIZE = 32


def parse_header(data):
    if data[:6] != b'NSIGII':
        raise ValueError("Invalid NSIGII file")

    version = data[8:13].decode("ascii").rstrip("\x00")
    width = struct.unpack("<I", data[16:20])[0]
    height = struct.unpack("<I", data[20:24])[0]
    frame_count = struct.unpack("<I", data[24:28])[0]

    return version, width, height, frame_count


def yuv420_to_rgb(width, height, yuv):
    frame_size = width * height
    y_plane = yuv[:frame_size]
    u_plane = yuv[frame_size:frame_size + frame_size // 4]
    v_plane = yuv[frame_size + frame_size // 4:]

    rgb = bytearray(width * height * 3)

    for j in range(height):
        for i in range(width):
            y = y_plane[j * width + i]

            uv_index = (j // 2) * (width // 2) + (i // 2)
            u = u_plane[uv_index] - 128
            v = v_plane[uv_index] - 128

            r = y + 1.402 * v
            g = y - 0.344136 * u - 0.714136 * v
            b = y + 1.772 * u

            idx = (j * width + i) * 3
            rgb[idx] = max(0, min(255, int(r)))
            rgb[idx + 1] = max(0, min(255, int(g)))
            rgb[idx + 2] = max(0, min(255, int(b)))

    return bytes(rgb)


def main():
    if len(sys.argv) != 2:
        print("Usage: python decode.py <input_file>")
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        data = f.read()

    version, width, height, frame_count = parse_header(data)

    print("Version:", version)
    print("Width:", width)
    print("Height:", height)
    print("Frames:", frame_count)

    offset = HEADER_SIZE
    os.makedirs("decoded", exist_ok=True)

    for frame_index in range(frame_count):
        frame_size = struct.unpack("<I", data[offset:offset + 4])[0]
        offset += 4

        compressed = data[offset:offset + frame_size]
        offset += frame_size

        decompressed = zlib.decompress(compressed, -zlib.MAX_WBITS)

        rgb = yuv420_to_rgb(width, height, decompressed)

        image = Image.frombytes("RGB", (width, height), rgb)

        output_path = os.path.join("decoded", f"frame_{frame_index}.png")
        image.save(output_path)

        print(f"Decoded frame {frame_index} → {output_path}")

if __name__ == "__main__":
    main()
