# 50 Consecutive Picks Proof for One Trillion Brackets

Cryptographic proof of 50 consecutive correct NCAA bracket picks, beating the previous record of 49.

Before the 2026 NCAA Tournament, [One Trillion Brackets](https://onetrillionbrackets.com) generated 1,000,000,000,000 brackets and published a Merkle root to the Ethereum blockchain. After 48 games (all of Round 1 and Round 2), this repo proves that brackets exist for all 4 possible outcomes of the next two games (Iowa vs Nebraska, Texas vs Purdue), guaranteeing at least 50 consecutive correct picks.

## Quick Start

```bash
pip install blake3
python verify.py
```

## What's in this repo

### Scripts

- `verify.py`: Standalone verifier. Proves each bracket exists by checking it against the Merkle root. prove_all is more thorough, but this does the trick.
- `commitment.json`: The published Merkle root and dataset metadata
- `decode_bracket.py`: Decodes a 63-bit bracket string into human-readable game results.
- `prove_all.py`: Full proof runner. Verifies all 4 brackets end to end with detailed output.

### data/

Proof files and chunk data for 4 brackets covering all outcomes:

| File | Iowa vs Nebraska | Texas vs Purdue | Bracket # |
|------|-----------------|-----------------|-----------|
| `data/proof_0_0.json` + `data/chunk_0_0.bin` | Iowa wins | Texas wins | #1,869,192,317 |
| `data/proof_0_1.json` + `data/chunk_0_1.bin` | Iowa wins | Purdue wins | #370,415,626 |
| `data/proof_1_0.json` + `data/chunk_1_0.bin` | Nebraska wins | Texas wins | #263,059,721 |
| `data/proof_1_1.json` + `data/chunk_1_1.bin` | Nebraska wins | Purdue wins | #625,811,199 |

## The Merkle Root

```
c0bf64aedf2d6b18c027d61eaee3790ea81e2450f6157fb6eba3a894ab91a6e2
```

Published on Ethereum before the tournament:
[View on Etherscan](https://etherscan.io/tx/0xb0c2dd3c980246d7ba12fe30fa811e5c623b55b5af95e09fd02770174a193187)

Click "Click to show more" and reference the "Input Data." The hash follows "0x".

## How it works:

The bracket's 63-bit string is converted to a uint64 and verified against the raw chunk data.
The chunk is hashed with BLAKE3 (domain-separated with `0x00` prefix) to produce a leaf hash.
The leaf hash is walked up 20 levels of the Merkle tree using the sibling hashes.
The computed root is compared to the published commitment

If any bit of any bracket were different, the root would not match.

## No trust required

This verifier uses only `blake3` and standard Python. It does not import any code from the One Trillion Brackets project. You can read `verify.py` and confirm it does nothing but hash and compare.
