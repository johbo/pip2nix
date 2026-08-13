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

``pip2nix generate`` takes the same set of package specifications ``pip install`` does.
It understands ``-r``, git links and package specifications. Editable
requirements (``-e``) are rejected rather than ignored: the installation
report describes them as the local directory they would be checked out
into, which loses the url and the revision they come from.


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
``pip2nix scaffold``. To work on a project `myProject` you'd use::

    $ pip2nix scaffold --package myProject
    $ cat > pip2nix.ini <<EOF
    [pip2nix]
    requirements = .
    EOF
    $ pip2nix generate
    $ nix-shell  # all the deps should be available
