#!/usr/bin/env python3
"""
Standalone Merkle proof verifier for onetrillionbrackets.com

Verifies that specific brackets exist in the committed dataset.
Requires only: blake3 (pip install blake3)

Usage:
    pip install blake3
    python verify.py
"""
import json
import struct
import sys
import os

try:
    import blake3
except ImportError:
    print("ERROR: pip install blake3")
    raise SystemExit(1)


# Actual tournament results (R1 + R2 + S16 + E8 = 60 games)
# Each bit: 0 = first-listed team wins, 1 = second-listed team wins
ACTUAL_RESULTS = "010000000100101001101000010000000011111101010101010001001100"


def hash_leaf(data: bytes) -> bytes:
    return blake3.blake3(b"\x00" + data).digest()


def hash_internal(left: bytes, right: bytes) -> bytes:
    return blake3.blake3(b"\x01" + left + right).digest()


def verify(proof_file: str, chunk_file: str, commitment_file: str = "commitment.json") -> bool:
    """
    Verify that a bracket exists at the claimed position in the committed dataset.

    Returns True if verified, False if any check fails.
    """
    with open(proof_file) as f:
        proof = json.load(f)
    with open(commitment_file) as f:
        commitment = json.load(f)

    bracket_index = proof["bracket_index"]
    bracket_bits = proof["bracket_bits"]
    chunk_index = proof["chunk_index"]
    offset = proof["bracket_offset_in_chunk_bytes"]
    leaf_hash_hex = proof["leaf_hash"]
    siblings = proof["siblings"]
    root_hex = commitment["root_hex"]

    claimed_uint64 = int(bracket_bits, 2)
    claimed_bytes = struct.pack("<Q", claimed_uint64)

    print(f"Verifying bracket #{bracket_index:,}")
    print(f"bits: {bracket_bits}")
    print(f"uint64: {claimed_uint64}")
    print(f"chunk: {chunk_index}, offset: {offset}")
    print()

    # Read the chunk and check the bracket bytes at the claimed offset
    chunk_data = open(chunk_file, "rb").read()
    record = chunk_data[offset : offset + 8]

    if record != claimed_bytes:
        (actual_val,) = struct.unpack("<Q", record)
        print(f"  [FAIL] Bracket bits do not match chunk data at offset {offset}")
        return False
    print(f"[PASS] Bracket bits match chunk data at expected offset")

    # Verify games match actual tournament results
    predicted = bracket_bits[:len(ACTUAL_RESULTS)]
    mismatches = [i for i in range(len(ACTUAL_RESULTS)) if predicted[i] != ACTUAL_RESULTS[i]]
    if mismatches:
        print(f"[FAIL] {len(mismatches)} game(s) do not match actual results")
        return False
    print(f"[PASS] First {len(ACTUAL_RESULTS)} games match actual tournament results")

    # Verify the leaf hash
    computed_leaf = hash_leaf(chunk_data)
    if computed_leaf.hex() != leaf_hash_hex:
        print(f"[FAIL] Leaf hash mismatch")
        return False
    print(f"[PASS] Leaf hash matches blake3(0x00 || chunk_data)")

    # Walk the Merkle sibling path to recompute the root
    node = computed_leaf
    idx = chunk_index
    for sib_hex in siblings:
        sib = bytes.fromhex(sib_hex)
        if idx % 2 == 0:
            node = hash_internal(node, sib)
        else:
            node = hash_internal(sib, node)
        idx //= 2

    if node.hex() != root_hex:
        print(f"[FAIL] Merkle root mismatch")
        print(f"Published: {root_hex}")
        print(f"Computed: {node.hex()}")
        return False

    print(f"[PASS] Merkle proof verified. root matches published commitment")
    print(f"Published root: {root_hex}")
    print(f"Computed root: {node.hex()}")
    print()
    return True


def main():
    # Two remaining brackets — both have UCONN and Michigan winning E8
    # They differ only on the championship game
    proof_sets = [
        ("data/proof_illinois_champ.json", "data/chunk_illinois_champ.bin", "Illinois wins championship"),
        ("data/proof_arizona_champ.json", "data/chunk_arizona_champ.bin", "Arizona wins championship"),
    ]

    results = []
    for proof_file, chunk_file, label in proof_sets:
        if not os.path.exists(proof_file) or not os.path.exists(chunk_file):
            print(f"Skipping {label}: {proof_file} or {chunk_file} not found")
            results.append(False)
            continue

        print("=" * 70)
        print(f"{label}")
        print("=" * 70)
        ok = verify(proof_file, chunk_file)
        results.append(ok)
        if ok:
            print(f"VERIFIED\n")
        else:
            print(f"FAILED\n")

    # Summary
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    if passed == total:
        print(f"ALL {total} PROOFS VERIFIED.")
        print(f"Both brackets predict: UCONN beats Duke, Illinois beats Iowa,")
        print(f"Arizona beats Purdue, Michigan beats Tennessee.")
        print(f"Then Illinois beats UCONN, Arizona beats Michigan.")
        print(f"Championship: Illinois vs Arizona — one bracket for each winner.")
    else:
        print(f"{passed}/{total} proofs verified.")
    print("=" * 70)


if __name__ == "__main__":
    main()
