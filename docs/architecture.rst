============
Architecture
============

pip2nix turns a set of Python requirements into a Nix expression
pinning every package that was resolved. This chapter says how the
generator is built and what shaped it; running it is
:doc:`getting_started`.

Context and scope
=================

pip2nix is run by whoever maintains a Nix package set for a Python
project. They state the requirements, run ``pip2nix generate``, and
commit what it wrote. What it wrote is then read by a Nix build rather
than by them.

The generator reads its configuration, runs pip, translates the report
pip wrote, resolves every source into something Nix can fetch, and
renders the file. The rest belongs elsewhere: pip resolves, a later
Nix run builds, and whatever Python metadata cannot express is the
customization layer's -- hand-maintained, written once by ``pip2nix
scaffold``, and never written by pip2nix again. See
:doc:`architecture/principles`.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Talks to
     - For
   * - pip, as a subprocess
     - Resolving the requirements into an installation report.
   * - The package index
     - Reached only through pip.
   * - ``nix-prefetch-url``, ``nix-prefetch-git``, ``git``
     - A source's hash, and a branch or a tag resolved to the
       :term:`commit ID` it names.
   * - ``nix-instantiate`` and a ``<nixpkgs>``
     - A ``lib.licenses`` attribute, under ``--licenses`` only.
   * - The previously generated file
     - A hash it already answered, so that a regeneration fetches
       nothing it need not.

One file is written, and it is overwritten whole every time. Nothing
put into it by hand survives, which is what the layer above it is for.

.. toctree::
   :maxdepth: 2

   architecture/design
   architecture/building-blocks
   architecture/runtime
   architecture/principles
