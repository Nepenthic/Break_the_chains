import pytest
import numpy as np
from src.core.shapes import Cube, Sphere, Cylinder, Transform

def test_cube_creation():
    """Test creating a cube with default parameters."""
    cube = Cube()
    mesh = cube.get_mesh()
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0

def test_cube_size():
    """Test that cube size is correctly applied."""
    size = 2.0
    cube = Cube(size=size)
    mesh = cube.get_mesh()
    # Check that the bounding box has the correct dimensions
    bounds = mesh.bounds
    assert np.allclose(bounds[1] - bounds[0], [size] * 3)

def test_sphere_creation():
    """Test creating a sphere with default parameters."""
    sphere = Sphere()
    mesh = sphere.get_mesh()
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0

def test_sphere_radius():
    """Test that sphere radius is correctly applied."""
    radius = 2.0
    sphere = Sphere(radius=radius)
    mesh = sphere.get_mesh()
    # Check that all vertices are approximately radius distance from center
    distances = np.linalg.norm(mesh.vertices, axis=1)
    assert np.allclose(distances, radius, rtol=0.1)

def test_cylinder_creation():
    """Test creating a cylinder with default parameters."""
    cylinder = Cylinder()
    mesh = cylinder.get_mesh()
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0

def test_shape_transformations():
    """Test that transformations are correctly applied to shapes."""
    cube = Cube()
    
    # Test translation
    cube.translate(1.0, 2.0, 3.0)
    mesh = cube.get_mesh()
    center = mesh.centroid
    assert np.allclose(center, [1.0, 2.0, 3.0])
    
    # Test rotation (90 degrees around Y axis)
    cube = Cube()  # Start with fresh cube
    cube.rotate(0.0, np.pi/2, 0.0)
    mesh = cube.get_mesh()
    # A rotated cube should still have the same bounding box dimensions
    bounds = mesh.bounds
    assert np.allclose(bounds[1] - bounds[0], [1.0] * 3)
    
    # Test scaling
    cube = Cube()  # Start with fresh cube
    cube.scale(2.0, 2.0, 2.0)
    mesh = cube.get_mesh()
    bounds = mesh.bounds
    assert np.allclose(bounds[1] - bounds[0], [2.0] * 3) 