// Execute one instruction of the generated interpreter on a caller-provided
// state. Guest addresses are host addresses (no translation), so tests can
// point base registers at their own buffers.

#include "cpu_state.hh"
#include "decoder.hh"
#include "memory.hh"
#include "naive_interpreter.hh"

#include <cstdint>
#include <cstring>

namespace {

using prot::isa::Addr;

class HostMemory final : public prot::memory::Memory {
public:
  void writeBlock(std::span<const std::byte> src, Addr addr) override {
    std::memcpy(reinterpret_cast<void *>(addr), src.data(), src.size());
  }
  void readBlock(Addr addr, std::span<std::byte> dest) const override {
    std::memcpy(dest.data(), reinterpret_cast<const void *>(addr), dest.size());
  }
  uint8_t read8(Addr addr) const override { return load<uint8_t>(addr); }
  uint16_t read16(Addr addr) const override { return load<uint16_t>(addr); }
  uint32_t read32(Addr addr) const override { return load<uint32_t>(addr); }
  void write8(Addr addr, uint8_t val) override { store(addr, val); }
  void write16(Addr addr, uint16_t val) override { store(addr, val); }
  void write32(Addr addr, uint32_t val) override { store(addr, val); }

private:
  template <typename T> static T load(Addr addr) {
    T v;
    std::memcpy(&v, reinterpret_cast<const void *>(addr), sizeof(T));
    return v;
  }
  template <typename T> static void store(Addr addr, T v) {
    std::memcpy(reinterpret_cast<void *>(addr), &v, sizeof(T));
  }
};

} // namespace

// x: 32 registers (x0..x30, sp); nzcv: 4-bit flags; pc: in/out.
// Returns 0 on success, -1 if the word does not decode, -2 on a runtime error.
extern "C" int lira_a64_exec(uint32_t word, uint64_t *x, uint64_t *nzcv,
                             uint64_t *pc) try {
  auto insn = prot::decoder::decode(word);
  if (!insn) {
    return -1;
  }
  prot::state::CPU cpu{};
  for (std::size_t i = 0; i < 32; ++i) {
    cpu.setX(i, x[i]);
  }
  cpu.m_nzcv = static_cast<uint8_t>(*nzcv);
  cpu.setPC(*pc);
  HostMemory mem;
  prot::engine::Interpreter engine;
  engine.execute(cpu, mem, *insn);
  for (std::size_t i = 0; i < 32; ++i) {
    x[i] = cpu.getX<uint64_t>(i);
  }
  *nzcv = cpu.m_nzcv;
  *pc = cpu.getPC();
  return 0;
} catch (...) {
  return -2;
}

// Opcode index of the decoded instruction (-1 if none); names are in isa.hh.
extern "C" int lira_a64_decode(uint32_t word) {
  auto insn = prot::decoder::decode(word);
  return insn ? static_cast<int>(insn->m_opc) : -1;
}
