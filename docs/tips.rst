
======
 Tips
======


Missing build dependencies
==========================

Some Python packages need external libraries or a compiler before their
metadata can be read at all, and that happens while ``pip2nix generate``
resolves rather than when the generated packages are built.

Where an index publishes a package's metadata on its own (:pep:`658`),
pip reads it from there. Where it does not, pip downloads the source
distribution and runs its build backend to obtain the metadata. A
backend that probes for C headers fails at that point:

.. code:: text

    Getting requirements to build wheel: finished with status 'error'
    × Getting requirements to build wheel did not run successfully.
    ╰─> Building lxml version 6.1.1.
        Building without Cython.
        Error: Please make sure the libxml2 and libxslt development
        packages are installed.

pip2nix reaches that path more often than a plain ``pip install`` does,
because it asks pip for the source distribution of every wheel that is
built for a specific platform -- see :ref:`adr-0003`.

The remedy is to make the libraries available to the generation run
itself:

.. code:: shell

   nix shell nixpkgs#libxml2 nixpkgs#libxslt \
       --command pip2nix generate -r requirements.txt

The package may never appear in the generated file. Resolution covers
the whole dependency graph while ``only_direct`` narrows only what is
written, so the generation can fail on headers for a package that
several generated packages propagate and none of them defines.

A package building a Rust or C extension wants its toolchain the same
way, and a compiler counts as part of it: ``nixpkgs#rustc`` and
``nixpkgs#cargo`` on their own leave every Rust build script failing
with ``linker `cc` not found``.

.. code:: shell

   nix shell nixpkgs#rustc nixpkgs#cargo nixpkgs#gcc \
       --command pip2nix generate -r requirements.txt

Expect that to be slow. Building such a package's metadata means
compiling it -- for ``maturin``, minutes of compilation for a few lines
of the generated file.
