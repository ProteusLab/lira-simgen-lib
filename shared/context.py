"""Main public interface for defining a generator's context and handlers.

BaseContext provides access to typed snippet values and output initialization.
The @context class decorator declares the C++ context type. The @emit method
decorator registers a statement handler.
"""

from lira.ir import Shape, Statement

from shared import cpp
from shared._values import cpp_value, initialize_outputs


class BaseContext:
    """Base class for a generator's Python statement handlers.

    The optional struct describes the C++ context passed to generated
    functions. Its parameter is named by parameter_name, which defaults to ctx.
    """

    struct: cpp.Struct | None = None
    parameter_name = "ctx"

    def initializer(self, **values: str) -> str:
        """Build a context initializer from C++ expressions keyed by field name.

        Fields are emitted in declaration order. Omitted fields follow C++
        aggregate initialization rules. Unknown fields or an absent context
        struct raise ValueError.
        """
        if self.struct is None:
            raise ValueError("This usage has no C++ context")
        return self.struct.initializer(**values)

    def resolve_var(self, name: str) -> cpp.NamedValue:
        """Resolve a LIRA name in a handler to a typed C++ value.

        Earlier definitions and the current statement's outputs are available.
        In a format string, the result expands to its C++ identifier.
        """
        return cpp_value(self._values[name])

    def value_type(self, name: str) -> tuple[int, Shape]:
        """Return the LIRA width and shape for a name available to resolve_var."""
        value = self._values[name]
        return value.width, value.shape

    def init_with(self, stmt: Statement, *expressions: str) -> cpp.Statement:
        """Declare outputs in statement order and normalize them to their LIRA widths.

        Pass one C++ expression per output, or a single expression that
        decomposes into as many elements as there are outputs.
        """
        return initialize_outputs([self._values[name] for name in stmt.outputs], expressions)


def context(name: str):
    """Class decorator that builds the named C++ context struct.

    Public string-valued class attributes, including inherited ones, supply
    field names and C++ type spellings. parameter_name is reserved.
    """
    def decorate(cls):
        fields = {}
        for base in reversed(cls.__mro__):
            if base is not BaseContext and issubclass(base, BaseContext):
                fields.update(
                    (key, value) for key, value in vars(base).items()
                    if not key.startswith("_") and key != "parameter_name"
                    and isinstance(value, str)
                )
        cls.struct = cpp.Struct(
            name, tuple(cpp.NamedValue(key, value) for key, value in fields.items())
        )
        return cls

    return decorate


def emit(kind: str, specifier: str | None = None):
    """Method decorator. Register a statement handler.

    An exact handler takes (self, ctx, stmt). A kind-wide handler takes
    (self, ctx, stmt, specifier) and runs when there is no exact match.
    Access a declared context field as ctx.field to get its C++ member
    expression. For a usage without a context struct, ctx is None.

    Return arbitrary C++ text or a cpp.Statement. Subclasses inherit
    handlers and can override them by registering the same key.
    The compiler handles input and output statements directly and supplies
    default lowering for const and op.
    """
    def decorate(method):
        method._statement_key = kind, specifier
        return method

    return decorate
