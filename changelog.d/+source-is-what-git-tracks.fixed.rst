Build from the files git tracks, so a stale ``build/`` in the working
tree cannot reach the build. Nix copies the whole working directory
into the store for a dirty tree without consulting ``.gitignore``, and
setuptools then reuses the ``build/lib`` it finds there rather than the
real sources -- which produced a generator several changes out of date
while reporting success.
