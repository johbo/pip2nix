Render the documentation's copyright year from the last commit rather
than from a pin kept in step by hand. ``conf.py`` writes ``2015-%Y``
and the flake passes ``self.lastModified``, so the year advances on
its own and an old revision keeps rendering the year it was written
in. Both documentation builds refuse an epoch from before the project
existed, which is what ``stdenv``'s 1980 default would otherwise put
in the footer.
