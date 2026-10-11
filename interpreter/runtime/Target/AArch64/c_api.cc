// Execute one instruction of the generated interpreter on a caller-provided
// state. Guest addresses are host addresses (no translation), so tests can
// point base registers at their own buffers.

#include "cpu_state.hh"
#include "decoder.hh"
#include "memory.hh"
#include "naive_interpreter.hh"

#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace {

using prot::isa::Addr;

// Host memory; with a window [base, base + size) (size > 0) any access
// outside it is a fault
class HostMemory final : public prot::memory::Memory {
public:
  HostMemory(Addr base = 0, uint64_t size = 0) : m_base(base), m_size(size) {}

  void writeBlock(std::span<const std::byte> src, Addr addr) override {
    check(addr, src.size());
    std::memcpy(reinterpret_cast<void *>(addr), src.data(), src.size());
  }
  void readBlock(Addr addr, std::span<std::byte> dest) const override {
    check(addr, dest.size());
    std::memcpy(dest.data(), reinterpret_cast<const void *>(addr), dest.size());
  }
  uint8_t read8(Addr addr) const override { return load<uint8_t>(addr); }
  uint16_t read16(Addr addr) const override { return load<uint16_t>(addr); }
  uint32_t read32(Addr addr) const override { return load<uint32_t>(addr); }
  void write8(Addr addr, uint8_t val) override { store(addr, val); }
  void write16(Addr addr, uint16_t val) override { store(addr, val); }
  void write32(Addr addr, uint32_t val) override { store(addr, val); }

private:
  void check(Addr addr, uint64_t n) const {
    if (m_size != 0 && (addr < m_base || addr - m_base > m_size || n > m_size - (addr - m_base)))
      throw std::runtime_error{"Data abort"};
  }
  template <typename T> T load(Addr addr) const {
    check(addr, sizeof(T));
    T v;
    std::memcpy(&v, reinterpret_cast<const void *>(addr), sizeof(T));
    return v;
  }
  template <typename T> void store(Addr addr, T v) {
    check(addr, sizeof(T));
    std::memcpy(reinterpret_cast<void *>(addr), &v, sizeof(T));
  }

  Addr m_base;
  uint64_t m_size;
};

unsigned __int128 load128(const uint8_t *bytes) {
  unsigned __int128 v;
  std::memcpy(&v, bytes, sizeof(v));
  return v;
}

void store128(uint8_t *bytes, unsigned __int128 v) { std::memcpy(bytes, &v, sizeof(v)); }

} // namespace

// x: 32 registers (x0..x30, sp); v: 32 SIMD&FP registers as 64 words (low,
// high); nzcv: 4-bit flags; fpcr, fpsr: FP control and status registers; pc.
// All in/out.
// Returns 0 on success, -1 if the word does not decode, -2 on a runtime error.
extern "C" int lira_a64_exec(uint32_t word, uint64_t *x, uint64_t *v,
                             uint64_t *nzcv, uint64_t *fpcr, uint64_t *fpsr,
                             uint64_t *pc) try {
  auto insn = prot::decoder::decode(word);
  if (!insn) {
    return -1;
  }
  prot::state::CPU cpu{};
  for (std::size_t i = 0; i < 32; ++i) {
    cpu.setX(i, x[i]);
    cpu.setV(i, static_cast<unsigned __int128>(v[2 * i + 1]) << 64 | v[2 * i]);
  }
  cpu.m_nzcv = static_cast<uint8_t>(*nzcv);
  cpu.m_fpcr = static_cast<uint32_t>(*fpcr);
  cpu.m_fpsr = static_cast<uint32_t>(*fpsr);
  cpu.setPC(*pc);
  HostMemory mem;
  prot::engine::Interpreter engine;
  engine.execute(cpu, mem, *insn);
  for (std::size_t i = 0; i < 32; ++i) {
    x[i] = cpu.getX<uint64_t>(i);
    v[2 * i] = static_cast<uint64_t>(cpu.getV(i));
    v[2 * i + 1] = static_cast<uint64_t>(cpu.getV(i) >> 64);
  }
  *nzcv = cpu.m_nzcv;
  *fpcr = cpu.m_fpcr;
  *fpsr = cpu.m_fpsr;
  *pc = cpu.getPC();
  return 0;
} catch (...) {
  return -2;
}

// The whole state at a vector length of VQ quadwords (VL = 128 * VQ bits).
// Register files the simulated description lacks are ignored.
struct LiraA64State {
  uint64_t x[32];     // x0..x30, sp
  uint64_t nzcv;      // 4-bit flags
  uint64_t fpcr;
  uint64_t fpsr;
  uint64_t svcr;      // bit 0 SM, bit 1 ZA
  uint64_t pc;
  uint8_t z[32][256]; // z0..z31: the first VL / 8 bytes; v<n> is the low 16
  uint8_t p[16][32];  // p0..p15: the first VL / 64 bytes
  uint8_t ffr[32];    // the first VL / 64 bytes
  uint8_t za[65536];  // ZA: VL / 8 rows of VL / 8 bytes, row 0 first
};

// Run one word on `st` (in/out) at VQ `vq` (1..16). With mem_size > 0 any
// memory access outside [mem_base, mem_base + mem_size) is a fault.
// Returns 0 on success, -1 if the word does not decode, -2 on a fault or other
// runtime error, -4 for an invalid VQ.
extern "C" int lira_a64_run(uint32_t word, unsigned vq, LiraA64State *st, uint64_t mem_base,
                            uint64_t mem_size) try {
  if (vq < 1 || vq > 16)
    return -4;
  auto insn = prot::decoder::decode(word);
  if (!insn)
    return -1;
  prot::state::CPU cpu{};
  cpu.m_vq = vq;
  for (std::size_t i = 0; i < 32; ++i) {
    cpu.setX(i, st->x[i]);
    cpu.setV(i, load128(st->z[i]));
  }
  cpu.m_nzcv = static_cast<uint8_t>(st->nzcv);
  cpu.m_fpcr = static_cast<uint32_t>(st->fpcr);
  cpu.m_fpsr = static_cast<uint32_t>(st->fpsr);
  cpu.setPC(st->pc);
  HostMemory mem{mem_base, mem_size};
  prot::engine::Interpreter engine;
  engine.execute(cpu, mem, *insn);
  for (std::size_t i = 0; i < 32; ++i) {
    st->x[i] = cpu.getX<uint64_t>(i);
    store128(st->z[i], cpu.getV(i));
  }
  st->nzcv = cpu.m_nzcv;
  st->fpcr = cpu.m_fpcr;
  st->fpsr = cpu.m_fpsr;
  st->pc = cpu.getPC();
  return 0;
} catch (...) {
  return -2;
}

// Opcode index of the decoded instruction (-1 if none); names are in isa.hh.
extern "C" int lira_a64_decode(uint32_t word) {
  auto insn = prot::decoder::decode(word);
  return insn ? static_cast<int>(insn->m_opc) : -1;
}
