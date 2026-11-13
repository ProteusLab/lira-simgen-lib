# lira-simgen-lib/cpp/emitter.py
# Common base class for C++-code emitters.

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, Optional, Union

from cpp.context import Context
from cpp.func import Func
from lib.templates import Templates


def emit_function_dict(
    funcs: Mapping[str, Func], ctx: Union[str, Mapping[str, str]] = ""
) -> str:
    definitions = []
    for name, func in funcs.items():
        prefix = ctx if isinstance(ctx, str) else ctx.get(name, "")
        params = ", ".join(filter(None, (prefix, func.param_list)))
        definitions.append(
            f"{func.ret} {func.name}({params}) {{\n{func.body}\n}}"
        )
    return "\n\n".join(definitions)


class BaseEmitter(ABC):
    def __init__(self, driver, templates_dir: Path):
        self._driver = driver
        self._templates = Templates(templates_dir)

    @abstractmethod
    def artifacts(self) -> Dict[Path, str]: ...

    def snippet_func(
        self, name: str, *, compile_snippet: Callable = Func.from_snippet
    ) -> Func:
        index = self._driver.index
        return compile_snippet(snippet=index.snippet[name], index=index)

    def snippet_funcs(
        self,
        names: Iterable[str],
        *,
        compile_snippet: Callable = Func.from_snippet,
    ) -> Dict[str, Func]:
        return {
            name: self.snippet_func(name, compile_snippet=compile_snippet)
            for name in dict.fromkeys(names)
        }

    @staticmethod
    def snippet_ctx(snippet, name: str) -> Optional[Context]:
        fields = Func.dyn_fields(snippet)
        return Context(name=name, fields=fields) if fields else None
