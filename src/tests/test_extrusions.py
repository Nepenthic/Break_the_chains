"""
Tests for the ExtrudedShape class and its functionality.
"""

import pytest
import numpy as np
from src.core.shapes import ExtrudedShape, Transform

def test_basic_rectangle_creation():
    """Test creating a basic rectangular extrusion."""
    rectangle = ExtrudedShape.create_rectangle(width=2.0, length=1.0, height=0.5)
    mesh = rectangle.get_mesh()
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    # Check dimensions
    bounds = mesh.bounds
    dimensions = bounds[1] - bounds[0]
    assert np.allclose(dimensions, [2.0, 1.0, 0.5])

def test_polygon_different_sides():
    """Test creating polygons with different numbers of sides."""
    # Test odd and even numbers of sides
    for sides in [3, 5, 7, 8]:
        polygon = ExtrudedShape.create_polygon(
            num_sides=sides,
            radius=1.0,
            height=1.0
        )
        mesh = polygon.get_mesh()
        # Verify number of vertices matches sides
        # Each side has 2 vertices (top and bottom)
        assert len(mesh.vertices) == sides * 2
        # Number of faces should be: sides (for sides) + 2 * (sides-2) (for top/bottom)
        assert len(mesh.faces) == sides * 2 + 2 * (sides - 2)

def test_concave_shape():
    """Test creating an extrusion with a concave (non-convex) profile."""
    # Create a simple concave shape (U-shaped)
    profile_points = [
        [0.0, 0.0],
        [3.0, 0.0],
        [3.0, 1.0],
        [2.0, 1.0],
        [2.0, 2.0],
        [1.0, 2.0],
        [1.0, 1.0],
        [0.0, 1.0]
    ]
    shape = ExtrudedShape(profile_points=profile_points, height=1.0)
    mesh = shape.get_mesh()
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    # Verify the mesh is watertight
    assert mesh.is_watertight

def test_star_shape():
    """Test creating a star-shaped extrusion (complex concave shape)."""
    num_points = 5
    outer_radius = 1.0
    inner_radius = 0.4
    
    angles = np.linspace(0, 2*np.pi, num_points*2, endpoint=False)
    radii = [outer_radius if i % 2 == 0 else inner_radius 
             for i in range(len(angles))]
    x = np.cos(angles) * radii
    y = np.sin(angles) * radii
    
    star = ExtrudedShape(
        profile_points=np.column_stack([x, y]).tolist(),
        height=0.3
    )
    mesh = star.get_mesh()
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight

def test_profile_auto_closing():
    """Test that open profiles are automatically closed."""
    # Create an open profile (first and last points don't match)
    profile_points = [
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0]  # Not explicitly closed
    ]
    shape = ExtrudedShape(profile_points=profile_points, height=1.0)
    mesh = shape.get_mesh()
    # Verify the mesh is watertight (implies profile was closed)
    assert mesh.is_watertight

def test_invalid_profile():
    """Test that invalid profiles raise appropriate errors."""
    # Test with 3D points (should fail)
    with pytest.raises(ValueError):
        ExtrudedShape([[0, 0, 0], [1, 1, 1]], height=1.0)
    
    # Test with empty profile
    with pytest.raises(ValueError):
        ExtrudedShape([], height=1.0)

def test_transformations():
    """Test applying transformations to extruded shapes."""
    rectangle = ExtrudedShape.create_rectangle(
        width=1.0,
        length=2.0,
        height=0.5
    )
    
    # Test translation
    rectangle.translate(1.0, 2.0, 3.0)
    mesh = rectangle.get_mesh()
    center = mesh.centroid
    assert np.allclose(center, [1.0, 2.0, 3.0])
    
    # Test rotation (90 degrees around Y)
    rectangle = ExtrudedShape.create_rectangle(
        width=1.0,
        length=2.0,
        height=0.5
    )
    rectangle.rotate(0.0, np.pi/2, 0.0)
    mesh = rectangle.get_mesh()
    # After 90-degree Y rotation, width and height dimensions should swap
    bounds = mesh.bounds
    dimensions = bounds[1] - bounds[0]
    assert np.allclose(dimensions[::2], [1.0, 0.5])  # X and Z dimensions
    
    # Test scaling
    rectangle = ExtrudedShape.create_rectangle(
        width=1.0,
        length=2.0,
        height=0.5
    )
    rectangle.scale(2.0, 1.0, 3.0)
    mesh = rectangle.get_mesh()
    bounds = mesh.bounds
    dimensions = bounds[1] - bounds[0]
    assert np.allclose(dimensions, [2.0, 2.0, 1.5])

def test_centering():
    """Test the centering option for extruded shapes."""
    # Create a shape with centering enabled
    centered = ExtrudedShape.create_rectangle(
        width=2.0,
        length=2.0,
        height=1.0,
        center=True
    )
    centered_mesh = centered.get_mesh()
    assert np.allclose(centered_mesh.centroid, [0, 0, 0])
    
    # Create a shape with centering disabled
    uncentered = ExtrudedShape.create_rectangle(
        width=2.0,
        length=2.0,
        height=1.0,
        center=False
    )
    uncentered_mesh = uncentered.get_mesh()
    # The shape should start from origin and extend in positive directions
    bounds = uncentered_mesh.bounds
    assert np.allclose(bounds[0], [0, 0, 0])  # Min bounds at origin
    assert np.allclose(bounds[1], [2.0, 2.0, 1.0])  # Max bounds at dimensions 