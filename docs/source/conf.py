import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))

project = "Django Dynamic Serializer"
copyright = "2026, Jackson Alves"
author = "Jackson Alves"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Link "View page source" to GitHub instead of Read the Docs source view
html_context = {
    "display_github": True,
    "github_user": "jackson541",
    "github_repo": "django-dynamic-serializer",
    "github_version": "main",
    "conf_py_path": "docs/source/",
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": ("https://docs.djangoproject.com/en/stable/", "https://docs.djangoproject.com/en/stable/_objects/"),
    "rest_framework": ("https://www.django-rest-framework.org/", None),
}
