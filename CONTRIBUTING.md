# Contributing to MindVoice

Thank you for your interest in contributing to MindVoice! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different viewpoints and experiences

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/mindvoice/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment information (OS, Python version, Node.js version)
   - Screenshots if applicable

### Suggesting Features

1. Check if the feature has already been suggested
2. Create a new issue with:
   - Clear description of the feature
   - Use cases and benefits
   - Possible implementation approach (if you have ideas)

### Submitting Pull Requests

1. **Fork the repository** and create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Follow the existing code style
   - Add comments for complex logic
   - Update documentation if needed
   - Add tests if applicable

3. **Test your changes**:
   - Ensure all existing tests pass
   - Test your new functionality
   - Test on different platforms if possible

4. **Commit your changes**:
   ```bash
   git commit -m "Add: description of your changes"
   ```
   Use clear, descriptive commit messages.

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Provide a clear description of your changes
   - Reference any related issues
   - Wait for review and address feedback

## Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/mindvoice.git
   cd mindvoice
   ```

2. Set up Python environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up Node.js environment:
   ```bash
   cd electron-app
   npm install
   ```

4. Copy configuration example:
   ```bash
   cp config.yml.example config.yml
   # Edit config.yml with your own credentials (if needed for testing)
   ```

## Code Style

### Python
- Follow PEP 8 style guide
- Use type hints where appropriate
- Keep functions focused and small
- Add docstrings for public functions/classes

### TypeScript/JavaScript
- Use ESLint configuration
- Follow React best practices
- Use TypeScript types
- Keep components focused and reusable

## Project Structure

- `src/` - Python backend code
- `electron-app/` - Electron frontend code
- `docs/` - Documentation
- `tests/` - Test files (if added)

## Adding New Features

### Adding a New ASR Provider

1. Create a new file in `src/providers/asr/`
2. Inherit from `ASRProvider` base class
3. Implement required methods
4. Add documentation
5. Update README if needed

### Adding a New Storage Provider

1. Create a new file in `src/providers/storage/`
2. Inherit from `StorageProvider` base class
3. Implement required methods
4. Add configuration options
5. Update documentation

## Testing

- Write tests for new features
- Ensure existing tests pass
- Test on multiple platforms when possible

## Documentation

- Update README.md if adding new features
- Add code comments for complex logic
- Update API documentation if changing interfaces
- Keep examples up to date

## Questions?

Feel free to open an issue for any questions or clarifications!

Thank you for contributing to MindVoice! 🎉

