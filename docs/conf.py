# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------

project = "pip2nix"
copyright = "2015-%Y, the pip2nix authors"
author = "the pip2nix authors"

release = "0.12.0"
version = ".".join(release.split(".")[:2])


# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.extlinks",
    "sphinx.ext.ifconfig",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
]

exclude_patterns = [
    "_build",
    "decisions/README.md",
]


# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_book_theme"

html_static_path = []


# -- Options for PDF output --------------------------------------------------

latex_documents = [
    ("index", "pip2nix.tex", "pip2nix Documentation", author, "manual"),
]

# pdflatex errors on an undeclared character, and Sphinx declares only
# the box drawing its own examples use. The arc pip prints is not among
# them, so it renders as the corner it is a rounded form of.
latex_elements = {
    "preamble": r"\DeclareUnicodeCharacter{2570}{\sphinxunichar{2514}}",
}


intersphinx_mapping = {}
