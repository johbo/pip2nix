Announce a prefetch on stderr rather than on stdout. The two
remaining ``print`` calls became log records at INFO level, so a
run's progress goes to the stream its warnings already use and
carries the same ``INFO:`` prefix. The announcements stay visible at
default verbosity, and a prefetch answered from a recorded hash stays
silent as before.
