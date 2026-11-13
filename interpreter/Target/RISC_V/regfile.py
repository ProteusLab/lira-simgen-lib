from interpreter.regfile import RegisterFile, attributes


class XRegs(RegisterFile):
    @property
    def set_guard(self):
        return "".join(
            f"  if (reg == {index}) return; // {reg.name} is hardwired to zero\n"
            for index, reg in enumerate(self.file.regs) if "zero" in attributes(reg)
        )

    @property
    def get_guard(self):
        return "".join(
            f"  if (reg == {index}) return 0; // {reg.name} is hardwired to zero\n"
            for index, reg in enumerate(self.file.regs) if "zero" in attributes(reg)
        )


REGISTER_FILES = {"XRegs": XRegs}
