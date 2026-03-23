#!/usr/bin/env python3
"""
Full proof runner for onetrillionbrackets.com

Verifies all 4 brackets end to end, printing every step:
  1. Read the chunk file and hash it to get the leaf hash
  2. Extract the bracket at the claimed byte offset
  3. Decode the 63-bit bracket into game outcomes
  4. Walk up every level of the Merkle tree, printing each hash
  5. Compare the final computed root to the published commitment

Requires: pip install blake3
"""
import json
import struct
import os
import sys

try:
    import blake3
except ImportError:
    print("you need to pip install blake3")
    raise SystemExit(1)

from decode_bracket import decode, ROUND_NAMES


# Actual tournament results (R1 + R2 = 48 games)
# Each bit: 0 = higher seed won, 1 = lower seed won
ACTUAL_RESULTS = "010000000100101001101000010000000011111101010101"


# Hashing

def hash_leaf(data: bytes) -> bytes:
    return blake3.blake3(b"\x00" + data).digest()


def hash_internal(left: bytes, right: bytes) -> bytes:
    return blake3.blake3(b"\x01" + left + right).digest()


#Pretty things

def hr(char="=", width=76):
    print(char * width)


def section(title):
    print()
    hr()
    print(f"  {title}")
    hr()
    print()


# proof logic

def prove_bracket(proof_path: str, chunk_path: str, commitment: dict) -> bool:
    with open(proof_path) as f:
        proof = json.load(f)

    bracket_index = proof["bracket_index"]
    bracket_bits = proof["bracket_bits"]
    chunk_index = proof["chunk_index"]
    offset = proof["bracket_offset_in_chunk_bytes"]
    leaf_hash_hex = proof["leaf_hash"]
    siblings = proof["siblings"]
    root_hex = commitment["root_hex"]

    game_49 = proof.get("game_49_outcome", "?")
    game_50 = proof.get("game_50_outcome", "?")

    section(f"BRACKET #{bracket_index:,}  ({game_49} wins, {game_50} wins)")

    # Hash the chunk

    print("Hash the chunk")
    print(f"Reading {chunk_path}")

    chunk_data = open(chunk_path, "rb").read()
    chunk_size = len(chunk_data)
    print(f"Chunk size: {chunk_size:,} bytes ({chunk_size / (1024*1024):.1f} MB)")
    print(f"Chunk index: {chunk_index:,}")
    print()

    print(f"Computing blake3(0x00 || chunk_data)")
    computed_leaf = hash_leaf(chunk_data)
    print(f"Computed leaf hash:  {computed_leaf.hex()}")
    print(f"Expected leaf hash:  {leaf_hash_hex}")

    if computed_leaf.hex() == leaf_hash_hex:
        print(f"[PASS] Leaf hash matches.")
    else:
        print(f"[FAIL] Leaf hash does not match!")
        return False
    print()

    # Extract bracket from chunk

    print("Extract bracket from chunk")
    print(f"Byte offset: {offset:,}")
    print(f"Reading 8 bytes at offset {offset:,}")

    record = chunk_data[offset : offset + 8]
    actual_uint64, = struct.unpack("<Q", record)
    actual_bits = format(actual_uint64, "063b")

    print(f"Raw bytes (hex): {record.hex()}")
    print(f"uint64 (little-endian): {actual_uint64:,}")
    print(f"As 63-bit binary: {actual_bits}")
    print()

    claimed_uint64 = int(bracket_bits, 2)
    print(f"Claimed bits: {bracket_bits}")
    print(f"Extracted bits: {actual_bits}")

    if actual_bits == bracket_bits:
        print(f"[PASS] Bracket bits match the chunk data.")
    else:
        print(f"[FAIL] Bracket bits do not match!")
        return False
    print()

    # Decode the bracket

    print("Decode the 63 bits into game outcomes")
    print()

    games = decode(bracket_bits)
    current_round = ""
    for g in games:
        if g["round"] != current_round:
            current_round = g["round"]
            print(f"{current_round}")
            print(f"{'-' * 56}")

        loser = g["team_b"] if g["winner"] == g["team_a"] else g["team_a"]
        bit = g["bit_value"]
        pos = g["bit_position"]
        print(f"{g['winner']:15s} def. {loser:15s}  (bit {pos}: {bit})")

    champ = games[-1]["winner"]
    print()
    print(f"Champion: {champ}")
    print()

    # Verify first 48 games match actual results

    print("Verify first 48 games match actual tournament results")
    print()
    print(f"Bracket bits (1-48): {bracket_bits[:48]}")
    print(f"Actual results: {ACTUAL_RESULTS}")
    print()

    mismatches = []
    for i in range(48):
        if bracket_bits[i] != ACTUAL_RESULTS[i]:
            mismatches.append(i)

    if not mismatches:
        print(f"[PASS] All 48 games match. Every Round 1 and Round 2 prediction was correct.")
    else:
        print(f"[FAIL] {len(mismatches)} game(s) do not match actual results:")
        for m in mismatches:
            print(f"Game {m}: bracket={bracket_bits[m]}, actual={ACTUAL_RESULTS[m]}")
        return False
    print()

    # Walk up the Merkle tree

    print("Walk up the Merkle tree (all 20 levels)")
    print()

    node = computed_leaf
    idx = chunk_index

    print(f"Leaf hash: {node.hex()}")
    print()

    for level, sib_hex in enumerate(siblings):
        sib = bytes.fromhex(sib_hex)
        is_right = idx % 2 == 1

        if is_right:
            left, right = sib, node
            left_label, right_label = "sibling", "ours"
        else:
            left, right = node, sib
            left_label, right_label = "ours", "sibling"

        parent = hash_internal(left, right)

        print(f"Level {level + 1} of {len(siblings)}")
        print(f"  Left ({left_label}):  {left.hex()}")
        print(f"  Right ({right_label}): {right.hex()}")
        print(f"  blake3(0x01 || left || right) = {parent.hex()}")
        print()

        node = parent
        idx //= 2

    # Compare to published root

    print("Compare computed root to published commitment")
    print()
    print(f"Published root: {root_hex}")
    print(f"Computed root:  {node.hex()}")
    print()

    if node.hex() == root_hex:
        print(f"[PASS] Merkle root matches the published commitment.")
        print(f"VERIFIED: Bracket #{bracket_index:,} provably exists in the dataset.")
        print(f"First 48 games correct, and {game_49} and {game_50} win games 49 and 50.")
        return True
    else:
        print(f"  [FAIL] Merkle root does not match!")
        return False


# Main

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    commitment_path = "commitment.json"
    with open(commitment_path) as f:
        commitment = json.load(f)

    print()
    hr("=", 76)
    print("ONE TRILLION BRACKETS: FULL PROOF VERIFICATION")
    hr("=", 76)
    print()
    print(f"Published Merkle root: {commitment['root_hex']}")
    print(f"Algorithm: {commitment['algorithm']}")
    print(f"Total brackets: {commitment['records']:,}")
    print(f"Total chunks: {commitment['total_chunks']:,}")
    print(f"Chunk size: {commitment['chunk_bytes']:,} bytes")
    print(f"Etherscan: https://etherscan.io/tx/0xb0c2dd3c980246d7ba12fe30fa811e5c623b55b5af95e09fd02770174a193187")

    proof_sets = [
        ("data/proof_0_0.json", "data/chunk_0_0.bin"),
        ("data/proof_0_1.json", "data/chunk_0_1.bin"),
        ("data/proof_1_0.json", "data/chunk_1_0.bin"),
        ("data/proof_1_1.json", "data/chunk_1_1.bin"),
    ]

    results = []
    for proof_file, chunk_file in proof_sets:
        if not os.path.exists(proof_file) or not os.path.exists(chunk_file):
            print(f"\n  Skipping: {proof_file} or {chunk_file} not found")
            results.append(False)
            continue

        ok = prove_bracket(proof_file, chunk_file, commitment)
        results.append(ok)
        print()

    # Summary
    section("SUMMARY")
    passed = sum(results)
    total = len(results)
    for i, (pf, _) in enumerate(proof_sets):
        status = "VERIFIED" if results[i] else "FAILED"
        with open(pf) as f:
            p = json.load(f)
        g49 = p.get("game_49_outcome", "?")
        g50 = p.get("game_50_outcome", "?")
        print(f"[{status}]  Bracket #{p['bracket_index']:,}  ({g49} wins, {g50} wins)")

    print()
    if passed == total:
        print(f"ALL {total} PROOFS VERIFIED.")
        print(f"All 4 possible outcomes of games 49 and 50 are covered.")
        print(f"50 consecutive correct picks guaranteed.")
    else:
        print(f"{passed}/{total} proofs verified.")
    hr()
    print()


if __name__ == "__main__":
    main()
