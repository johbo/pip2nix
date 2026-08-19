**Breaking:** Require Python 3.11. The 3.10 release target built, but
the built package could not be imported: ``build_system.py`` reads
``tomllib``, which is stdlib from 3.11 on. ``setup.py`` declares
``python_requires`` now, and the classifiers name the versions that
actually work rather than Python 2.7 through 3.6.
