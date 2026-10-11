// Values of LIRA vector statements (LIRA docs/float_ops.md, "Vector
// statements"), lane 0 first:
// * a value of fixed shape N > 1 is std::array<T, N>, of shape 1 a scalar T;
// * a value of scalable shape (`<n>VQ`, `<n>VQVQ`) is a Scalable<T>: its lane
//   count is known at run time, its storage comes from the arena of the
//   running instruction (ArenaScope), so large values (a ZA-shaped value is up
//   to 64 KiB) stay off the stack.
// The helpers treat the three alike; each writes every lane of its output.

#ifndef LIRA_VEC_HH_INCLUDED
#define LIRA_VEC_HH_INCLUDED

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <memory>
#include <type_traits>
#include <vector>

namespace prot::vec {

template <class T> struct Scalable {
  T *data{nullptr};
  std::size_t n{0};

  T &operator[](std::size_t i) { return data[i]; }
  const T &operator[](std::size_t i) const { return data[i]; }
};

// Bump allocation in blocks that never move; a mark releases everything
// allocated after it
class Arena {
public:
  struct Mark {
    std::size_t block;
    std::size_t used;
  };

  Mark mark() const { return {m_cur, m_used}; }
  void release(Mark m) {
    m_cur = m.block;
    m_used = m.used;
  }

  void *alloc(std::size_t bytes, std::size_t align) {
    for (;;) {
      if (m_cur < m_blocks.size()) {
        const std::size_t at = (m_used + align - 1) / align * align;
        if (at + bytes <= m_blocks[m_cur].size) {
          m_used = at + bytes;
          return m_blocks[m_cur].data.get() + at;
        }
        if (m_used == 0) { // an empty block too small for the request
          m_blocks[m_cur] = Block(bytes);
          continue;
        }
        ++m_cur;
        m_used = 0;
        continue;
      }
      m_blocks.emplace_back(std::max(bytes, kBlockBytes));
    }
  }

private:
  static constexpr std::size_t kBlockBytes = std::size_t{1} << 20;

  struct Block {
    explicit Block(std::size_t n)
        : data(std::make_unique<std::byte[]>(n)), size(n) {}
    std::unique_ptr<std::byte[]> data;
    std::size_t size;
  };

  std::vector<Block> m_blocks;
  std::size_t m_cur{0};
  std::size_t m_used{0};
};

inline Arena &arena() {
  thread_local Arena a;
  return a;
}

// The scalable values of an instruction live until the end of its scope
class ArenaScope {
public:
  ArenaScope() : m_mark(arena().mark()) {}
  ArenaScope(const ArenaScope &) = delete;
  ArenaScope &operator=(const ArenaScope &) = delete;
  ~ArenaScope() { arena().release(m_mark); }

private:
  Arena::Mark m_mark;
};

// A scalable value of n lanes (contents unspecified until written)
template <class T> Scalable<T> make(std::size_t n) {
  return {static_cast<T *>(arena().alloc(n * sizeof(T), alignof(T))), n};
}

template <class X> struct Shape {
  static constexpr bool scalable = false;
  static constexpr std::size_t lanes = 1;
  using Lane = X;
};

template <class T, std::size_t N> struct Shape<std::array<T, N>> {
  static constexpr bool scalable = false;
  static constexpr std::size_t lanes = N;
  using Lane = T;
};

template <class T> struct Shape<Scalable<T>> {
  static constexpr bool scalable = true;
  static constexpr std::size_t lanes = 0; // known at run time
  using Lane = T;
};

template <class X> using Lane = typename Shape<std::remove_cvref_t<X>>::Lane;
template <class X> constexpr bool is_scalar = !Shape<std::remove_cvref_t<X>>::scalable &&
                                              Shape<std::remove_cvref_t<X>>::lanes == 1;

// Number of lanes of a value
template <class X> constexpr std::size_t count(const X &x) {
  if constexpr (Shape<X>::scalable)
    return x.n;
  else
    return Shape<X>::lanes;
}

// Lane i of a vector, or the scalar itself (i == 0)
template <class X> constexpr decltype(auto) lane(X &x, std::size_t i) {
  if constexpr (is_scalar<X>) {
    (void)i;
    return (x);
  } else {
    return (x[i]);
  }
}

// `const`, `replicate`: the same value (lane 0 of `v`) in every lane
template <class Out, class T> constexpr void splat(Out &out, const T &v) {
  const auto x = static_cast<Lane<Out>>(lane(v, 0));
  for (std::size_t i = 0; i < count(out); ++i)
    lane(out, i) = x;
}

// `index`: [0, 1, ..., N - 1]
template <class Out> constexpr void iota(Out &out) {
  for (std::size_t i = 0; i < count(out); ++i)
    lane(out, i) = static_cast<Lane<Out>>(i);
}

// `gather(value, index, default)`: out[i] = value[index[i]] when the index is
// in range, otherwise default[i]
template <class Out, class V, class I, class D>
constexpr void gather(Out &out, const V &value, const I &index, const D &dflt) {
  const std::size_t n = count(value);
  for (std::size_t i = 0; i < count(out); ++i) {
    const auto j = lane(index, i);
    lane(out, i) = j < n ? static_cast<Lane<Out>>(lane(value, static_cast<std::size_t>(j)))
                         : static_cast<Lane<Out>>(lane(dflt, i));
  }
}

// `extract_first`: the first lanes; `extend_zero`: append zero lanes
template <class Out, class X> constexpr void resize(Out &out, const X &x) {
  const std::size_t n = count(x);
  for (std::size_t i = 0; i < count(out); ++i)
    lane(out, i) = i < n ? static_cast<Lane<Out>>(lane(x, i)) : Lane<Out>{0};
}

// A register value as lanes of W bits (lane 0 in the low bits) and back
template <unsigned W, class Out, class R> constexpr void unpack(Out &out, R reg) {
  for (std::size_t i = 0; i < count(out); ++i)
    lane(out, i) = static_cast<Lane<Out>>(reg >> (W * i));
}

template <class R, unsigned W, class X> constexpr R pack(const X &x) {
  R reg{0};
  for (std::size_t i = 0; i < count(x); ++i)
    reg |= static_cast<R>(lane(x, i)) << (W * i);
  return reg;
}

// The bytes of a register (little endian, lane 0 first) as lanes of W bits
// and back; lanes narrower than a byte are packed into the bytes
template <unsigned W, class Out> void load(Out &out, const uint8_t *bytes) {
  using T = Lane<Out>;
  if constexpr (W % 8 == 0) {
    for (std::size_t i = 0; i < count(out); ++i) {
      T v{0};
      std::memcpy(&v, bytes + i * (W / 8), W / 8);
      lane(out, i) = v;
    }
  } else {
    static_assert(8 % W == 0, "lanes narrower than a byte divide it");
    for (std::size_t i = 0; i < count(out); ++i)
      lane(out, i) = static_cast<T>((bytes[i * W / 8] >> (i * W % 8)) & ((1U << W) - 1));
  }
}

template <unsigned W, class X> void store(uint8_t *bytes, const X &x) {
  if constexpr (W % 8 == 0) {
    for (std::size_t i = 0; i < count(x); ++i) {
      const auto v = lane(x, i);
      std::memcpy(bytes + i * (W / 8), &v, W / 8);
    }
  } else {
    static_assert(8 % W == 0, "lanes narrower than a byte divide it");
    std::memset(bytes, 0, (count(x) * W + 7) / 8);
    for (std::size_t i = 0; i < count(x); ++i)
      bytes[i * W / 8] |= static_cast<uint8_t>((static_cast<unsigned>(lane(x, i)) & ((1U << W) - 1))
                                               << (i * W % 8));
  }
}

} // namespace prot::vec

#endif // LIRA_VEC_HH_INCLUDED
