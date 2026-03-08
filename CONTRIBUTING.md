# Contributing to django-dynamic-serializer

Contributions are welcome. This document explains how to get set up, run tests, and submit changes.

## Development setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/jackson541/django-dynamic-serializer.git
   cd django-dynamic-serializer
   ```

2. **Create a virtual environment** (recommended)

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   ```

3. **Install the project in editable mode with test dependencies**

   ```bash
   pip install -e ".[virtual-models]"
   ```

   Or without the optional dependency (tests that require django-virtual-models will be skipped):

   ```bash
   pip install -e .
   pip install django djangorestframework
   ```

## Running tests

Use either of the following. Both use the `tests.settings` Django configuration and the in-memory SQLite database.

**Option 1: project script (recommended)**

```bash
python runtests.py
```

**Option 2: Django test runner**

```bash
DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests
```

To run a specific test module or class:

```bash
DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_mixins
DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_views.ViewResponseTest
```

To run tests with django-virtual-models (so integration and virtual-model tests are not skipped), install the extra first:

```bash
pip install django-virtual-models>=0.1.4
python runtests.py
```

## Building the documentation

Documentation is built with Sphinx. From the repo root:

```bash
pip install sphinx sphinx-rtd-theme sphinx-copybutton
cd docs
make html
```

Output is in `docs/build/html/`. Open `index.html` in a browser to preview.

## Project layout

- **`django_dynamic_serializer/`** — main package (mixins and views). Changes to the library belong here.
- **`tests/`** — test suite: models, serializers, views, URLs, and test modules. Use these as reference and for regression tests.
- **`docs/source/`** — Sphinx documentation source. Update when changing the API or adding features.

## Submitting changes

1. **Open an issue** (optional but helpful) to discuss bugs or features before a large change.
2. **Fork the repository** and create a branch from `main` (or `master`).
3. **Make your changes.** Keep the test suite passing and add tests for new behavior.
4. **Run the full test suite** with `python runtests.py` (and with django-virtual-models installed if your change touches that integration).
5. **Open a pull request** against the default branch. Describe what changed and why; link any related issues.

By submitting a pull request, you agree that your contributions are licensed under the [MIT License](LICENSE).
