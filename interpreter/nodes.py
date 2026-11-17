# lira-simgen-lib/interpreter/nodes.py
# Snippet-node renderers for the interpreter.

import cpp.nodes  # noqa: F401  (registers the base renderers)

from lib.nodes import EnvCall, NodeImpl

from cpp.nodes import decl

from interpreter.interface import CpuInterface, m_cpu, m_mem


@NodeImpl.serves(EnvCall)
def _env_call(node: EnvCall) -> str:
    ctx = m_cpu if isinstance(node.interface, CpuInterface) else m_mem
    expr = getattr(ctx, node.interface.name)(node.inputs, node.out)
    if node.out is None:
        return f"{expr};\n"
    return f"""{decl(node.out)}
{node.out} = {expr};
"""
