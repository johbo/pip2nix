Installation
============

`pip2nix` is a flake, so it can be run without installing anything::

  $ nix run github:johbo/pip2nix -- generate -r requirements.txt

To keep a build around, clone the repository and build it::

  $ git clone https://github.com/johbo/pip2nix
  $ cd pip2nix
  $ nix build

The generator is then ``./result/bin/pip2nix``. ``nix build`` builds the
default target, which is Python 3.13. The targets
``.#pip2nix_python310`` up to ``.#pip2nix_python313`` build against a
specific interpreter.

That choice is not cosmetic: pip2nix resolves requirements against the
interpreter it runs under, not against the one the generated packages
are built with. See :doc:`architecture/design`.


Basic usage
===========


Ad-hoc python-packages.nix generation
-------------------------------------

To generate python-packages.nix for a set of requirements::

    $ pip2nix generate -r requirements.txt

``pip2nix generate`` understands requirement files (``-r``), package
specifications and git links, spelled the way ``pip install`` spells
them. Two kinds of requirement are rejected rather than resolved:

Editable requirements (``-e``)
    The installation report describes them as the local directory they
    would be checked out into, which loses the url and the revision
    they come from.

Mercurial repositories (``hg+``)
    Only git repositories are rendered.

Both abort the run and name the requirement, rather than generating
something plausible.


Using pip2nix in a project
--------------------------

When packaging a project with pip2nix you'll want to make sure it's called the
same way every time you bump dependencies. To do that, you can create a
``pip2nix.ini`` file::

    [pip2nix]
    requirements = -r ./requirements.txt

This way you can just run ``pip2nix generate`` in the project's root.
More about the configuration file in :doc:`configuration`.

To actually use the generated packages file, you can create a default.nix with
``pip2nix scaffold``. To work on a project `my-project` you'd use::

    $ pip2nix scaffold --package my-project
    $ cat > pip2nix.ini <<EOF
    [pip2nix]
    requirements = .
    EOF
    $ pip2nix generate
    $ nix-shell  # all the deps should be available

The name is canonicalized before it is written -- lowercased, with
underscores and dots turned into hyphens -- so the scaffold refers to
the package under the same name the generated file defines it under.
``--package My_Project`` and ``--package my-project`` produce the same
file. See :doc:`architecture/principles`.
