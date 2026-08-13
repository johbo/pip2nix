
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

A package building a Rust or C extension wants its toolchain the same
way, ``nixpkgs#rustc`` or ``nixpkgs#libffi`` alongside the libraries it
links against.


Failing `nix-prefetch-hg`
=========================

When pointing to Mercurial repositories from your requirement files, you might
run into a situation where things fail due to issues with `nix-prefetch-hg`.
When trying to run it manually you would see an error as follows:

.. code:: shell

    nix-prefetch-hg https://code.example.com/your-repository
    abort: http authorization required for https://code.example.com/your-repository

The background is that the prefetch scripts change the environment variable
`HOME` and this means that Mercurial will not find ``~/.hgrc``.

Manually setting the environment variable `HGRCPATH` can be used as a workaround:

.. code:: shell

   export HGRCPATH=~/.hgrc
