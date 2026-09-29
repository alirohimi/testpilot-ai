# Contributing to TestPilot AI

Thanks for your interest in contributing to TestPilot AI! This document provides guidelines and instructions.

## 🚀 Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/alirohimi/testpilot-ai.git`
3. Create a virtual environment: `python -m venv venv && source venv/bin/activate`
4. Install dependencies: `pip install -e ".[dev]"`
5. Run tests: `pytest`

## 📋 Development Workflow

### Code Style
- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where possible
- Run `black src tests` before committing
- Run `flake8 src tests` to check for style issues

### Testing
- Write tests for new features
- Run `pytest` to ensure all tests pass
- Aim for >80% code coverage

### Git Guidelines
- Use descriptive commit messages
- Reference issue numbers when applicable
- Create feature branches for each change

## 🤝 Contribution Steps

1. **Fork & Clone**: Create a fork and clone it locally
2. **Branch**: Create a feature branch (`git checkout -b feature/amazing-feature`)
3. **Code**: Make your changes
4. **Test**: Run tests and ensure they pass
5. **Commit**: Commit your changes (`git commit -m 'Add amazing feature'`)
6. **Push**: Push to your fork (`git push origin feature/amazing-feature`)
7. **PR**: Create a Pull Request

## 📝 Pull Request Process

1. Update documentation as needed
2. Add tests for new functionality
3. Ensure CI passes
4. Request review from maintainers
5. Squash commits if requested

## 🐛 Reporting Bugs

If you find a bug, please create an issue with:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Your environment (Python version, OS, etc.)

## 💡 Feature Requests

For feature requests, please:
1. Search existing issues first
2. Describe the use case
3. Explain how it aligns with project goals

## 📖 Documentation

- Keep README.md up to date
- Add docstrings to public functions/classes
- Update CHANGELOG.md with notable changes

## 🔒 Security

- Report security vulnerabilities privately
- Do not commit secrets or API keys
- Use environment variables for sensitive data

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
