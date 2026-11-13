from pathlib import Path
from typing import Dict

import cpp.base_ops
from cpp.emitter import BaseEmitter, emit_function_dict
from cpp.isa import Isa, IsaEmitter
from format.builder import FormatBuilder, string_view_literal


class FormatterEmitter(BaseEmitter):
    def __init__(self, driver):
        super().__init__(driver, Path(__file__).parent / "templates")
        self._isa = IsaEmitter(driver)

    def artifacts(self) -> Dict[Path, str]:
        constraints = self.snippet_funcs(
            syntax.condition
            for inst in self._driver.insts
            for syntax in inst.syntaxes
        )
        formats = self.snippet_funcs(
            (syntax.syntax for inst in self._driver.insts for syntax in inst.syntaxes),
            compile_snippet=FormatBuilder.snippet_func,
        )
        mnemonics = dict.fromkeys(
            syntax.mnemonic for inst in self._driver.insts for syntax in inst.syntaxes
        )
        tables = {
            name: [string_view_literal(value) for value in table.values]
            for name, table in getattr(self._driver.index, "tables_str", {}).items()
        }

        return {
            **self._isa.artifacts(),
            Path("formatter.hh"): self._templates.render(name=Path("formatter.hh.jinja")),
            Path("formatter.cc"): self._templates.render(
                name=Path("formatter.cc.jinja"),
                isa=Isa,
                insts=self._driver.insts,
                constraints=constraints,
                formats=formats,
                mnemonics={name: i for i, name in enumerate(mnemonics)},
                mnemonic_literals=[string_view_literal(name) for name in mnemonics],
                tables=tables,
                constraint_definitions=emit_function_dict(constraints),
                format_definitions=emit_function_dict(formats, "FmtCtx& ctx"),
            ),
        }
