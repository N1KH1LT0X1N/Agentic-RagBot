# Contributing to MediGuard AI RAG-Helper

First off, thank you for considering contributing to MediGuard AI! It's people like you that make this project better for everyone.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

### Our Standards

- **Be Respectful**: Treat everyone with respect
- **Be Collaborative**: Work together effectively
- **Be Professional**: Maintain professionalism at all times
- **Be Inclusive**: Welcome diverse perspectives and backgrounds

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- A GitHub account
- FREE API key from Groq or Google Gemini

### First Contribution

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/RagBot.git
   cd RagBot
   ```
3. **Set up development environment** (see below)
4. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## How Can I Contribute?

### 🐛 Reporting Bugs

**Before submitting a bug report:**
- Check the [existing issues](https://github.com/yourusername/RagBot/issues)
- Ensure you're using the latest version
- Collect relevant information (Python version, OS, error messages)

**How to submit a good bug report:**
- Use a clear and descriptive title
- Describe the exact steps to reproduce
- Provide specific examples
- Describe the behavior you observed and what you expected
- Include screenshots if applicable
- Include your environment details

**Template:**
```markdown
## Bug Description
[Clear description of the bug]

## Steps to Reproduce
1. 
2. 
3. 

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- OS: [e.g., Windows 11, macOS 14, Ubuntu 22.04]
- Python Version: [e.g., 3.11.5]
- MediGuard Version: [e.g., 1.0.0]

## Additional Context
[Any other relevant information]
```

### 💡 Suggesting Enhancements

**Before submitting an enhancement suggestion:**
- Check if it's already been suggested
- Determine which part of the project it relates to
- Consider if it aligns with the project's goals

**How to submit a good enhancement suggestion:**
- Use a clear and descriptive title
- Provide a detailed description of the proposed enhancement
- Explain why this enhancement would be useful
- List potential benefits and drawbacks
- Provide examples or mockups if applicable

### 🔨 Pull Requests

**Good first issues:**
- Look for issues labeled `good first issue`
- Documentation improvements
- Test coverage improvements
- Bug fixes

**Areas needing contribution:**
- Additional biomarker support
- Disease model improvements
- Performance optimizations
- Documentation enhancements
- Test coverage
- UI/UX improvements

## Development Setup

### 1. Fork and Clone

```bash
# Fork via GitHub UI, then:
git clone https://github.com/your-username/RagBot.git
cd RagBot
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies
pip install pytest pytest-cov black flake8 mypy
```

### 4. Configure Environment

```bash
cp .env.template .env
# Edit .env with your API keys
```

### 5. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_basic.py
```

## Style Guidelines

### Python Code Style

We follow **PEP 8** with some modifications:

- **Line length**: 100 characters maximum
- **Imports**: Organized with `isort`
- **Formatting**: Automated with `black`
- **Type hints**: Required for function signatures
- **Docstrings**: Google style

### Code Formatting

**Before committing, run:**

```bash
# Auto-format code
black src/ scripts/ tests/

# Check style compliance
flake8 src/ scripts/ tests/

# Type checking
mypy src/

# Import sorting
isort src/ scripts/ tests/
```

### Docstring Example

```python
def analyze_biomarkers(
    biomarkers: Dict[str, float],
    patient_context: Optional[Dict[str, Any]] = None
) -> AnalysisResult:
    """
    Analyze patient biomarkers and generate clinical insights.
    
    Args:
        biomarkers: Dictionary of biomarker names to values
        patient_context: Optional patient demographic information
        
    Returns:
        AnalysisResult containing predictions and recommendations
        
    Raises:
        ValueError: If biomarkers dictionary is empty
        ValidationError: If biomarker values are invalid
        
    Example:
        >>> result = analyze_biomarkers({"Glucose": 185, "HbA1c": 8.2})
        >>> print(result.prediction.disease)
        'Diabetes'
    """
    pass
```

### Testing Guidelines

- **Write tests** for all new features
- **Maintain coverage** above 80%
- **Test edge cases** and error conditions
- **Use descriptive test names**

**Test Example:**

```python
def test_biomarker_validation_with_critical_high_glucose():
    """Test that critically high glucose values trigger safety alerts."""
    validator = BiomarkerValidator()
    biomarkers = {"Glucose": 400}  # Critically high
    
    flags, alerts = validator.validate_all(biomarkers)
    
    assert len(alerts) > 0
    assert any("critical" in alert.message.lower() for alert in alerts)
```

## Commit Messages

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```bash
# Good commit messages
git commit -m "feat(agents): add liver disease detection agent"
git commit -m "fix(validation): correct hemoglobin range for females"
git commit -m "docs: update API documentation with new endpoints"
git commit -m "test: add integration tests for workflow"

# Bad commit messages (avoid these)
git commit -m "fixed stuff"
git commit -m "updates"
git commit -m "WIP"
```

## Pull Request Process

### Before Submitting

1. ✅ **Update your branch** with latest main
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-feature-branch
   git rebase main
   ```

2. ✅ **Run all tests** and ensure they pass
   ```bash
   pytest
   ```

3. ✅ **Format your code**
   ```bash
   black src/ scripts/ tests/
   flake8 src/ scripts/ tests/
   ```

4. ✅ **Update documentation** if needed
   - README.md
   - Docstrings
   - API documentation

5. ✅ **Add/update tests** for your changes

### Submitting the PR

1. **Push to your fork**
   ```bash
   git push origin your-feature-branch
   ```

2. **Create pull request** via GitHub UI

3. **Fill out the PR template** completely

### PR Template

```markdown
## Description
[Clear description of what this PR does]

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #[issue number]

## Testing
- [ ] All tests pass locally
- [ ] Added new tests for changes
- [ ] Updated existing tests

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
```

### Review Process

1. **Automated checks** must pass (if configured)
2. **Code review** by maintainer(s)
3. **Address feedback** if requested
4. **Approval** from maintainer
5. **Merge** by maintainer

### After Merge

- Delete your feature branch
- Update your fork's main branch
- Celebrate! 🎉

## Project Structure

Understanding the codebase:

```
src/
├── agents/          # Specialist agent implementations
├── evaluation/      # Quality evaluation framework
├── evolution/       # Self-improvement engine
├── biomarker_validator.py  # Validation logic
├── config.py        # Configuration classes
├── llm_config.py    # LLM setup
├── pdf_processor.py # Vector store management
├── state.py         # State definitions
└── workflow.py      # Main workflow orchestration
```

## Development Tips

### Local Testing

```bash
# Test specific component
python -c "from src.biomarker_validator import BiomarkerValidator; v = BiomarkerValidator(); print('OK')"

# Test workflow initialization
python -c "from src.workflow import create_guild; guild = create_guild(); print('Guild OK')"

# Test chat interface
python scripts/chat.py
```

### Debugging

- Use `print()` statements liberally during development
- Set `LANGCHAIN_TRACING_V2="true"` for LLM call tracing
- Check logs in the console output
- Use Python debugger: `import pdb; pdb.set_trace()`

### Common Issues

**Import errors:**
- Ensure you're in the project root directory
- Check virtual environment is activated

**API errors:**
- Verify API keys in `.env`
- Check rate limits haven't been exceeded

**Vector store errors:**
- Ensure FAISS indices exist in `data/vector_stores/`
- Run `python src/pdf_processor.py` to rebuild if needed

## Questions?

- **General questions**: Open a GitHub Discussion
- **Bug reports**: Open a GitHub Issue
- **Security concerns**: Email maintainers directly

## Recognition

Contributors will be recognized in:
- Project README
- Release notes
- Special mentions for significant contributions

Thank you for contributing! 🙏
