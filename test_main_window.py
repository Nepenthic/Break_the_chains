"""
Unit tests for the main window UI components.
"""

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from main import CADCAMMainWindow
from shapes_3d import Cube, Sphere, Cylinder, ExtrudedShape

@pytest.fixture
def main_window(qtbot):
    """Create main window instance for tests."""
    window = CADCAMMainWindow()
    qtbot.addWidget(window)
    return window

def test_window_initialization(main_window):
    """Test main window initialization."""
    assert main_window.windowTitle() == "CAD/CAM Program"
    assert main_window.geometry().width() == 1200
    assert main_window.geometry().height() == 800
    
    # Check tab widget
    tab_widget = main_window.findChild(QTabWidget)
    assert tab_widget is not None
    assert tab_widget.count() == 5  # Shapes, Transform, Boolean, CAM, Constraints
    
    # Check viewport
    assert main_window.viewport is not None

def test_shape_creation(main_window, qtbot):
    """Test shape creation through the UI."""
    # Create a cube
    main_window.onShapeCreated("Cube", {"Width": 2.0, "Height": 1.0, "Depth": 1.0})
    assert len(main_window.viewport.scene_manager.shapes) == 1
    
    # Create a sphere
    main_window.onShapeCreated("Sphere", {"Radius": 1.0, "Segments": 32})
    assert len(main_window.viewport.scene_manager.shapes) == 2
    
    # Create a cylinder
    main_window.onShapeCreated("Cylinder", {"Radius": 1.0, "Height": 2.0, "Segments": 32})
    assert len(main_window.viewport.scene_manager.shapes) == 3
    
    # Create an extrusion
    main_window.onShapeCreated("Extrusion", {"Sides": 6, "Radius": 1.0, "Height": 2.0})
    assert len(main_window.viewport.scene_manager.shapes) == 4

def test_shape_selection(main_window, qtbot):
    """Test shape selection in the viewport."""
    # Create and add shapes
    cube = Cube(size=1.0)
    sphere = Sphere(radius=0.5)
    cube_id = main_window.viewport.addShape(cube)
    sphere_id = main_window.viewport.addShape(sphere)
    
    # Select first shape
    main_window.viewport.selectShape(cube_id)
    selected = main_window.viewport.scene_manager.get_selected_shape()
    assert selected is not None
    assert selected[0] == cube_id
    
    # Select second shape
    main_window.viewport.selectShape(sphere_id)
    selected = main_window.viewport.scene_manager.get_selected_shape()
    assert selected is not None
    assert selected[0] == sphere_id

def test_keyboard_shortcuts(main_window, qtbot):
    """Test keyboard shortcuts."""
    # Test transform mode shortcuts
    QTest.keyClick(main_window, Qt.Key_T)
    assert main_window.viewport.transform_mode == "translate"
    
    QTest.keyClick(main_window, Qt.Key_R)
    assert main_window.viewport.transform_mode == "rotate"
    
    QTest.keyClick(main_window, Qt.Key_S)
    assert main_window.viewport.transform_mode == "scale"
    
    # Test axis selection shortcuts
    QTest.keyClick(main_window, Qt.Key_Alt | Qt.Key_X)
    assert main_window.viewport.scene_manager.active_axis == "x"
    
    QTest.keyClick(main_window, Qt.Key_Alt | Qt.Key_Y)
    assert main_window.viewport.scene_manager.active_axis == "y"
    
    QTest.keyClick(main_window, Qt.Key_Alt | Qt.Key_Z)
    assert main_window.viewport.scene_manager.active_axis == "z"
    
    # Test snapping shortcut
    QTest.keyClick(main_window, Qt.Key_Control | Qt.Key_G)
    assert main_window.transform_tab.getSnapSettings()['enabled'] == True
    
    # Test cancel shortcut
    QTest.keyClick(main_window, Qt.Key_Escape)
    assert main_window.viewport.transform_mode is None

def test_undo_redo(main_window, qtbot):
    """Test undo/redo functionality."""
    # Create a shape
    cube = Cube(size=1.0)
    cube_id = main_window.viewport.addShape(cube)
    main_window.viewport.selectShape(cube_id)
    
    # Apply a transform
    main_window.onTransformApplied("translate", {
        "mode": "translate",
        "axis": "x",
        "value": 1.0
    })
    original_position = cube.transform.position.copy()
    
    # Undo transform
    main_window.undoTransform()
    assert np.allclose(cube.transform.position, original_position)
    
    # Redo transform
    main_window.redoTransform()
    assert cube.transform.position[0] == original_position[0] + 1.0

def test_status_messages(main_window, qtbot):
    """Test status message display."""
    # Test shape creation message
    main_window.onShapeCreated("Cube", {"Width": 1.0, "Height": 1.0, "Depth": 1.0})
    assert "Creating Cube" in main_window.viewport.status_message
    
    # Test transform message
    cube = Cube(size=1.0)
    cube_id = main_window.viewport.addShape(cube)
    main_window.viewport.selectShape(cube_id)
    main_window.onTransformApplied("translate", {
        "mode": "translate",
        "axis": "x",
        "value": 1.0
    })
    assert "Transform applied" in main_window.viewport.status_message
    
    # Test error message
    main_window.viewport.selectShape(None)  # Deselect
    main_window.onTransformApplied("translate", {
        "mode": "translate",
        "axis": "x",
        "value": 1.0
    })
    assert "No shape selected" in main_window.viewport.status_message

def test_tab_switching(main_window, qtbot):
    """Test tab switching behavior."""
    tab_widget = main_window.findChild(QTabWidget)
    
    # Switch to each tab
    for i in range(tab_widget.count()):
        tab_widget.setCurrentIndex(i)
        assert tab_widget.currentIndex() == i
        
        # Verify tab content is visible
        current_widget = tab_widget.currentWidget()
        assert current_widget.isVisible()
        assert current_widget.isEnabled()

def test_viewport_resize(main_window, qtbot):
    """Test viewport resize behavior."""
    # Get initial size
    initial_width = main_window.viewport.width()
    initial_height = main_window.viewport.height()
    
    # Resize window
    new_width = 1600
    new_height = 1000
    main_window.resize(new_width, new_height)
    
    # Verify viewport resized proportionally
    assert main_window.viewport.width() > initial_width
    assert main_window.viewport.height() > initial_height
    assert main_window.viewport.width() / main_window.viewport.height() == initial_width / initial_height

def test_shape_creation_validation(main_window, qtbot):
    """Test shape creation parameter validation."""
    # Test invalid parameters
    with pytest.raises(ValueError):
        main_window.onShapeCreated("Cube", {"Width": -1.0, "Height": 1.0, "Depth": 1.0})
    
    with pytest.raises(ValueError):
        main_window.onShapeCreated("Sphere", {"Radius": 0.0, "Segments": 32})
    
    with pytest.raises(ValueError):
        main_window.onShapeCreated("Cylinder", {"Radius": 1.0, "Height": -2.0, "Segments": 32})
    
    with pytest.raises(ValueError):
        main_window.onShapeCreated("Extrusion", {"Sides": 2, "Radius": 1.0, "Height": 2.0})

def test_transform_validation(main_window, qtbot):
    """Test transform parameter validation."""
    # Create and select a shape
    cube = Cube(size=1.0)
    cube_id = main_window.viewport.addShape(cube)
    main_window.viewport.selectShape(cube_id)
    
    # Test invalid transform parameters
    with pytest.raises(ValueError):
        main_window.onTransformApplied("translate", {
            "mode": "translate",
            "axis": "invalid",
            "value": 1.0
        })
    
    with pytest.raises(ValueError):
        main_window.onTransformApplied("rotate", {
            "mode": "rotate",
            "axis": "x",
            "value": 360.0  # Invalid rotation value
        })
    
    with pytest.raises(ValueError):
        main_window.onTransformApplied("scale", {
            "mode": "scale",
            "axis": "y",
            "value": 0.0  # Invalid scale value
        }) 