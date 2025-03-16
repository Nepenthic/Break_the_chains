"""
Integration tests for the SceneManager class.
"""

import pytest
import numpy as np
from src.core.scene import SceneManager

def test_shape_creation():
    """Test creating different types of shapes in the scene."""
    scene = SceneManager()
    
    # Create a cube
    cube_params = {'size': 2.0}
    cube_id = scene.create_shape('cube', cube_params)
    assert cube_id is not None
    cube = scene.get_shape(cube_id)
    assert cube is not None
    
    # Create a sphere with transform
    sphere_params = {
        'radius': 1.0
    }
    transform = {
        'position': [1.0, 2.0, 3.0],
        'rotation': [0.0, 0.0, 0.0],
        'scale': [1.0, 1.0, 1.0]
    }
    sphere_id = scene.create_shape('sphere', sphere_params, transform)
    assert sphere_id is not None
    sphere = scene.get_shape(sphere_id)
    assert sphere is not None
    
    # Verify we can get all shapes
    shapes = scene.get_all_shapes()
    assert len(shapes) == 2
    shape_ids = [id for id, _ in shapes]
    assert cube_id in shape_ids
    assert sphere_id in shape_ids

def test_shape_selection():
    """Test shape selection functionality."""
    scene = SceneManager()
    
    # Create two shapes
    shape1_id = scene.create_shape('cube', {'size': 1.0})
    shape2_id = scene.create_shape('sphere', {'radius': 1.0})
    
    # Test selecting first shape
    assert scene.select_shape(shape1_id)
    selected = scene.get_selected_shape()
    assert selected is not None
    assert selected[0] == shape1_id
    
    # Test switching selection
    assert scene.select_shape(shape2_id)
    selected = scene.get_selected_shape()
    assert selected is not None
    assert selected[0] == shape2_id
    
    # Test clearing selection
    assert scene.select_shape(None)
    assert scene.get_selected_shape() is None
    
    # Test selecting non-existent shape
    assert not scene.select_shape("non-existent-id")

def test_shape_transformation():
    """Test applying transformations to shapes."""
    scene = SceneManager()
    
    # Create a cube
    cube_id = scene.create_shape('cube', {'size': 1.0})
    
    # Test translation
    scene.apply_transform(cube_id, 'translate', {'x': 1.0, 'y': 2.0, 'z': 3.0})
    cube = scene.get_shape(cube_id)
    assert np.allclose(cube.transform.position, [1.0, 2.0, 3.0])
    
    # Test rotation
    scene.apply_transform(cube_id, 'rotate', {'x': 0.0, 'y': np.pi/2, 'z': 0.0})
    cube = scene.get_shape(cube_id)
    assert np.allclose(cube.transform.rotation, [0.0, np.pi/2, 0.0])
    
    # Test scaling
    scene.apply_transform(cube_id, 'scale', {'x': 2.0, 'y': 2.0, 'z': 2.0})
    cube = scene.get_shape(cube_id)
    assert np.allclose(cube.transform.scale, [2.0, 2.0, 2.0])
    
    # Test invalid shape ID
    with pytest.raises(KeyError):
        scene.apply_transform("non-existent-id", 'translate', {'x': 1.0, 'y': 0.0, 'z': 0.0})

def test_shape_removal():
    """Test removing shapes from the scene."""
    scene = SceneManager()
    
    # Create and remove a shape
    shape_id = scene.create_shape('cube', {'size': 1.0})
    assert scene.remove_shape(shape_id)
    assert scene.get_shape(shape_id) is None
    
    # Test removing non-existent shape
    assert not scene.remove_shape("non-existent-id")
    
    # Test removing selected shape
    shape_id = scene.create_shape('sphere', {'radius': 1.0})
    scene.select_shape(shape_id)
    assert scene.remove_shape(shape_id)
    assert scene.get_selected_shape() is None

def test_extrusion_creation():
    """Test creating and manipulating extruded shapes."""
    scene = SceneManager()
    
    # Create rectangular extrusion
    rect_params = {
        'extrusion_type': 'rectangle',
        'width': 2.0,
        'length': 1.0,
        'height': 0.5
    }
    rect_id = scene.create_shape('extrusion', rect_params)
    assert rect_id is not None
    
    # Create polygon extrusion
    poly_params = {
        'extrusion_type': 'polygon',
        'num_sides': 6,
        'radius': 1.0,
        'height': 1.0
    }
    poly_id = scene.create_shape('extrusion', poly_params)
    assert poly_id is not None
    
    # Create custom profile extrusion
    custom_params = {
        'extrusion_type': 'custom',
        'profile_points': [[0,0], [1,0], [1,1], [0,1]],
        'height': 1.0
    }
    custom_id = scene.create_shape('extrusion', custom_params)
    assert custom_id is not None
    
    # Verify all shapes were created
    shapes = scene.get_all_shapes()
    assert len(shapes) == 3

def test_error_handling():
    """Test error handling in the SceneManager."""
    scene = SceneManager()
    
    # Test invalid shape type
    with pytest.raises(ValueError):
        scene.create_shape('invalid_type', {})
    
    # Test invalid parameters
    with pytest.raises(ValueError):
        scene.create_shape('cube', {'invalid_param': 1.0})
    
    # Test invalid transform type
    shape_id = scene.create_shape('cube', {'size': 1.0})
    with pytest.raises(ValueError):
        scene.apply_transform(shape_id, 'invalid_transform', {'x': 0, 'y': 0, 'z': 0})

def test_shape_export():
    """Test shape export functionality."""
    scene = SceneManager()
    
    # Create a shape
    shape_id = scene.create_shape('cube', {'size': 1.0})
    
    # Test successful export (note: requires write permissions)
    assert scene.export_shape_stl(shape_id, "test_cube.stl")
    
    # Test export with invalid shape ID
    assert not scene.export_shape_stl("non-existent-id", "test.stl") 