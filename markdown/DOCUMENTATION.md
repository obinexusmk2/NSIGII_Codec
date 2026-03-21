# NSIGII Polygatic Video Codec - Technical Documentation

## System Architecture Overview

The NSIGII (ενσιγιι) codec implements a human rights verification protocol through a trident channel architecture that processes video data with mathematical guarantees of consistency and integrity.

### Core Components

#### 1. Discriminant Flash Verification System

The codec uses the quadratic discriminant formula to determine system state at each frame processing stage:

```
Δ = b² - 4ac
```

Three possible states emerge from the discriminant value:

- **ORDER (Δ > 0)**: The system has two distinct real roots, indicating stable dual-polarity encoding
- **CONSENSUS (Δ = 0)**: The flash point where encoding achieves perfect verification
- **CHAOS (Δ < 0)**: Complex roots indicate instability requiring enzyme repair operations

The roots themselves encode the bipolar nature of the system through the ± operator in the quadratic formula:

```
x = (-b ± √Δ) / 2a
```

The positive root represents the BUILD/CREATE path, while the negative root represents the BREAK/DESTROY path.

#### 2. Flash Buffer Storage Model

The flash buffer implements dimensional reduction through two mathematical operations:

**Additive Flash**: `1/2 + 1/2 = 1`
This operation unites two half-buffers into a complete frame without loss.

**Multiplicative Flash**: `1/2 × 1/2 = 1/4`
This operation requires four quarter-flashes to reconstruct the unit, implementing a 2D to 1D dimensional reduction.

The relativistic time encoding is modeled as:

```
t' = 1 / √(1 - v²/c²)
```

where v represents the velocity of state change in the codec stream.

#### 3. ROPEN Sparse Duplex Encoding

The ROPEN algorithm performs 2→1 sparse duplex encoding where two physical bytes map to one logical byte:

**Polarity A (Normal)**:
```
logical = a ⊕ conjugate(b)
```

**Polarity B (Conjugate)**:
```
logical = conjugate(a) ⊕ b
```

The conjugate operation performs nibble inversion:
```
conjugate(x) = 0xF ⊕ x
```

This creates a heterogeneous-homogeneous encoding space where data can be read coherently from either polarity without preference.

#### 4. Red-Black AVL Tree Pruning

The RB-AVL tree maintains encoding state with the following guarantees:

- **Space complexity**: O(½ log n) through combined Red-Black and AVL balancing
- **Time complexity**: O(¼ log n) per operation through duplex encoding
- **NIL preservation**: Zero bytes are never pruned, maintaining epsilon-state continuity

Pruning occurs when:
```
confidence < 0.5 OR polarity == NEGATIVE
```

The streak counter tracks consecutive negative measurements:
```
if streak[key & 0xFF] >= PRUNE_STREAK:
    node.val = 0
    node.confidence = 0.0
```

#### 5. Trident Channel Architecture

Three channels process each frame with distinct roles:

**Channel 0 - Transmitter (1/3 ratio)**
- **State**: ORDER
- **Operation**: Encodes raw RGB24 data using ROPEN sparse duplex
- **Permission**: WRITE (RWX = 0x02)
- **Address**: 127.0.0.1
- **Wheel Position**: 0°

**Channel 1 - Receiver (2/3 ratio)**  
- **State**: CHAOS (bipolar)
- **Operation**: Decodes and verifies hash integrity
- **Permission**: READ (RWX = 0x04)
- **Address**: 127.0.0.2
- **Wheel Position**: 120°

**Channel 2 - Verifier (3/3 ratio)**
- **State**: VERIFIED
- **Operation**: Applies discriminant flash verification
- **Permission**: EXECUTE (RWX = 0x01) → FULL (RWX = 0x07) when verified
- **Address**: 127.0.0.3
- **Wheel Position**: 240° → 360° when complete

#### 6. Bipolar Enzyme Model

The enzyme model implements biological-style read-write-execute operations:

**Order Sequence**:
```
CREATE → BUILD → RENEW → REPAIR
```

**Chaos Sequence**:
```
DESTROY → BREAK → REPAIR
```

Each operation transforms data without requiring explicit state management, mimicking how biological enzymes process substrates:

- **CREATE**: Allocates new buffer space
- **DESTROY**: Zeros buffer (epsilon state)
- **BUILD**: Appends data structurally
- **BREAK**: Performs dimensional halving
- **RENEW**: Refreshes through copy operation
- **REPAIR**: XOR-based error correction with shift

#### 7. Quadratic Spline Interpolation

Frame transitions use quadratic Bézier splines for smooth interpolation:

```
P(t) = (1-t)²P₀ + 2(1-t)t·P₁ + t²P₂
```

where:
- P₀ is the starting frame pixel value
- P₁ is the midpoint control value
- P₂ is the ending frame pixel value
- t ∈ [0,1] is the interpolation parameter

This creates C¹ continuous transitions between frames, preventing visual artifacts during playback.

### Codec Operation Flow

1. **Input Stage**: Raw RGB24 frames read from stdin or file
2. **Flash Buffer**: Frame split into two halves for 1/2 + 1/2 operation
3. **Channel 0**: ROPEN sparse duplex encoding with polarity A
4. **RB-AVL Insert**: Encoded bytes stored with confidence scores
5. **Channel 1**: Bipartite order check (even/odd sequence token)
6. **Channel 2**: Discriminant calculation and flash verification
7. **Enzyme Operation**: Repair applied if chaos state detected
8. **YUV Conversion**: RGB24 → YUV420 for compression efficiency
9. **DEFLATE**: Standard compression on YUV data
10. **Output Stage**: Binary packet with NSIGII header

### Mathematical Foundations

#### Bipartite Consensus Formula

The consensus value represents the balance between order and chaos:

```
order_weight = count_set_bits(content)
total_bits = content_length × 8
base_consensus = order_weight / total_bits
wheel_correction = sin(wheel_position × π / 180)
final_consensus = |base_consensus + wheel_correction| / 2
```

#### Space-Time Bound

The codec achieves O(1) space-time complexity through careful resource allocation:

```
space_complexity = O(½ log n)  // RB-AVL tree height
time_per_byte = O(¼ log n)     // Duplex encoding + pruning
auxiliary_space = O(1)          // Fixed buffer sizes
```

### File Format Specification

#### NSIGII Container Format

**Header (32 bytes)**:
```
Offset | Size | Field
-------|------|-------
0      | 8    | Magic: "NSIGII\0\0"
8      | 8    | Version: "7.0.0\0\0\0"
16     | 4    | Width (uint32)
20     | 4    | Height (uint32)
24     | 4    | Frame Count (uint32)
28     | 4    | Reserved
```

**Frame Structure**:
```
Offset | Size | Field
-------|------|-------
0      | 4    | Frame Size (uint32)
4      | N    | Compressed Frame Data
```

Each frame contains DEFLATE-compressed YUV420 data after passing through all three trident channels.

### Verification Properties

The codec provides the following verification guarantees:

1. **Hash Integrity**: SHA-256 verification at receiver channel
2. **RWX Permission Chain**: WRITE → READ → EXECUTE must be valid
3. **Discriminant Consensus**: Flash point (Δ = 0) confirms verification
4. **Wheel Continuity**: Position advances 0° → 120° → 240° → 360°
5. **Human Rights Tag**: "NSIGII_HR_TRANSMIT" tag preserved through pipeline

### Performance Characteristics

Based on the original codec example with 384×216 frames:

- **Raw Frame Size**: 248,832 bytes (RGB24)
- **YUV420 Conversion**: 50% reduction → 124,416 bytes
- **ROPEN Duplex**: 50% reduction → 62,208 bytes
- **DEFLATE Compression**: ~75% reduction → ~15,552 bytes
- **Total Compression**: ~93.75% reduction from raw

The trident verification adds approximately 5% overhead for the RB-AVL tree operations and discriminant calculations.

### Usage Example

```bash
# Encode video
cat input.rgb24 | go run main.go \
    --width 384 \
    --height 216 \
    --input video.rgb24 \
    --output encoded.nsigii

# Output shows:
# NSIGII Polygatic Video Codec v7.0.0
# Initializing trident channels...
# Encoding frames with trident verification...
# Encoded 256 frames...
# 
# === NSIGII Encoding Complete ===
# Frames encoded: 256
# Raw size: 63700992 bytes
# Encoded size: 3962562 bytes
# Compression ratio: 93.78%
# Trident channels: TRANSMIT → RECEIVE → VERIFY
# Flash verification: Discriminant-based
# Output file: encoded.nsigii
```

### Integration with Existing Systems

The NSIGII codec can integrate with standard video pipelines:

**FFmpeg Integration**:
```bash
ffmpeg -i input.mp4 -f rawvideo -pix_fmt rgb24 - | \
    go run main.go --input - --output video.nsigii
```

**Streaming Pipeline**:
```bash
# Producer
gstreamer-launch-1.0 videotestsrc ! videoconvert ! \
    video/x-raw,format=RGB,width=384,height=216 ! \
    fdsink | go run main.go --input -

# Consumer  
cat video.nsigii | decoder | ffplay -
```

### Security Considerations

The human rights verification protocol ensures:

1. **Non-repudiation**: Each frame is cryptographically linked through the RB-AVL tree
2. **Tamper Detection**: Discriminant verification fails if content is modified
3. **Access Control**: RWX permissions enforced at each channel
4. **Audit Trail**: Sequence tokens and timestamps preserved in packet headers

### Future Extensions

Potential enhancements to the codec include:

1. **Multi-threaded Channel Processing**: Parallel trident channels for real-time encoding
2. **GPU Acceleration**: CUDA/OpenCL for YUV conversion and spline interpolation
3. **Adaptive Bitrate**: Dynamic compression based on discriminant state
4. **Error Correction**: Reed-Solomon codes integrated with enzyme repair
5. **Network Streaming**: UDP/TCP transport with packet recovery

### References

- **Bipolar Sequence Theory**: NSIGII transcripts (30 Jan 2026)
- **Filter and Flash**: Cisco interdependence sequences
- **ROPEN Specification**: github.com/obinexus/ropen
- **Rectorial Reasoning**: Rational Wheel Framework (11 Feb 2026)
- **Trident Protocol**: NSIGII Command & Control specification

---

*"In ¼ log n time and ½ log n space, NSIGII encodes human rights into every frame—without ever vacating the verification chamber or dropping a zero."*
