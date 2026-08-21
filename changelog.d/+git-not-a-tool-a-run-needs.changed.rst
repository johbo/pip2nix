Stop reaching for ``git``. A repository source is fetched at the commit
pip already resolved it to, so no branch or tag is looked up any more
and ``git`` no longer has to be on ``PATH`` -- ``nix-prefetch-git``
brings its own.
