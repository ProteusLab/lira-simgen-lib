// Values of LIRA vector statements (LIRA docs/float_ops.md, "Vector
// statements"): a value of shape N > 1 is std::array<T, N> (lane 0 first), a
// value of shape 1 is a scalar T. The helpers treat both alike.

#ifndef LIRA_VEC_HH_INCLUDED
#define LIRA_VEC_HH_INCLUDED

#include <array>
#include <cstddef>
#include <type_traits>

namespace prot::vec {

template <class X> struct Shape {
  static constexpr std::size_t lanes = 1;
  using Lane = X;
};

template <class T, std::size_t N> struct Shape<std::array<T, N>> {
  static constexpr std::size_t lanes = N;
  using Lane = T;
};

template <class X> constexpr std::size_t lanes = Shape<std::remove_cvref_t<X>>::lanes;
template <class X> using Lane = typename Shape<std::remove_cvref_t<X>>::Lane;

// Lane i of a vector, or the scalar itself (i == 0)
template <class X> constexpr decltype(auto) lane(X &x, std::size_t i) {
  if constexpr (lanes<X> == 1) {
    (void)i;
    return (x);
  } else {
    return (x[i]);
  }
}

// `const`, `replicate`: the same value in every lane
template <class Out, class T> constexpr Out splat(T v) {
  Out out{};
  for (std::size_t i = 0; i < lanes<Out>; ++i)
    lane(out, i) = static_cast<Lane<Out>>(v);
  return out;
}

// `index`: [0, 1, ..., N - 1]
template <class Out> constexpr Out iota() {
  Out out{};
  for (std::size_t i = 0; i < lanes<Out>; ++i)
    lane(out, i) = static_cast<Lane<Out>>(i);
  return out;
}

// `gather(value, index, default)`: out[i] = value[index[i]] when the index is
// in range, otherwise default[i]
template <class Out, class V, class I, class D>
constexpr Out gather(const V &value, const I &index, const D &dflt) {
  Out out{};
  for (std::size_t i = 0; i < lanes<Out>; ++i) {
    const auto j = lane(index, i);
    lane(out, i) = j < lanes<V> ? static_cast<Lane<Out>>(lane(value, static_cast<std::size_t>(j)))
                                : static_cast<Lane<Out>>(lane(dflt, i));
  }
  return out;
}

// `extract_first`: the first lanes; `extend_zero`: append zero lanes
template <class Out, class X> constexpr Out resize(const X &x) {
  Out out{};
  for (std::size_t i = 0; i < lanes<Out> && i < lanes<X>; ++i)
    lane(out, i) = static_cast<Lane<Out>>(lane(x, i));
  return out;
}

// A register value as lanes of W bits (lane 0 in the low bits) and back
template <class Out, unsigned W, class R> constexpr Out unpack(R reg) {
  Out out{};
  for (std::size_t i = 0; i < lanes<Out>; ++i)
    lane(out, i) = static_cast<Lane<Out>>(reg >> (W * i));
  return out;
}

template <class R, unsigned W, class X> constexpr R pack(const X &x) {
  R reg{0};
  for (std::size_t i = 0; i < lanes<X>; ++i)
    reg |= static_cast<R>(lane(x, i)) << (W * i);
  return reg;
}

} // namespace prot::vec

#endif // LIRA_VEC_HH_INCLUDED
