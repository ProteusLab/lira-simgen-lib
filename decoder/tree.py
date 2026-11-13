from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class MaskValue:
    mask: int
    value: int


@dataclass(frozen=True)
class Node:
    shift: int
    mask: int
    offset: int  # Child table offset, or leaf index if mask is zero.


@dataclass(frozen=True)
class DecodeTree:
    root_index: int
    nodes: tuple[Node, ...]
    children: tuple[int, ...]
    leaf_candidates: tuple[tuple[int, ...], ...]


def build_tree(encodings: Sequence[MaskValue]) -> DecodeTree:
    """Build lookup tables over ordered instruction indices for 32-bit words."""
    word_bits = 32
    if any(
        not 0 <= encoding.mask < 1 << word_bits
        or encoding.value < 0
        or encoding.value & ~encoding.mask
        for encoding in encodings
    ):
        raise ValueError("Expected a 32-bit mask and a value contained in that mask")

    nodes = []
    children = []
    leaves = []
    leaf_nodes = {}
    # Wildcard candidates can appear on many paths. Cap the total table size.
    child_budget = 16 * len(encodings)

    def leaf(candidates):
        if candidates not in leaf_nodes:
            leaf_nodes[candidates] = len(nodes)
            nodes.append(Node(shift=0, mask=0, offset=len(leaves)))
            leaves.append(candidates)
        return leaf_nodes[candidates]

    def build(candidates, tested_bits):
        if len(candidates) <= 4:
            return leaf(candidates)

        split = _choose_split(
            encodings, candidates, tested_bits, word_bits, child_budget - len(children)
        )
        if split is None:
            return leaf(candidates)

        shift, mask, buckets = split
        offset = len(children)
        children.extend([0] * len(buckets))
        next_tested = tested_bits | (mask << shift)
        for index, bucket in enumerate(buckets):
            children[offset + index] = build(bucket, next_tested)
        node_index = len(nodes)
        nodes.append(Node(shift, mask, offset))
        return node_index

    root = build(tuple(range(len(encodings))), 0)
    return DecodeTree(root, tuple(nodes), tuple(children), tuple(leaves))


def _choose_split(encodings, candidates, tested_bits, word_bits, remaining_entries):
    fixed_bits = 0
    for index in candidates:
        fixed_bits |= encodings[index].mask
    available_bits = fixed_bits & ~tested_bits

    best = None
    best_score = (len(candidates), 0)
    for width in range(1, 5):
        size = 1 << width
        if size > remaining_entries:
            break
        mask = size - 1
        for shift in range(word_bits - width + 1):
            window = mask << shift
            if window & available_bits != window:
                continue
            buckets = [[] for _ in range(size)]
            for index in candidates:
                encoding = encodings[index]
                fixed = (encoding.mask >> shift) & mask
                value = (encoding.value >> shift) & mask
                for entry, bucket in enumerate(buckets):
                    if entry & fixed == value:
                        bucket.append(index)
            score = (sum(map(len, buckets)) / size, size)
            if score < best_score:
                best_score = score
                best = shift, mask, tuple(map(tuple, buckets))
    return best
