"""
Examples demonstrating the extrusion functionality.
"""

import os
import numpy as np
from src.core.shapes import ExtrudedShape, Transform

def demonstrate_extrusions():
    """Demonstrate various extrusion capabilities."""
    # Create output directory
    os.makedirs("output/extrusions", exist_ok=True)
    
    # Example 1: Simple rectangular extrusion
    print("\nExample 1: Rectangular extrusion")
    rectangle = ExtrudedShape.create_rectangle(
        width=2.0,
        length=1.0,
        height=0.5
    )
    rectangle.export_stl("output/extrusions/rectangle.stl")
    
    # Example 2: Regular polygon extrusions
    print("\nExample 2: Regular polygon extrusions")
    # Create various regular polygons
    for sides in [3, 4, 6, 8]:
        polygon = ExtrudedShape.create_polygon(
            num_sides=sides,
            radius=1.0,
            height=0.5
        )
        # Move each polygon along X axis
        polygon.translate((sides - 3) * 3.0, 0.0, 0.0)
        polygon.export_stl(f"output/extrusions/polygon_{sides}_sides.stl")
    
    # Example 3: Custom profile extrusion
    print("\nExample 3: Custom profile extrusion")
    # Create a star-like shape
    num_points = 5
    outer_radius = 1.0
    inner_radius = 0.4
    
    angles = np.linspace(0, 2*np.pi, num_points*2, endpoint=False)
    radii = [outer_radius if i % 2 == 0 else inner_radius for i in range(len(angles))]
    x = np.cos(angles) * radii
    y = np.sin(angles) * radii
    
    star = ExtrudedShape(
        profile_points=np.column_stack([x, y]).tolist(),
        height=0.3,
        center=True
    )
    # Rotate it slightly for better visualization
    star.rotate(0.0, np.pi/6, 0.0)
    star.export_stl("output/extrusions/star.stl")
    
    # Example 4: Transformed extrusion
    print("\nExample 4: Transformed extrusion")
    # Create an L-shaped profile
    l_profile = [
        [0.0, 0.0],
        [2.0, 0.0],
        [2.0, 0.5],
        [0.5, 0.5],
        [0.5, 2.0],
        [0.0, 2.0]
    ]
    
    # Create with an initial transform
    transform = Transform(
        position=np.array([1.0, 1.0, 0.0]),
        rotation=np.array([0.0, np.pi/4, 0.0]),  # 45 degrees around Y
        scale=np.array([1.0, 1.0, 1.0])
    )
    
    l_shape = ExtrudedShape(
        profile_points=l_profile,
        height=1.0,
        transform=transform
    )
    l_shape.export_stl("output/extrusions/l_shape.stl")

def main():
    """Run all extrusion demonstrations."""
    print("Starting extrusion demonstrations...")
    demonstrate_extrusions()
    print("\nAll examples have been exported to 'output/extrusions/'")

if __name__ == "__main__":
    main() 