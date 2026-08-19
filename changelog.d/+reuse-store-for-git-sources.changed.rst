Stop cloning a repository the Nix store already holds. The hash a
``fetchgit`` source was generated with is recovered from the previous
file, keyed on the url and the revision together, and handed to
``nix-prefetch-git``, which then answers from the store. A regeneration
of a consumer built on git sources re-clones none of them, and the
generated file does not move. Nothing roots those store paths, so a
garbage collection puts the clones back.
