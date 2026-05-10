# nsigii_player.py
import sys
import struct
import zlib
from pathlib import Path
import cv2
import numpy as np
from typing import Generator

class NSIGIIPlayer:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.frame_count = 0

    def read_header(self, f):
        """Read NSIGII container header"""
        magic = f.read(8)
        if magic != b'NSIGII\x00\x00':
            raise ValueError("Not a valid NSIGII file")

        version = f.read(8)
        self.width = struct.unpack("<I", f.read(4))[0]
        self.height = struct.unpack("<I", f.read(4))[0]
        self.frame_count = struct.unpack("<I", f.read(4))[0]
        f.read(4)  # reserved

        print(f"NSIGII Video: {self.width}x{self.height}, {self.frame_count} frames")

    def decode_frame(self, f) -> np.ndarray | None:
        """Read and decode one frame"""
        # Read frame size
        size_data = f.read(4)
        if not size_data:
            return None
        frame_size = struct.unpack("<I", size_data)[0]

        # Read compressed frame data
        compressed = f.read(frame_size)
        if len(compressed) != frame_size:
            return None

        try:
            # Decompress DEFLATE (used in Go codec)
            yuv_data = zlib.decompress(compressed)

            # Convert YUV420 to RGB
            yuv = np.frombuffer(yuv_data, dtype=np.uint8)
            yuv = yuv.reshape((self.height + self.height//2, self.width))

            rgb = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB_I420)
            return rgb

        except Exception as e:
            print(f"Frame decode error: {e}")
            return None

    def play(self, nsigii_path: str, fps: int = 30):
        path = Path(nsigii_path)
        if not path.exists():
            print("File not found")
            return

        cap = None
        try:
            with open(path, "rb") as f:
                self.read_header(f)

                window_name = f"NSIGII Player - {path.name}"
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

                frame_num = 0
                while True:
                    frame = self.decode_frame(f)
                    if frame is None:
                        break

                    cv2.imshow(window_name, frame)
                    frame_num += 1

                    if cv2.waitKey(1000 // fps) & 0xFF == ord('q'):
                        break

                    if frame_num % 30 == 0:
                        print(f"Playing frame {frame_num}/{self.frame_count}")

        except Exception as e:
            print(f"Error playing file: {e}")
        finally:
            cv2.destroyAllWindows()


def main():
    if len(sys.argv) < 2:
        print("Usage: python nsigii_player.py <file.nsigii> [fps]")
        return

    fps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    player = NSIGIIPlayer()
    player.play(sys.argv[1], fps)


if __name__ == "__main__":
    main()
