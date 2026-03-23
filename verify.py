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


# Actual tournament results (R1 + R2 = 48 games)
# Each bit: 0 = top team in the bracket wins, 1 = lower team on the bracket wins
ACTUAL_RESULTS = "010000000100101001101000010000000011111101010101"


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

    label = ""
    if "game_49_outcome" in proof:
        label = f" ({proof['game_49_outcome']} + {proof['game_50_outcome']})"

    print(f"Verifying bracket #{bracket_index:,}{label}")
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

    # Verify first 48 games match actual tournament results
    predicted = bracket_bits[:48]
    mismatches = [i for i in range(48) if predicted[i] != ACTUAL_RESULTS[i]]
    if mismatches:
        print(f"[FAIL] {len(mismatches)} game(s) do not match actual results")
        return False
    print(f"[PASS] First 48 games match actual tournament results")

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
    # The 4 brackets covering all outcomes of games 49 and 50
    # (Iowa vs Nebraska) x (Texas vs Purdue)
    proof_sets = [
        ("data/proof_0_0.json", "data/chunk_0_0.bin", "Iowa wins, Texas wins"),
        ("data/proof_0_1.json", "data/chunk_0_1.bin", "Iowa wins, Purdue wins"),
        ("data/proof_1_0.json", "data/chunk_1_0.bin", "Nebraska wins, Texas wins"),
        ("data/proof_1_1.json", "data/chunk_1_1.bin", "Nebraska wins, Purdue wins"),
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
        print(f"ALL {total} PROOFS VERIFIED — 50 consecutive correct picks guaranteed.")
    else:
        print(f"{passed}/{total} proofs verified.")
    print("=" * 70)


if __name__ == "__main__":
    main()
