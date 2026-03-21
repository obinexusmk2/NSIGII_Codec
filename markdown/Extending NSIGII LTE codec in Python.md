# Developer guide: Extending NSIGII LTE codec in Python

This guide shows how to **work with `.nsigii` files and NSIGII concepts from Python**, so you can:

- Inspect and decode NSIGII containers.
- Re‑implement or prototype parts of the trident pipeline.
- Build analysis tools (e.g. discriminant visualizers, ORDER/CHAOS statistics, human‑rights audits).

It assumes you’ve read the main README and skimmed the Go implementation.

---

## 1. Understanding the Go reference

Key structures you’ll mirror in Python:

- **Container header** (fixed struct)
- **Per‑frame header** (`Size uint32`)
- **Trident packet** (conceptual; not fully serialized in the current writer)
- **ROpen encoding**, **RB‑AVL confidence**, **discriminant flash**, **bipolar enzyme**

From the Go code:

> "NSIGII Polygatic Video Codec v7.0.0"  
> "Encoding frames with trident verification..."

The current writer only persists the **compressed YUV frame stream**, not the full `TridentPacket` structure. That means your first Python extension is usually:

1. **Container‑level tooling** (read header + frames).
2. **Re‑encoding / re‑verification** in Python using the same math.

---

## 2. Parsing `.nsigii` in Python

### 2.1. Container header

The header layout is:

```go
Magic      [8]byte // "NSIGII\0\0"
Version    [8]byte // "7.0.0\0\0\0"
Width      uint32
Height     uint32
FrameCount uint32
Reserved   uint32
```

Python parser:

```python
import struct
from dataclasses import dataclass
from typing import BinaryIO

HEADER_STRUCT = struct.Struct("<8s8sIIII")  # little-endian

@dataclass
class NSIGIIHeader:
    magic: str
    version: str
    width: int
    height: int
    frame_count: int
    reserved: int

def read_header(f: BinaryIO) -> NSIGIIHeader:
    data = f.read(HEADER_STRUCT.size)
    if len(data) != HEADER_STRUCT.size:
        raise EOFError("File too small for NSIGII header")
    magic_raw, version_raw, width, height, frame_count, reserved = HEADER_STRUCT.unpack(data)
    magic = magic_raw.rstrip(b"\x00").decode("ascii", errors="replace")
    version = version_raw.rstrip(b"\x00").decode("ascii", errors="replace")
    if magic != "NSIGII":
        raise ValueError(f"Not an NSIGII file (magic={magic!r})")
    return NSIGIIHeader(magic, version, width, height, frame_count, reserved)
```

### 2.2. Frame iterator

Each frame is:

```go
struct{ Size uint32 } + <Size bytes of DEFLATE-compressed YUV420>
```

Python:

```python
FRAME_HEADER_STRUCT = struct.Struct("<I")

def iter_frames(f: BinaryIO):
    while True:
        hdr = f.read(FRAME_HEADER_STRUCT.size)
        if not hdr:
            break
        if len(hdr) != FRAME_HEADER_STRUCT.size:
            raise EOFError("Truncated frame header")
        (size,) = FRAME_HEADER_STRUCT.unpack(hdr)
        payload = f.read(size)
        if len(payload) != size:
            raise EOFError("Truncated frame payload")
        yield payload
```

---

## 3. Decompressing and reconstructing frames

The Go codec uses **DEFLATE** via `compress/flate` and writes **YUV420** frames. In Python:

```python
import zlib
import numpy as np

def decode_yuv420_frame(data: bytes, width: int, height: int):
    raw = zlib.decompress(data)
    y_size = width * height
    uv_size = y_size // 4
    if len(raw) != y_size + 2 * uv_size:
        raise ValueError("Unexpected YUV420 size")
    y = np.frombuffer(raw[0:y_size], dtype=np.uint8).reshape((height, width))
    u = np.frombuffer(raw[y_size:y_size+uv_size], dtype=np.uint8).reshape((height // 2, width // 2))
    v = np.frombuffer(raw[y_size+uv_size:], dtype=np.uint8).reshape((height // 2, width // 2))
    return y, u, v
```

To convert YUV420 → RGB for visualization, one  can use OpenCV or your own formulas.

---

## 4. Re‑implementing NSIGII primitives in Python

Even though the current `.nsigii` file doesn’t store full trident packets, one can **mirror the logic** to:

- Re‑encode raw frames in Python.
- Compare discriminant states with the Go implementation.
- Prototype alternative policies.

### 4.1. Discriminant flash verification

Go:

```go
delta := ff.B*ff.B - 4*ff.A*ff.C
// Δ > 0 → ORDER, Δ = 0 → CONSENSUS, Δ < 0 → CHAOS
```

Python:

```python
from enum import Enum
import math

class DiscriminantState(Enum):
    ORDER = 1
    CONSENSUS = 0
    CHAOS = -1

def compute_discriminant(a: float, b: float, c: float) -> float:
    return b*b - 4*a*c

def classify_discriminant(a: float, b: float, c: float) -> DiscriminantState:
    delta = compute_discriminant(a, b, c)
    if delta > 0:
        return DiscriminantState.ORDER
    elif delta == 0:
        return DiscriminantState.CONSENSUS
    else:
        return DiscriminantState.CHAOS
```

Mirror `bipartiteConsensus`:

```python
def bipartite_consensus(content: bytes, wheel_pos: int) -> tuple[float, float, float]:
    if not content:
        return 1.0, 0.0, 1.0
    set_bits = sum(bin(b).count("1") for b in content)
    total_bits = len(content) * 8
    base = set_bits / total_bits
    wheel_correct = math.sin(math.radians(wheel_pos))
    consensus = abs(base + wheel_correct) / 2.0
    return 1.0, consensus * 4.0, 1.0
```

### 4.2. ROPEN sparse duplex encoding

Go:

```go
logical = a ^ Conjugate(b) // or Conjugate(a) ^ b
```

Python:

```python
POLARITY_POS = ord('+')
POLARITY_NEG = ord('-')
EPSILON_PAD = 0x00

def conjugate(x: int) -> int:
    return 0xF ^ x

def rift_encode(data: bytes, polarity_a: bool) -> bytes:
    out = bytearray()
    for i in range(0, len(data), 2):
        a = data[i]
        b = data[i+1] if i+1 < len(data) else EPSILON_PAD
        if polarity_a:
            logical = a ^ conjugate(b)
        else:
            logical = conjugate(a) ^ b
        out.append(logical)
    return bytes(out)
```


1. Splits an RGB frame into halves.
2. Applies `rift_encode`.
3. Computes bipartite consensus and discriminant.
4. Applies a simple enzyme repair (e.g. XOR‑chain) when CHAOS is detected.

---

## 5. Strategy for Python extensions


1. **Inspector CLI (Python):**
   - Input: `.nsigii` file.
   - Output: header info, frame count, total compressed size, per‑frame size histogram.
   - Optional: decode a sample frame to PNG.

2. **Discriminant visualizer:**
   - For each frame payload, run `bipartite_consensus` + `classify_discriminant`.
   - Plot ORDER / CONSENSUS / CHAOS over time.

3. **Python encoder prototype:**
   - Use `ffmpeg-python` or `imageio` to get RGB frames.
   - Implement NSIGII encode path in Python (ROpen + discriminant + DEFLATE).
   - Compare output sizes and ORDER/CHAOS ratios with the Go implementation.

4. **Bindings / FFI (optional):**
   - Expose the Go codec as a shared library (`c-shared`) and call from Python via `ctypes` or `cffi`.
   - Or re‑implement only the mathematical parts in Python and keep heavy lifting in Go.
 

## 6. Design principles to preserve


When extending it in Python, try to keep:

- **Trident separation of concern:**
  - TRANSMIT (ORDER), RECEIVE (CHAOS), VERIFY (CONSENSUS).
- **Human‑rights semantics:**
  - Keep `HumanRightsTag`‑like metadata alongside your Python tools.
- **Tomographic thinking:**
  - Treat each frame as a slice through a higher‑dimensional state (ORDER/CHAOS history, entropy, wheel position).
- **Non‑destructive experimentation:**
 - Prefer adding new channels / flags / sidecar metadata over mutating the core container format.
