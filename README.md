# Break the Chains - Modern CAD System

A powerful, open-source CAD (Computer-Aided Design) system built with modern software engineering practices and a focus on user experience.

## Features

### CAD Features
- Parametric 2D sketching
  - Points, lines, circles, arcs, and splines
  - Geometric constraints (coincident, parallel, perpendicular, etc.)
  - Dynamic preview while drawing
  - Constraint solver for maintaining relationships
- Robust 3D modeling operations (Coming Soon)
  - Extrusion
  - Revolution
  - Sweep
  - Loft
  - Boolean operations
- Advanced assembly management (Coming Soon)
  - Component placement
  - Mate constraints
  - Assembly validation
  - Bill of materials

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/break_the_chains.git
cd break_the_chains
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Development Setup

1. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Set up pre-commit hooks:
```bash
pre-commit install
```

3. Run tests:
```bash
pytest
```

## Project Structure

```
break_the_chains/
├── src/
│   ├── core/           # Core CAD functionality
│   │   ├── sketch.py   # Sketch entities and constraints
│   │   └── model.py    # 3D modeling operations
│   ├── ui/             # User interface components
│   │   ├── main_window.py
│   │   └── sketch_view.py
│   └── main.py         # Application entry point
├── tests/              # Test suite
├── docs/               # Documentation
├── requirements.txt    # Project dependencies
└── README.md          # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Design Philosophy

- **Robustness**: Built with modern software engineering practices, including comprehensive testing and error handling.
- **User-Centric**: Focus on intuitive interfaces and workflows that enhance productivity.
- **Extensibility**: Modular architecture that makes it easy to add new features.
- **Performance**: Optimized for smooth operation with large assemblies and complex models.
- **Open Standards**: Support for industry-standard file formats and interoperability.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- PyQt6 for the GUI framework
- NumPy for numerical computations
- The open-source CAD/CAM community for inspiration and guidance