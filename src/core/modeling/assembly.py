"""
Assembly management system for handling multi-part assemblies.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union
import numpy as np
from .solid import Solid

@dataclass
class MateReference:
    """Reference geometry for mating components."""
    type: str  # 'face', 'edge', 'vertex', 'axis', 'plane'
    geometry_id: int
    transform: np.ndarray = field(default_factory=lambda: np.eye(4))
    parent: Optional['Component'] = None

    def get_transform(self) -> np.ndarray:
        """Get the global transform of this reference."""
        if self.parent:
            return self.parent.get_global_transform() @ self.transform
        return self.transform

@dataclass
class Mate:
    """Defines a constraint between two components."""
    type: str  # 'coincident', 'concentric', 'perpendicular', 'parallel', 'tangent', etc.
    ref1: MateReference
    ref2: MateReference
    offset: float = 0.0
    angle: float = 0.0
    
    def is_valid(self) -> bool:
        """Check if the mate constraint is valid."""
        valid_mates = {
            'coincident': [
                ('face', 'face'),
                ('vertex', 'vertex'),
                ('vertex', 'edge'),
                ('vertex', 'face')
            ],
            'concentric': [
                ('axis', 'axis'),
                ('circle', 'circle'),
                ('circle', 'axis')
            ],
            'perpendicular': [
                ('axis', 'axis'),
                ('face', 'face'),
                ('edge', 'edge')
            ],
            'parallel': [
                ('axis', 'axis'),
                ('face', 'face'),
                ('edge', 'edge')
            ],
            'tangent': [
                ('face', 'face'),
                ('circle', 'face'),
                ('cylinder', 'face')
            ]
        }
        
        if self.type not in valid_mates:
            return False
            
        ref_types = (self.ref1.type, self.ref2.type)
        return ref_types in valid_mates[self.type]

@dataclass
class SmartFastener:
    """Intelligent fastener that adapts to assembly context."""
    type: str  # 'bolt', 'screw', 'pin', etc.
    size: str  # Standard size designation
    length: float
    material: str
    thread_spec: Optional[str] = None
    clearance_hole: bool = True
    
    def create_geometry(self, mate_ref: MateReference) -> Solid:
        """Create the fastener geometry based on context."""
        # TODO: Implement fastener geometry creation
        pass
    
    def validate_fit(self, hole_diameter: float, material_thickness: float) -> bool:
        """Validate fastener specifications against usage context."""
        # TODO: Implement fit validation
        pass

@dataclass
class Component:
    """A component in an assembly."""
    name: str
    solid: Solid
    transform: np.ndarray = field(default_factory=lambda: np.eye(4))
    parent: Optional['Assembly'] = None
    mate_references: Dict[str, MateReference] = field(default_factory=dict)
    
    def add_mate_reference(self, name: str, mate_ref: MateReference) -> None:
        """Add a mate reference to the component."""
        mate_ref.parent = self
        self.mate_references[name] = mate_ref
    
    def get_mate_reference(self, name: str) -> Optional[MateReference]:
        """Get a mate reference by name."""
        return self.mate_references.get(name)
    
    def get_global_transform(self) -> np.ndarray:
        """Get the global transformation matrix."""
        if self.parent:
            return self.parent.get_global_transform() @ self.transform
        return self.transform
    
    def update_transform(self, matrix: np.ndarray) -> None:
        """Update the component's transformation."""
        self.transform = matrix
        self.solid.apply_transform(matrix)

@dataclass
class Assembly:
    """Manages a collection of components and their relationships."""
    name: str
    components: Dict[str, Component] = field(default_factory=dict)
    mates: List[Mate] = field(default_factory=list)
    sub_assemblies: Dict[str, 'Assembly'] = field(default_factory=dict)
    transform: np.ndarray = field(default_factory=lambda: np.eye(4))
    parent: Optional['Assembly'] = None
    
    def add_component(self, name: str, component: Component) -> None:
        """Add a component to the assembly."""
        component.parent = self
        self.components[name] = component
    
    def add_sub_assembly(self, name: str, assembly: 'Assembly') -> None:
        """Add a sub-assembly."""
        assembly.parent = self
        self.sub_assemblies[name] = assembly
    
    def add_mate(self, mate: Mate) -> bool:
        """Add a mate constraint between components."""
        if mate.is_valid():
            self.mates.append(mate)
            return True
        return False
    
    def get_global_transform(self) -> np.ndarray:
        """Get the global transformation matrix."""
        if self.parent:
            return self.parent.get_global_transform() @ self.transform
        return self.transform
    
    def solve_mates(self) -> bool:
        """Solve all mate constraints in the assembly."""
        # TODO: Implement constraint solving
        # This will involve:
        # 1. Building a graph of components and constraints
        # 2. Detecting and handling circular dependencies
        # 3. Solving the constraint system
        # 4. Updating component transforms
        return True
    
    def explode_view(self, distance: float = 1.0) -> Dict[str, np.ndarray]:
        """Generate transforms for exploded view."""
        exploded_transforms = {}
        center = np.zeros(3)
        
        # Calculate assembly center
        for name, component in self.components.items():
            center += component.solid.get_center_of_mass()
        if self.components:
            center /= len(self.components)
            
        # Generate exploded transforms
        for name, component in self.components.items():
            direction = component.solid.get_center_of_mass() - center
            if np.any(direction):
                direction = direction / np.linalg.norm(direction)
            else:
                direction = np.array([1.0, 0.0, 0.0])
                
            translation = np.eye(4)
            translation[:3, 3] = direction * distance
            exploded_transforms[name] = translation
            
        return exploded_transforms
    
    def get_bill_of_materials(self) -> List[Dict[str, Union[str, int]]]:
        """Generate bill of materials."""
        bom = []
        component_counts = {}
        
        # Count components
        for name, component in self.components.items():
            if component.solid.name in component_counts:
                component_counts[component.solid.name] += 1
            else:
                component_counts[component.solid.name] = 1
                
        # Generate BOM entries
        for name, count in component_counts.items():
            bom.append({
                'name': name,
                'quantity': count,
                'material': 'Unknown',  # TODO: Add material property to Solid
                'part_number': 'TBD'    # TODO: Add part numbering system
            })
            
        # Include sub-assemblies
        for sub_assembly in self.sub_assemblies.values():
            bom.extend(sub_assembly.get_bill_of_materials())
            
        return bom
    
    def validate_assembly(self) -> Tuple[bool, List[str]]:
        """Validate the assembly configuration."""
        issues = []
        
        # Check for missing components referenced by mates
        referenced_components = set()
        for mate in self.mates:
            if mate.ref1.parent and mate.ref1.parent.name not in self.components:
                issues.append(f"Mate references missing component: {mate.ref1.parent.name}")
            if mate.ref2.parent and mate.ref2.parent.name not in self.components:
                issues.append(f"Mate references missing component: {mate.ref2.parent.name}")
                
        # Check for interference
        # TODO: Implement interference checking using trimesh
        
        # Validate sub-assemblies
        for name, sub_assembly in self.sub_assemblies.items():
            valid, sub_issues = sub_assembly.validate_assembly()
            if not valid:
                issues.extend([f"Sub-assembly {name}: {issue}" for issue in sub_issues])
                
        return len(issues) == 0, issues 