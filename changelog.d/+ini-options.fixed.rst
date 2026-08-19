Fix three options a ``pip2nix.ini`` could not set. ``no_index``,
``licenses`` and ``extra_index_url`` were overwritten by the command
line's own defaults, so a file that set them was ignored without
saying so. ``licenses`` was additionally read while declared in no
configuration spec, and can be set in a file at all for the first
time.
