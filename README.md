# CAD/CAM Program

A Python-based CAD/CAM program for creating, manipulating, and exporting 3D models for CNC machining.

## Features (Planned)
- 3D shape creation (cubes, spheres, cylinders, extrusions)
- Shape manipulation (translation, rotation, scaling)
- 3D viewport controls
- STL export
- G-code generation for CNC machines

## Setup
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Project Structure
```
src/
├── core/           # Core functionality
│   ├── shapes/     # Shape creation and manipulation
│   ├── viewport/   # Viewport control logic
│   └── export/     # STL and G-code export
├── utils/          # Utility functions
└── tests/          # Test cases
```

## Development
- Follow PEP 8 style guide
- Write tests for new functionality
- Document code using docstrings
- Use type hints for better code clarity

## Testing
Run tests using pytest:
```bash
pytest
```