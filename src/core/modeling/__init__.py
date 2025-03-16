"""
Core 3D modeling module for solid and surface modeling operations.
"""

from .solid import (
    Solid,
    Extrusion,
    Revolution,
    Sweep,
    Loft,
    Shell,
    Draft,
    Fillet,
    Chamfer,
    Pattern,
    Mirror,
    Boolean
)

from .surface import (
    Surface,
    ExtrudedSurface,
    RevolvedSurface,
    LoftedSurface,
    FilledSurface,
    TrimmedSurface,
    ExtendedSurface,
    ThickenedSurface
)

from .assembly import (
    Assembly,
    Component,
    Mate,
    MateReference,
    SmartFastener
)

__all__ = [
    # Solid modeling
    'Solid',
    'Extrusion',
    'Revolution',
    'Sweep',
    'Loft',
    'Shell',
    'Draft',
    'Fillet',
    'Chamfer',
    'Pattern',
    'Mirror',
    'Boolean',
    
    # Surface modeling
    'Surface',
    'ExtrudedSurface',
    'RevolvedSurface',
    'LoftedSurface',
    'FilledSurface',
    'TrimmedSurface',
    'ExtendedSurface',
    'ThickenedSurface',
    
    # Assembly
    'Assembly',
    'Component',
    'Mate',
    'MateReference',
    'SmartFastener'
] 