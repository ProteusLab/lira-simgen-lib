#include "aarch64_elf_loader.hh"
#include "hart.hh"
#include "memory.hh"
#include "naive_interpreter.hh"

#include <CLI/CLI.hpp>
#include <fmt/core.h>
#include <fmt/ostream.h>

#include <chrono>
#include <filesystem>
#include <memory>

namespace {
// Index 31 of the X register file is SP.
constexpr std::size_t kSPRegister = 31;
constexpr prot::isa::Addr kDefaultStack = 0xfff00000;
} // namespace

int main(int argc, const char *argv[]) try {
  std::filesystem::path elfPath;
  prot::isa::Addr stackTop = kDefaultStack;
  bool propagateExit = false;
  bool quiet = false;

  CLI::App app{"Generated LIRA AArch64 simulator (interpreter)"};

  app.add_option("elf", elfPath, "Path to executable ELF file")
      ->required()
      ->check(CLI::ExistingFile);
  app.add_flag("--propagate-exit", propagateExit,
               "Propagate exit code from guest to host");
  app.add_flag("-q,--quiet", quiet, "Do not print statistics");

  CLI11_PARSE(app, argc, argv);

  auto hart = [&] {
    prot::elf_loader::Aarch64ElfLoader loader{elfPath};

    std::unique_ptr<prot::engine::ExecEngine> engine =
        std::make_unique<prot::engine::Interpreter>();

    prot::hart::Hart hart{prot::memory::makePlain(4ULL << 30U),
                          std::move(engine)};
    hart.load(loader);
    hart.cpu().setX(kSPRegister, stackTop);
    return hart;
  }();

  auto start = std::chrono::high_resolution_clock::now();
  hart.run();
  auto end = std::chrono::high_resolution_clock::now();
  std::chrono::duration<double> duration = end - start;

  if (!quiet) {
    fmt::println(std::cerr, "icount: {}", hart.getIcount());
    fmt::println(std::cerr, "time: {} s", duration.count());
    fmt::println(std::cerr, "MIPS: {:.2f}",
                 hart.getIcount() / (duration.count() * 1'000'000));
  }

  return propagateExit ? hart.getExitCode() : EXIT_SUCCESS;
} catch (const std::exception &ex) {
  fmt::println(std::cerr, "Caught exception of type {}: {}", typeid(ex).name(),
               ex.what());
  return EXIT_FAILURE;
} catch (...) {
  fmt::println(std::cerr, "Unknown exception caught");
  return EXIT_FAILURE;
}
