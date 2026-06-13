# Contributing to FiOpt

Thank you for your interest in contributing to FiOpt! We welcome contributions of all forms, including bug fixes, feature requests, documentation improvements, and feedback.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Getting Started

### 1. Fork and Clone the Repository
Fork the repository on GitHub, and clone it locally:
```bash
git clone https://github.com/YOUR_USERNAME/fiops.git
cd fiops
```

### 2. Set Up a Virtual Environment
We recommend using a virtual environment (Python 3.10 or higher):
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies in Editable Mode
Install the package along with its development dependencies:
```bash
pip install -e .[dev]
```

---

## Running the Test Suite

Before making any changes, ensure all existing tests pass:
```bash
pytest
```

To run tests with verbose output:
```bash
pytest -v
```

All new features or bug fixes should include corresponding tests under the `tests/` directory.

---

## Coding Style & Standards

- **Type Hints**: We require type hints for all function arguments and return values.
- **Formatting**: Please format your code to comply with standard Python styles (like Black/PEP 8).
- **Docstrings**: Include descriptive docstrings for modules, classes, and public API methods.

---

## Creating a Pull Request

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/my-cool-feature
   ```
2. Implement your changes and write appropriate tests.
3. Verify that all tests pass:
   ```bash
   pytest
   ```
4. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "feat: add analysis support for generator expressions"
   ```
5. Push to your fork:
   ```bash
   git push origin feature/my-cool-feature
   ```
6. Open a Pull Request (PR) on GitHub against the `main` branch.
