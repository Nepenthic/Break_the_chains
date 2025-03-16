# Frontend-Backend Interface Specification

## Overview
This document outlines the interface between the frontend UI and backend shape management system for our CAD/CAM program. It defines the data structures, events, and methods for communication between the two components.

## Core Components

### 1. Shape Management
The backend provides a `SceneManager` class that handles all shape-related operations. The frontend interacts with this through well-defined events and data structures.

### 2. Data Structures

#### Shape Parameters
```typescript
interface ShapeParameters {
    // Common parameters
    transform?: {
        position: [number, number, number];  // [x, y, z] in world units
        rotation: [number, number, number];  // [x, y, z] in radians
        scale: [number, number, number];     // [x, y, z] scale factors
    };
    
    // Basic shape parameters
    size?: number;          // Cube: length of each side
    radius?: number;        // Sphere/Cylinder: radius
    height?: number;        // Cylinder/Extrusion: height
    
    // Extrusion-specific parameters
    width?: number;         // Rectangle extrusion: width
    length?: number;        // Rectangle extrusion: length
    num_sides?: number;     // Polygon extrusion: number of sides
    profile_points?: [number, number][];  // Custom extrusion: 2D points
    extrusion_type?: 'rectangle' | 'polygon' | 'custom';
}
```

#### Transform Parameters
```typescript
interface TransformParameters {
    x: number;
    y: number;
    z: number;
}
```

#### Mesh Data (for Viewport)
```typescript
interface MeshData {
    vertices: Float32Array;    // Flattened array of vertex positions [x1,y1,z1,x2,y2,z2,...]
    faces: Uint32Array;        // Flattened array of triangle indices [i1,i2,i3,i4,i5,i6,...]
    normals?: Float32Array;    // Optional vertex normals [nx1,ny1,nz1,nx2,ny2,nz2,...]
}
```

### 3. Events and Methods

#### Shape Creation
```typescript
interface ShapeCreatedEvent {
    shape_type: 'cube' | 'sphere' | 'cylinder' | 'extrusion';
    parameters: ShapeParameters;
}

// Frontend -> Backend
function createShape(event: ShapeCreatedEvent): string;  // Returns shape_id

// Backend -> Frontend
function onShapeCreated(shape_id: string, meshData: MeshData): void;
```

#### Shape Transformation
```typescript
interface TransformAppliedEvent {
    shape_id: string;
    transform_type: 'translate' | 'rotate' | 'scale';
    parameters: TransformParameters;
}

// Frontend -> Backend
function applyTransform(event: TransformAppliedEvent): void;

// Backend -> Frontend
function onShapeTransformed(shape_id: string, meshData: MeshData): void;
```

#### Shape Selection
```typescript
interface ShapeSelectedEvent {
    shape_id: string | null;  // null to clear selection
}

// Frontend -> Backend
function selectShape(event: ShapeSelectedEvent): boolean;

// Backend -> Frontend
function onShapeSelected(shape_id: string | null): void;
```

#### Shape Export
```typescript
interface ExportRequestedEvent {
    shape_id: string;
    filepath: string;
    format: 'stl';  // Add more formats as needed
}

// Frontend -> Backend
function exportShape(event: ExportRequestedEvent): Promise<boolean>;
```

## Implementation Details

### 1. Coordinate System
- Right-handed coordinate system
- Y-axis up
- Units in meters
- Rotations in radians, applied in XYZ order

### 2. Viewport Integration
The backend provides mesh data for each shape in a format suitable for WebGL rendering:
```python
# Example mesh data generation
def get_shape_mesh_data(shape_id: str) -> MeshData:
    shape = scene_manager.get_shape(shape_id)
    mesh = shape.get_mesh()
    return {
        'vertices': mesh.vertices.flatten(),
        'faces': mesh.faces.flatten(),
        'normals': mesh.vertex_normals.flatten()
    }
```

### 3. Error Handling
- All methods return Promises or throw typed errors
- Error types include:
  - `ShapeNotFoundError`
  - `InvalidParametersError`
  - `TransformError`
  - `ExportError`

### 4. Performance Considerations
- Mesh data is transferred only when shapes are created or transformed
- Large meshes (>100k vertices) should be simplified before transfer
- Consider implementing a worker thread for heavy computations

## Example Usage

```typescript
// Creating a shape
const cubeId = await createShape({
    shape_type: 'cube',
    parameters: {
        size: 2.0,
        transform: {
            position: [1.0, 0.0, 0.0],
            rotation: [0.0, Math.PI/4, 0.0],
            scale: [1.0, 1.0, 1.0]
        }
    }
});

// Applying a transformation
await applyTransform({
    shape_id: cubeId,
    transform_type: 'rotate',
    parameters: { x: 0, y: Math.PI/2, z: 0 }
});

// Exporting a shape
const success = await exportShape({
    shape_id: cubeId,
    filepath: 'output/cube.stl',
    format: 'stl'
});
```

## Next Steps
1. Review and finalize this interface specification
2. Implement basic shape creation and viewport rendering
3. Add transformation support
4. Implement shape selection and highlighting
5. Add export functionality

## Questions for Discussion
1. Should we use a different format for mesh data transfer?
2. Do we need additional events for error handling?
3. Should transformations be relative or absolute?
4. How should we handle undo/redo operations? 