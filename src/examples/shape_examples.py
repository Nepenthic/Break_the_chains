"""
Comprehensive examples demonstrating shape creation, transformation, and export.
"""

import os
import numpy as np
from src.core.shapes import Cube, Sphere, Cylinder, Transform

def demonstrate_transformations():
    """Demonstrate various shape transformations."""
    # Create output directory
    os.makedirs("output/transforms", exist_ok=True)
    
    # Example 1: Cube with combined transformations
    print("\nExample 1: Cube with combined transformations")
    cube = Cube(size=2.0)
    # Rotate 45 degrees around Y axis
    cube.rotate(0.0, np.pi/4, 0.0)
    # Move up and right
    cube.translate(1.0, 2.0, 0.0)
    # Scale non-uniformly
    cube.scale(1.0, 2.0, 1.0)
    cube.export_stl("output/transforms/transformed_cube.stl")
    
    # Example 2: Sphere with precise positioning
    print("\nExample 2: Sphere with precise positioning")
    sphere = Sphere(radius=1.5)
    # Create a specific transform
    transform = Transform(
        position=np.array([1.0, 1.0, 1.0]),
        rotation=np.array([0.0, np.pi/6, 0.0]),  # 30 degrees around Y
        scale=np.array([1.0, 1.0, 1.0])
    )
    sphere = Sphere(radius=1.5, transform=transform)
    sphere.export_stl("output/transforms/positioned_sphere.stl")
    
    # Example 3: Cylinder sequence
    print("\nExample 3: Cylinder sequence")
    # Create three cylinders in different orientations
    cylinders = []
    for i in range(3):
        cylinder = Cylinder(radius=0.5, height=3.0)
        # Rotate around different axes
        if i == 0:
            cylinder.rotate(np.pi/2, 0.0, 0.0)  # Lying flat (X rotation)
        elif i == 1:
            cylinder.rotate(0.0, 0.0, np.pi/2)  # Standing up (Z rotation)
        # Third cylinder remains in default orientation
        
        # Position them side by side
        cylinder.translate(i * 4.0, 0.0, 0.0)
        cylinders.append(cylinder)
        cylinder.export_stl(f"output/transforms/cylinder_{i}.stl")

def demonstrate_shape_creation():
    """Demonstrate various ways to create and combine shapes."""
    os.makedirs("output/shapes", exist_ok=True)
    
    # Example 1: Creating shapes with different parameters
    print("\nExample 1: Basic shape creation")
    shapes = [
        Cube(size=1.0),
        Cube(size=2.0),
        Sphere(radius=1.0),
        Sphere(radius=0.5),
        Cylinder(radius=1.0, height=2.0),
        Cylinder(radius=0.5, height=3.0)
    ]
    
    # Position them in a grid
    for i, shape in enumerate(shapes):
        row = i // 3
        col = i % 3
        shape.translate(col * 3.0, row * 3.0, 0.0)
        shape.export_stl(f"output/shapes/shape_{i}.stl")

def main():
    """Run all demonstrations."""
    print("Starting shape creation and transformation demonstrations...")
    
    demonstrate_shape_creation()
    demonstrate_transformations()
    
    print("\nAll examples have been exported to the 'output' directory.")
    print("- Basic shapes are in 'output/shapes/'")
    print("- Transformed shapes are in 'output/transforms/'")

if __name__ == "__main__":
    main() 