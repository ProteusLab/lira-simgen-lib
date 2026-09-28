// Standard float operation bases of LIRA `fop` statements (LIRA
// docs/float_ops.md). A C++ port of the executable reference
// python/lira/float_ops.py: the Arm FP library (FPUnpack, FPRound,
// FPProcessNaN(s), FPAdd, FPMulAdd, ...) with FPCR.AH = FIZ = NEP = 0, no
// trapped exceptions and IEEE half precision.
//
// Values are IEEE binary16/32/64 bit patterns in uint64_t. Arithmetic is exact
// on a 128-bit mantissa: every operand has at most 106 significant bits (a
// double product), so aligned operands keep 70+ guard bits and the bits
// shifted out are "jammed" into the lowest bit. That is enough for a single
// correct rounding in every mode (the jammed result is odd and far below the
// rounding position).

#ifndef LIRA_FP_HH_INCLUDED
#define LIRA_FP_HH_INCLUDED

#include <cstdint>
#include <initializer_list>

namespace prot::fp {

using u128 = unsigned __int128;
using i128 = __int128;

// Rounding-mode operand values; kDyn takes the mode from the FPU state
enum : unsigned { kRNE = 0, kRTP = 1, kRTN = 2, kRTZ = 3, kRNA = 4, kODD = 5, kDyn = 7 };

// Exception flags
enum : unsigned {
  kInvalid = 1U << 0,
  kDivByZero = 1U << 1,
  kOverflow = 1U << 2,
  kUnderflow = 1U << 3,
  kInexact = 1U << 4,
  kInputDenormal = 1U << 5,
};

// Result of fcmpq/fcmps
enum : unsigned { kCmpEq = 0, kCmpLt = 1, kCmpGt = 2, kCmpUn = 3 };

// FPU controls read by an operation and the flags it raises
struct State {
  unsigned rmode = kRNE;
  bool fz = false;
  bool fz16 = false;
  bool dn = false;
  unsigned flags = 0;
};

template <unsigned N> struct Format;
template <> struct Format<16> { static constexpr int E = 5, F = 10; };
template <> struct Format<32> { static constexpr int E = 8, F = 23; };
template <> struct Format<64> { static constexpr int E = 11, F = 52; };

namespace detail {

enum Type { kZero, kDenormal, kNonzero, kInfinity, kQNaN, kSNaN };

// value = (sign ? -1 : 1) * mant * 2^exp; the lowest bit of mant may be jammed
struct Exact {
  bool sign = false;
  u128 mant = 0;
  int exp = 0;
};

struct Unpacked {
  Type type;
  bool sign;
  Exact value;
};

inline int msb(u128 v) {
  const uint64_t hi = static_cast<uint64_t>(v >> 64);
  return hi ? 127 - __builtin_clzll(hi)
            : 63 - __builtin_clzll(static_cast<uint64_t>(v));
}

inline u128 mask(int bits) { return bits >= 128 ? ~u128{0} : (u128{1} << bits) - 1; }

// Shift right, OR-ing the bits shifted out into the lowest bit
inline u128 jam_right(u128 v, int n) {
  if (n <= 0)
    return v;
  if (n >= 128)
    return v != 0;
  return (v >> n) | ((v & mask(n)) != 0);
}

// Put the most significant bit at `bit` (value unchanged)
inline Exact normalized(Exact v, int bit) {
  const int s = bit - msb(v.mant);
  v.mant <<= s;
  v.exp -= s;
  return v;
}

template <unsigned N> constexpr int emin() { return 2 - (1 << (Format<N>::E - 1)); }

template <unsigned N> constexpr uint64_t zero(bool sign) {
  return static_cast<uint64_t>(sign) << (N - 1);
}

template <unsigned N> constexpr uint64_t inf(bool sign) {
  constexpr int E = Format<N>::E, F = Format<N>::F;
  return zero<N>(sign) | (((uint64_t{1} << E) - 1) << F);
}

template <unsigned N> constexpr uint64_t default_nan() {
  constexpr int F = Format<N>::F;
  return inf<N>(false) | (uint64_t{1} << (F - 1));
}

// FPUnpackBase; `flush = false` for conversions of half precision (FZ16 is
// ignored), single and double always follow FZ
template <unsigned N> Unpacked unpack(uint64_t bits, State &st, bool flush = true) {
  constexpr int E = Format<N>::E, F = Format<N>::F;
  const bool sign = (bits >> (N - 1)) & 1;
  const uint64_t exp = (bits >> F) & ((uint64_t{1} << E) - 1);
  const uint64_t frac = bits & ((uint64_t{1} << F) - 1);
  Unpacked u{kZero, sign, {sign, 0, 0}};
  if (exp == 0) {
    if (frac == 0)
      return u;
    if (N == 16 ? st.fz16 && flush : st.fz) {
      if (N != 16)
        st.flags |= kInputDenormal;
      return u;
    }
    u.type = kDenormal;
    u.value = {sign, frac, emin<N>() - F};
  } else if (exp == (uint64_t{1} << E) - 1) {
    u.type = frac == 0 ? kInfinity : (frac >> (F - 1)) & 1 ? kQNaN : kSNaN;
  } else {
    u.type = kNonzero;
    u.value = {sign, frac | (uint64_t{1} << F),
               static_cast<int>(exp) - ((1 << (E - 1)) - 1) - F};
  }
  return u;
}

inline bool is_nan(Type t) { return t == kQNaN || t == kSNaN; }

inline unsigned mode(unsigned rm, const State &st) { return rm == kDyn ? st.rmode : rm; }

// Tail below the rounding position: none, below half, half, above half
enum Tail { kExact, kBelow, kHalf, kAbove };

// FPRoundBase (FPCR.AH = 0) of a non-zero exact value
template <unsigned N>
uint64_t round(const Exact &v, State &st, unsigned rounding, bool flush = true) {
  constexpr int E = Format<N>::E, F = Format<N>::F;
  const bool flush_out = flush && (N == 16 ? st.fz16 : st.fz);
  const bool sign = v.sign;
  const int exponent = msb(v.mant) + v.exp;
  if (flush_out && exponent < emin<N>()) {
    st.flags |= kUnderflow;
    return zero<N>(sign);
  }
  int biased = exponent - emin<N>() + 1;
  if (biased < 0)
    biased = 0;
  const int lsb_exp = biased == 0 ? emin<N>() - F : exponent - F;
  const int shift = lsb_exp - v.exp;       // bits of mant below the result lsb
  u128 int_mant;
  Tail tail;
  if (shift <= 0) {
    int_mant = v.mant << -shift;
    tail = kExact;
  } else {
    int_mant = shift >= 128 ? 0 : v.mant >> shift;
    const u128 rest = v.mant & mask(shift);
    if (rest == 0) {
      tail = kExact;
    } else if (shift > 128) {
      tail = kBelow;
    } else {
      const u128 half = u128{1} << (shift - 1);
      tail = rest < half ? kBelow : rest == half ? kHalf : kAbove;
    }
  }
  const bool error = tail != kExact;
  if (biased == 0 && error)
    st.flags |= kUnderflow;
  bool up, to_inf;
  switch (rounding) {
  case kRNE:
    up = tail == kAbove || (tail == kHalf && (int_mant & 1));
    to_inf = true;
    break;
  case kRTP:
    up = error && !sign;
    to_inf = !sign;
    break;
  case kRTN:
    up = error && sign;
    to_inf = sign;
    break;
  case kRTZ:
  case kODD:
    up = to_inf = false;
    break;
  default: // kRNA
    up = tail == kHalf || tail == kAbove;
    to_inf = true;
  }
  if (up) {
    ++int_mant;
    if (int_mant == u128{1} << F)
      biased = 1;
    if (int_mant == u128{1} << (F + 1)) {
      ++biased;
      int_mant >>= 1;
    }
  }
  if (error && rounding == kODD && !(int_mant & 1))
    ++int_mant;
  uint64_t result;
  bool inexact = error;
  if (biased >= (1 << E) - 1) {
    result = to_inf ? inf<N>(sign) : inf<N>(sign) - 1;
    st.flags |= kOverflow;
    inexact = true;
  } else {
    result = zero<N>(sign) | (static_cast<uint64_t>(biased) << F) |
             (static_cast<uint64_t>(int_mant) & ((uint64_t{1} << F) - 1));
  }
  if (inexact)
    st.flags |= kInexact;
  return result;
}

template <unsigned N> uint64_t process_nan(Type t, uint64_t op, State &st) {
  if (t == kSNaN) {
    op |= uint64_t{1} << (Format<N>::F - 1);
    st.flags |= kInvalid;
  }
  return st.dn ? default_nan<N>() : op;
}

// FPProcessNaNs: a signalling NaN beats a quiet one, then operand order
template <unsigned N, unsigned K>
bool process_nans(const Type (&types)[K], const uint64_t (&ops)[K], State &st,
                  uint64_t &result) {
  for (Type kind : {kSNaN, kQNaN})
    for (unsigned i = 0; i < K; ++i)
      if (types[i] == kind) {
        result = process_nan<N>(types[i], ops[i], st);
        return true;
      }
  return false;
}

inline Exact neg(Exact v) {
  v.sign = !v.sign;
  return v;
}

inline Exact add(Exact a, Exact b) {
  if (a.mant == 0)
    return b;
  if (b.mant == 0)
    return a;
  a = normalized(a, 125);
  b = normalized(b, 125);
  if (a.exp < b.exp) {
    const Exact t = a;
    a = b;
    b = t;
  }
  const u128 small = jam_right(b.mant, a.exp - b.exp);
  if (a.sign == b.sign)
    return {a.sign, a.mant + small, a.exp};
  if (a.mant >= small)
    return {a.sign, a.mant - small, a.exp};
  return {b.sign, small - a.mant, a.exp};
}

inline Exact mul(const Exact &a, const Exact &b) {
  return {a.sign != b.sign, a.mant * b.mant, a.exp + b.exp};
}

inline Exact div(const Exact &a, const Exact &b) {
  const Exact n = normalized(a, 125);
  u128 q = n.mant / b.mant;
  q |= (n.mant % b.mant) != 0;
  return {a.sign != b.sign, q, n.exp - b.exp};
}

inline u128 isqrt(u128 v) {
  u128 r = 0;
  u128 bit = u128{1} << 126;
  while (bit > v)
    bit >>= 2;
  while (bit != 0) {
    if (v >= r + bit) {
      v -= r + bit;
      r = (r >> 1) + bit;
    } else {
      r >>= 1;
    }
    bit >>= 2;
  }
  return r;
}

inline Exact sqrt(const Exact &v) {
  int s = 124 - msb(v.mant);
  if ((v.exp - s) & 1)
    ++s;
  const u128 m = v.mant << s;
  const int e = v.exp - s;
  u128 t = isqrt(m);
  t |= t * t != m;
  return {false, t, e / 2};
}

// Compare signed exact values: -1, 0, 1
inline int compare(const Exact &a, const Exact &b) {
  const bool za = a.mant == 0, zb = b.mant == 0;
  if (za && zb)
    return 0;
  const int sa = za ? 0 : a.sign ? -1 : 1;
  const int sb = zb ? 0 : b.sign ? -1 : 1;
  if (sa != sb)
    return sa < sb ? -1 : 1;
  const Exact x = normalized(a, 125), y = normalized(b, 125);
  int mag = x.exp != y.exp ? (x.exp < y.exp ? -1 : 1)
            : x.mant != y.mant ? (x.mant < y.mant ? -1 : 1)
                               : 0;
  return sa < 0 ? -mag : mag;
}

// Compare unpacked non-NaN values, infinities included: -1, 0, 1
inline int compare(const Unpacked &a, const Unpacked &b) {
  const auto rank = [](const Unpacked &u) {
    return u.type != kInfinity ? 0 : u.sign ? -1 : 1;
  };
  const int ra = rank(a), rb = rank(b);
  if (ra != 0 || rb != 0)
    return ra == rb ? 0 : ra < rb ? -1 : 1;
  return compare(a.value, b.value);
}

inline unsigned exact_zero_sign(unsigned rounding) { return rounding == kRTN; }

// Integer part and tail of |v| * 2^scale; magnitudes of 2^100 and above are
// clamped (every conversion saturates there)
inline void split(const Exact &v, int scale, u128 &ip, Tail &tail) {
  const int e = v.exp + scale;
  tail = kExact;
  if (v.mant == 0) {
    ip = 0;
  } else if (e >= 0) {
    ip = msb(v.mant) + e >= 100 ? u128{1} << 100 : v.mant << e;
  } else {
    const int n = -e;
    ip = n >= 128 ? 0 : v.mant >> n;
    const u128 rest = v.mant & mask(n);
    if (rest != 0) {
      if (n > 128) {
        tail = kBelow;
      } else {
        const u128 half = u128{1} << (n - 1);
        tail = rest < half ? kBelow : rest == half ? kHalf : kAbove;
      }
    }
  }
}

// _round_int: round |v| * 2^scale (signed) to an integer; `inexact` is set
// when the value was not integral
inline i128 round_int(const Exact &v, int scale, unsigned rounding, bool &inexact) {
  u128 ip;
  Tail frac;
  split(v, scale, ip, frac);
  // floor(value) and value - floor(value)
  i128 i;
  Tail error;
  if (!v.sign || frac == kExact) {
    i = v.sign ? -static_cast<i128>(ip) : static_cast<i128>(ip);
    error = frac;
  } else {
    i = -static_cast<i128>(ip) - 1;
    error = frac == kBelow ? kAbove : frac == kAbove ? kBelow : kHalf;
  }
  inexact = error != kExact;
  bool up;
  switch (rounding) {
  case kRNE:
    up = error == kAbove || (error == kHalf && (i & 1));
    break;
  case kRTP:
    up = error != kExact;
    break;
  case kRTN:
    up = false;
    break;
  case kRTZ:
    up = error != kExact && i < 0;
    break;
  default: // kRNA
    up = error == kAbove || (error == kHalf && i >= 0);
  }
  return i + up;
}

template <unsigned N> Exact from_int(i128 i) {
  return {i < 0, static_cast<u128>(i < 0 ? -i : i), 0};
}

template <unsigned N> uint64_t fmaxmin(State &st, uint64_t a, uint64_t b, bool is_max) {
  const Unpacked u1 = unpack<N>(a, st), u2 = unpack<N>(b, st);
  uint64_t result;
  if (process_nans<N>({u1.type, u2.type}, {a, b}, st, result))
    return result;
  const int c = compare(u1, u2);
  const Unpacked &u = (is_max ? c > 0 : c < 0) ? u1 : u2;
  if (u.type == kInfinity)
    return inf<N>(u.sign);
  if (u.type == kZero)
    return zero<N>(is_max ? (u1.sign && u2.sign) : (u1.sign || u2.sign));
  return round<N>(u.value, st, st.rmode);
}

template <unsigned N> uint64_t fnum(State &st, uint64_t a, uint64_t b, bool is_max) {
  const Type t1 = unpack<N>(a, st).type, t2 = unpack<N>(b, st).type;
  const uint64_t replacement = inf<N>(is_max); // a single quiet NaN loses
  if (t1 == kQNaN && t2 != kQNaN)
    a = replacement;
  else if (t1 != kQNaN && t2 == kQNaN)
    b = replacement;
  return fmaxmin<N>(st, a, b, is_max);
}

template <unsigned N> unsigned fcmp(State &st, uint64_t a, uint64_t b, bool signal) {
  const Unpacked u1 = unpack<N>(a, st), u2 = unpack<N>(b, st);
  if (is_nan(u1.type) || is_nan(u2.type)) {
    if (signal || u1.type == kSNaN || u2.type == kSNaN)
      st.flags |= kInvalid;
    return kCmpUn;
  }
  const int c = compare(u1, u2);
  return c == 0 ? kCmpEq : c < 0 ? kCmpLt : kCmpGt;
}

template <unsigned N> uint64_t frint(State &st, uint64_t a, unsigned rm, bool exact) {
  const unsigned rounding = mode(rm, st);
  const Unpacked u = unpack<N>(a, st);
  if (is_nan(u.type))
    return process_nan<N>(u.type, a, st);
  if (u.type == kInfinity)
    return inf<N>(u.sign);
  if (u.type == kZero)
    return zero<N>(u.sign);
  bool inexact;
  uint64_t result;
  if (u.value.exp >= 0) { // already integral
    inexact = false;
    result = round<N>(u.value, st, kRTZ);
  } else {
    const i128 i = round_int(u.value, 0, rounding, inexact);
    result = i == 0 ? zero<N>(u.sign) : round<N>(from_int<N>(i), st, kRTZ);
  }
  if (inexact && exact)
    st.flags |= kInexact;
  return result;
}

template <unsigned N, unsigned M>
uint64_t ftoi(State &st, uint64_t a, unsigned fbits, unsigned rm, bool is_unsigned) {
  const unsigned rounding = mode(rm, st);
  const Unpacked u = unpack<N>(a, st);
  if (is_nan(u.type))
    st.flags |= kInvalid;
  i128 i;
  bool inexact = false;
  if (u.type == kInfinity)
    i = u.sign ? -(i128{1} << 100) : i128{1} << 100;
  else if (is_nan(u.type))
    i = 0;
  else
    i = round_int(u.value, static_cast<int>(fbits), rounding, inexact);
  const i128 lo = is_unsigned ? 0 : -(i128{1} << (M - 1));
  const i128 hi = is_unsigned ? (i128{1} << M) - 1 : (i128{1} << (M - 1)) - 1;
  if (i < lo || i > hi) {
    st.flags |= kInvalid;
    i = i < lo ? lo : hi;
  } else if (inexact) {
    st.flags |= kInexact;
  }
  return static_cast<uint64_t>(i) & (M == 64 ? ~uint64_t{0} : (uint64_t{1} << M) - 1);
}

template <unsigned N, unsigned M>
uint64_t itof(State &st, uint64_t a, unsigned fbits, unsigned rm, bool is_unsigned) {
  const unsigned rounding = mode(rm, st);
  i128 i = static_cast<i128>(a);
  if (!is_unsigned && ((a >> (N - 1)) & 1))
    i -= i128{1} << N;
  if (i == 0)
    return zero<M>(false);
  Exact v = from_int<N>(i);
  v.exp = -static_cast<int>(fbits);
  return round<M>(v, st, rounding);
}

} // namespace detail

// -- Operation bases ----------------------------------------------------------

template <unsigned N> uint64_t fadd(State &st, uint64_t a, uint64_t b, unsigned rm,
                                   bool negate_b = false) {
  using namespace detail;
  const unsigned rounding = mode(rm, st);
  const Unpacked u1 = unpack<N>(a, st);
  Unpacked u2 = unpack<N>(b, st);
  uint64_t result;
  if (process_nans<N>({u1.type, u2.type}, {a, b}, st, result))
    return result;
  if (negate_b) { // FPSub
    u2.sign = !u2.sign;
    u2.value = neg(u2.value);
  }
  const bool inf1 = u1.type == kInfinity, inf2 = u2.type == kInfinity;
  if (inf1 && inf2 && u1.sign != u2.sign) {
    st.flags |= kInvalid;
    return default_nan<N>();
  }
  if ((inf1 && !u1.sign) || (inf2 && !u2.sign))
    return inf<N>(false);
  if (inf1 || inf2)
    return inf<N>(true);
  if (u1.type == kZero && u2.type == kZero && u1.sign == u2.sign)
    return zero<N>(u1.sign);
  const Exact r = add(u1.value, u2.value);
  if (r.mant == 0)
    return zero<N>(exact_zero_sign(rounding));
  return round<N>(r, st, rounding);
}

template <unsigned N> uint64_t fsub(State &st, uint64_t a, uint64_t b, unsigned rm) {
  return fadd<N>(st, a, b, rm, true);
}

template <unsigned N> uint64_t fmul(State &st, uint64_t a, uint64_t b, unsigned rm) {
  using namespace detail;
  const unsigned rounding = mode(rm, st);
  const Unpacked u1 = unpack<N>(a, st), u2 = unpack<N>(b, st);
  uint64_t result;
  if (process_nans<N>({u1.type, u2.type}, {a, b}, st, result))
    return result;
  const bool inf1 = u1.type == kInfinity, inf2 = u2.type == kInfinity;
  const bool z1 = u1.type == kZero, z2 = u2.type == kZero;
  if ((inf1 && z2) || (z1 && inf2)) {
    st.flags |= kInvalid;
    return default_nan<N>();
  }
  if (inf1 || inf2)
    return inf<N>(u1.sign != u2.sign);
  if (z1 || z2)
    return zero<N>(u1.sign != u2.sign);
  return round<N>(mul(u1.value, u2.value), st, rounding);
}

template <unsigned N> uint64_t fdiv(State &st, uint64_t a, uint64_t b, unsigned rm) {
  using namespace detail;
  const unsigned rounding = mode(rm, st);
  const Unpacked u1 = unpack<N>(a, st), u2 = unpack<N>(b, st);
  uint64_t result;
  if (process_nans<N>({u1.type, u2.type}, {a, b}, st, result))
    return result;
  const bool inf1 = u1.type == kInfinity, inf2 = u2.type == kInfinity;
  const bool z1 = u1.type == kZero, z2 = u2.type == kZero;
  if ((inf1 && inf2) || (z1 && z2)) {
    st.flags |= kInvalid;
    return default_nan<N>();
  }
  if (inf1 || z2) {
    if (!inf1)
      st.flags |= kDivByZero;
    return inf<N>(u1.sign != u2.sign);
  }
  if (z1 || inf2)
    return zero<N>(u1.sign != u2.sign);
  return round<N>(div(u1.value, u2.value), st, rounding);
}

// addend + a * b with a single rounding (FPMulAdd)
template <unsigned N>
uint64_t fmuladd(State &st, uint64_t addend, uint64_t a, uint64_t b, unsigned rm) {
  using namespace detail;
  const unsigned rounding = mode(rm, st);
  const Unpacked ua = unpack<N>(addend, st), u1 = unpack<N>(a, st), u2 = unpack<N>(b, st);
  const bool inf1 = u1.type == kInfinity, inf2 = u2.type == kInfinity;
  const bool z1 = u1.type == kZero, z2 = u2.type == kZero;
  uint64_t result = 0;
  const bool done = process_nans<N>({ua.type, u1.type, u2.type}, {addend, a, b}, st, result);
  if (ua.type == kQNaN && ((inf1 && z2) || (z1 && inf2))) {
    st.flags |= kInvalid;
    result = default_nan<N>();
  }
  if (done)
    return result;
  const bool infa = ua.type == kInfinity, zeroa = ua.type == kZero;
  const bool sp = u1.sign != u2.sign, infp = inf1 || inf2, zerop = z1 || z2;
  if ((inf1 && z2) || (z1 && inf2) || (infa && infp && ua.sign != sp)) {
    st.flags |= kInvalid;
    return default_nan<N>();
  }
  if ((infa && !ua.sign) || (infp && !sp))
    return inf<N>(false);
  if (infa || infp)
    return inf<N>(true);
  if (zeroa && zerop && ua.sign == sp)
    return zero<N>(ua.sign);
  const Exact r = add(ua.value, mul(u1.value, u2.value));
  if (r.mant == 0)
    return zero<N>(exact_zero_sign(rounding));
  return round<N>(r, st, rounding);
}

template <unsigned N> uint64_t fsqrt(State &st, uint64_t a, unsigned rm) {
  using namespace detail;
  const unsigned rounding = mode(rm, st);
  const Unpacked u = unpack<N>(a, st);
  if (is_nan(u.type))
    return process_nan<N>(u.type, a, st);
  if (u.type == kZero)
    return zero<N>(u.sign);
  if (u.type == kInfinity && !u.sign)
    return inf<N>(false);
  if (u.sign) {
    st.flags |= kInvalid;
    return default_nan<N>();
  }
  return round<N>(detail::sqrt(u.value), st, rounding);
}

template <unsigned N> uint64_t fmax(State &st, uint64_t a, uint64_t b) {
  return detail::fmaxmin<N>(st, a, b, true);
}

template <unsigned N> uint64_t fmin(State &st, uint64_t a, uint64_t b) {
  return detail::fmaxmin<N>(st, a, b, false);
}

template <unsigned N> uint64_t fmaxnm(State &st, uint64_t a, uint64_t b) {
  return detail::fnum<N>(st, a, b, true);
}

template <unsigned N> uint64_t fminnm(State &st, uint64_t a, uint64_t b) {
  return detail::fnum<N>(st, a, b, false);
}

// Quiet comparison: invalid only for signalling NaNs
template <unsigned N> uint64_t fcmpq(State &st, uint64_t a, uint64_t b) {
  return detail::fcmp<N>(st, a, b, false);
}

// Signalling comparison: invalid for any NaN
template <unsigned N> uint64_t fcmps(State &st, uint64_t a, uint64_t b) {
  return detail::fcmp<N>(st, a, b, true);
}

template <unsigned N> uint64_t frint(State &st, uint64_t a, unsigned rm) {
  return detail::frint<N>(st, a, rm, false);
}

template <unsigned N> uint64_t frintx(State &st, uint64_t a, unsigned rm) {
  return detail::frint<N>(st, a, rm, true);
}

// FPConvert from N-bit to M-bit float (half precision ignores FZ16)
template <unsigned N, unsigned M> uint64_t fcvtf(State &st, uint64_t a, unsigned rm) {
  using namespace detail;
  const unsigned rounding = mode(rm, st);
  const Unpacked u = unpack<N>(a, st, false);
  if (is_nan(u.type)) {
    if (u.type == kSNaN)
      st.flags |= kInvalid;
    if (st.dn)
      return default_nan<M>();
    constexpr int FN = Format<N>::F, FM = Format<M>::F;
    uint64_t payload = a & ((uint64_t{1} << (FN - 1)) - 1);
    payload = FM > FN ? payload << (FM - FN) : payload >> (FN - FM);
    return inf<M>(u.sign) | (uint64_t{1} << (FM - 1)) | payload;
  }
  if (u.type == kInfinity)
    return inf<M>(u.sign);
  if (u.type == kZero)
    return zero<M>(u.sign);
  return round<M>(u.value, st, rounding, M != 16);
}

// FPToFixed: N-bit float to M-bit (un)signed fixed point, saturating
template <unsigned N, unsigned M>
uint64_t ftosi(State &st, uint64_t a, uint64_t fbits, unsigned rm) {
  return detail::ftoi<N, M>(st, a, static_cast<unsigned>(fbits), rm, false);
}

template <unsigned N, unsigned M>
uint64_t ftoui(State &st, uint64_t a, uint64_t fbits, unsigned rm) {
  return detail::ftoi<N, M>(st, a, static_cast<unsigned>(fbits), rm, true);
}

// FixedToFP: N-bit (un)signed fixed point to M-bit float
template <unsigned N, unsigned M>
uint64_t sitof(State &st, uint64_t a, uint64_t fbits, unsigned rm) {
  return detail::itof<N, M>(st, a, static_cast<unsigned>(fbits), rm, false);
}

template <unsigned N, unsigned M>
uint64_t uitof(State &st, uint64_t a, uint64_t fbits, unsigned rm) {
  return detail::itof<N, M>(st, a, static_cast<unsigned>(fbits), rm, true);
}

} // namespace prot::fp

#endif // LIRA_FP_HH_INCLUDED
