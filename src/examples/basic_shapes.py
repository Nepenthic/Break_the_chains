"""
Example script demonstrating basic shape creation and manipulation.
"""

import os
from src.core.shapes import Cube, Sphere, Cylinder, Transform
import numpy as np

def main():
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Create a cube and export it
    cube = Cube(size=2.0)
    cube.translate(1.0, 0.0, 0.0)  # Move it right
    cube.export_stl("output/cube.stl")
    
    # Create a sphere and export it
    sphere = Sphere(radius=1.0)
    sphere.translate(-1.0, 0.0, 0.0)  # Move it left
    sphere.export_stl("output/sphere.stl")
    
    # Create a cylinder and export it
    cylinder = Cylinder(radius=0.5, height=3.0)
    # Rotate 90 degrees around X axis to make it lie down
    cylinder.rotate(np.pi/2, 0.0, 0.0)
    cylinder.export_stl("output/cylinder.stl")
    
    print("Shapes have been exported to the 'output' directory.")

if __name__ == "__main__":
    main() 