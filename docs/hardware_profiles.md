# Hardware Profiles and Performance Thresholds

## Overview
This document outlines the hardware profiling system used to adapt performance thresholds and optimize the transform system's behavior across different hardware configurations.

## Hardware Tiers

### Scoring System
Hardware is scored based on three main components:
- **CPU (40% weight)**:
  - Core count: Up to 5 points (4 cores = 5 points)
  - Frequency: Up to 5 points (3 GHz = 5 points)
  - Final CPU score = (core_score + frequency_score) / 2

- **RAM (30% weight)**:
  - 1 point per 2GB, capped at 10 points
  - Example: 8GB = 4 points

- **GPU (30% weight)**:
  - 1 point per 2GB VRAM, capped at 10 points
  - Integrated graphics or no GPU = 0 points

### Tier Classification
Total Score = (CPU_score × 0.4) + (RAM_score × 0.3) + (GPU_score × 0.3)

- **Low-end**: Score < 4.0
  - Typical specs: 2 cores, <2.0 GHz, 4GB RAM, integrated graphics
  - Use case: Basic transforms, limited scene complexity

- **Mid-range**: Score 4.0-7.0
  - Typical specs: 4 cores, 2.0-3.0 GHz, 8GB RAM, 2-4GB VRAM
  - Use case: Moderate scene complexity, regular transforms

- **High-end**: Score > 7.0
  - Typical specs: 8+ cores, >3.0 GHz, 16GB+ RAM, 4GB+ VRAM
  - Use case: Complex scenes, batch transforms, high FPS

## Performance Thresholds

### Frame Time Thresholds
- **Low-end**: 33.3ms (30 FPS)
- **Mid-range**: 20.0ms (50 FPS)
- **High-end**: 16.7ms (60 FPS)

### Memory Thresholds
- **Low-end**: 512MB
- **Mid-range**: 768MB
- **High-end**: 1024MB

### GPU Memory Thresholds
- **Low-end**: 512MB
- **Mid-range**: 1024MB
- **High-end**: 2048MB (adjusts up to 4GB based on available VRAM)

### Operation Thresholds
- **Batch Transform (per 100 shapes)**
  - Low-end: 50ms
  - Mid-range: 25ms
  - High-end: 16ms

- **Vertex Processing (per 1000 vertices)**
  - Low-end: 0.2ms
  - Mid-range: 0.1ms
  - High-end: 0.05ms

## Threshold Adjustments

### CPU Adjustments
When CPU cores > 8:
- Batch transform threshold reduced by 20%
- State capture threshold reduced by 20%

### GPU Adjustments
When GPU memory > 4GB:
- GPU memory threshold = min(50% of VRAM, 4GB)

## Testing Guidelines

### Required Test Configurations
1. **Low-end System**
   - CPU: Dual-core or low-frequency quad-core
   - RAM: 4GB or less
   - GPU: Integrated graphics

2. **Mid-range System**
   - CPU: Quad-core, 2.0-3.0 GHz
   - RAM: 8GB
   - GPU: 2-4GB VRAM

3. **High-end System**
   - CPU: 8+ cores, >3.0 GHz
   - RAM: 16GB+
   - GPU: 4GB+ VRAM

### Test Scenarios
1. **Basic Operations**
   - Single shape transforms
   - UI responsiveness
   - State capture/restore

2. **Complex Operations**
   - Batch transforms (50-500 shapes)
   - High-vertex meshes
   - Compound operations

3. **Resource Usage**
   - Memory growth
   - GPU memory utilization
   - CPU utilization

### Test Validation
1. **Performance Metrics**
   - Frame times within tier threshold
   - Operation times within limits
   - Resource usage within bounds

2. **Warning System**
   - Verify warnings trigger appropriately
   - Check warning details and thresholds
   - Validate recommendation system

3. **State Management**
   - Verify checkpoints include hardware info
   - Test state restore across configurations
   - Validate performance correlation

## Troubleshooting

### Common Issues
1. **Frame Time Spikes**
   - Check for background processes
   - Verify GPU driver status
   - Monitor thermal throttling

2. **Memory Issues**
   - Enable aggressive GC for low memory
   - Check for memory leaks
   - Monitor paging/swap usage

3. **GPU Issues**
   - Verify driver compatibility
   - Check for GPU memory fragmentation
   - Consider software rendering fallback

### Performance Optimization Tips
1. **Low-end Systems**
   - Reduce batch operation size
   - Enable aggressive cleanup
   - Use simplified meshes

2. **Mid-range Systems**
   - Balance batch sizes
   - Monitor resource usage
   - Adjust thresholds as needed

3. **High-end Systems**
   - Maximize parallel operations
   - Use full GPU capabilities
   - Enable advanced features

## Reporting Issues
When reporting performance issues:
1. Include full hardware profile log
2. Attach performance metrics summary
3. Describe test scenario and steps
4. Include any warning messages
5. Note system environment details 