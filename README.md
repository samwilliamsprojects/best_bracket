# Best Bracket Proof — One Trillion Brackets

Cryptographic proof that two brackets from [One Trillion Brackets](https://onetrillionbrackets.com) correctly predicted all 60 games through the Elite 8 of the 2026 NCAA Tournament.

Both brackets predict Illinois beating UCONN and Arizona beating Michigan in the Final Four, then Illinois vs Arizona in the championship. One has Illinois winning, the other Arizona.

## Quick Start

```bash
pip install blake3
python verify.py
```

## What's in this repo

### Scripts

- `verify.py`: Standalone verifier. Proves each bracket exists by checking it against the Merkle root.
- `prove_all.py`: Full proof runner. Verifies both brackets end to end with detailed output.
- `commitment.json`: The published Merkle root and dataset metadata.
- `decode_bracket.py`: Decodes a 63-bit bracket string into human-readable game results.

### data/

| File | Championship pick | Bracket # |
|------|------------------|-----------|
| `proof_illinois_champ.json` + `chunk_illinois_champ.bin` | Illinois wins | #655,912,043,391 |
| `proof_arizona_champ.json` + `chunk_arizona_champ.bin` | Arizona wins | #549,682,686,232 |

## The Merkle Root

```
c0bf64aedf2d6b18c027d61eaee3790ea81e2450f6157fb6eba3a894ab91a6e2
```

Published on Ethereum before the tournament:
[View on Etherscan](https://etherscan.io/tx/0xb0c2dd3c980246d7ba12fe30fa811e5c623b55b5af95e09fd02770174a193187)

Click "Click to show more" and reference the "Input Data." The hash follows "0x".

## How it works

1. The bracket's 63-bit string is converted to a uint64 and verified against the raw chunk data
2. The chunk is hashed with BLAKE3 (domain-separated with `0x00` prefix) to produce a leaf hash
3. The leaf hash is walked up 20 levels of the Merkle tree using the sibling hashes
4. The computed root is compared to the published commitment

If any bit of any bracket were different, the root would not match.

## No trust required

This verifier uses only `blake3` and standard Python. It does not import any code from the One Trillion Brackets project. You can read `verify.py` and confirm it does nothing but hash and compare.
