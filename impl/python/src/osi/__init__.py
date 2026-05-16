"""OSI Foundation v0.1 Python reference implementation.

Public entry points:

    from osi.parsing.parser   import parse_semantic_model
    from osi.planning         import SemanticQuery, Reference, plan
    from osi.planning.planner_context import PlannerContext
    from osi.codegen          import Dialect, compile_plan

See ``SPEC.md`` and ``ARCHITECTURE.md`` at the project root for the
contract, and the top-level ``README.md`` for a runnable quick-start
example. The normative standard text lives one repository level up at
``../../proposals/foundation-v0.1/Proposed_OSI_Semantics.md``.
"""

__version__ = "0.1.0"
