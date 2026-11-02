# lira-simgen-lib/lib/Target/RISC_V/__init__.py
# Declarative target model for RISC-V. Register-file and interface emission
# models live with the tools that render them; the library only contributes
# the base-operation overrides from the C++ backend.

from cpp.Target.RISC_V import base_ops  # noqa: F401  (registers the target overrides)
