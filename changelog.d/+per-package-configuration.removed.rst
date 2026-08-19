**Breaking:** Remove per-package configuration. The
``[pip2nix:package:…]`` section, with ``additional_requirements``,
``excluded_requirements`` and ``args``, was parsed and never applied
to anything pip2nix generated. A file that declares one now fails
validation instead of reporting success. Customize a generated
package in the overrides layer beside the generated file. See
ADR-0006.
