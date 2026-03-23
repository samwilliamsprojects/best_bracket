#!/usr/bin/env python3
"""
Decode a 63-bit bracket string into human-readable game results.

Exactly mirrors the bracket generation used in One Trillion Brackets.
Each bit represents a game outcome: 0 = first team wins, 1 = second team wins. Read top to bottom for a matchup.
Bits are read MSB-first: bit 62 is the first Round 1 game, bit 0 is the championship (yes, that means functionally backwards).

Usage:
    python decode_bracket.py <63-bit string>
    python decode_bracket.py 011000100000000000000010000010000111000000100111001100000001000
"""
import sys

# Tournament Configuration
# Team names in exact bracket order per region.
# Each region lists 8 matchups: (1v16), (8v9), (5v12), (4v13), (6v11), (3v14), (7v10), (2v15)
# NOTE: I did NOT match team regions to the true regions in the tournament. I found it easier
# to not move things around and just use the regions that already existed in my simulation runs from previous years
# and just apply the current teams for the top-left quadrant to the region that I had labled
# as the top-left quadrant. This order matches the order of brackets commonly on the internet in every way except
# region name.
REGIONS = {
    "South": [
        ("Duke", "Siena"), ("Ohio St", "TCU"), ("St. John's", "N. Iowa"),
        ("Kansas", "Cal Baptist"), ("Louisville", "South Florida"),
        ("Mich. St.", "NDSU"), ("UCLA", "UCF"), ("UCONN", "Furman"),
    ],
    "West": [
        ("Florida", "Prairie"), ("Clemson", "Iowa"), ("Vanderbilt", "McNeese St."),
        ("Nebraska", "Troy"), ("UNC", "VCU"),
        ("Illinois", "Penn"), ("St. Mary's", "Texas A&M"), ("Houston", "Idaho"),
    ],
    "East": [
        ("Arizona", "Long Island"), ("Villanova", "Utah St."), ("Wisconsin", "High Point"),
        ("Arkansas", "Hawaii"), ("BYU", "Texas"),
        ("Gonzaga", "Kennesaw St."), ("Miami (FL)", "Missouri"), ("Purdue", "Queens (N.C.)"),
    ],
    "Midwest": [
        ("Michigan", "UMBC"), ("Georgia", "St. Louis"), ("Texas Tech", "Akron"),
        ("Alabama", "Hofstra"), ("Tennessee", "Miami (OH)"),
        ("Virginia", "Wright St."), ("Kentucky", "Santa Clara"), ("Iowa St.", "Tennessee St."),
    ],
}

REGION_ORDER = ("South", "West", "East", "Midwest")
ROUND_NAMES = ["Round of 64", "Round of 32", "Sweet 16", "Elite 8", "Final Four", "Championship"]

# Final Four bracket: South vs West, East vs Midwest
FF_MATCHUPS = [(0, 1), (2, 3)]  # region indices


def decode(bits: str) -> list[dict]:
    """
    Decode a 63-bit string into a list of game results.

    Returns a list of dicts with keys:
        round, region (or 'Final Four'/'Championship'), team_a, team_b, winner, bit_position
    """
    if len(bits) != 63 or not all(c in '01' for c in bits):
        raise ValueError("Input must be exactly 63 characters of 0s and 1s")

    results = []
    bit_idx = 0  # index into the bit string (0 = MSB = bit 62)

    # Track winners advancing through rounds
    # winners[region_idx] = list of advancing teams
    winners = {r: [] for r in range(4)}

    # Round 1: 32 games (bits 0-31 of string = bits 62-31)
    for r_idx, region in enumerate(REGION_ORDER):
        matchups = REGIONS[region]
        for m_idx, (team_a, team_b) in enumerate(matchups):
            bit = int(bits[bit_idx])
            winner = team_a if bit == 0 else team_b
            results.append({
                "round": ROUND_NAMES[0],
                "region": region,
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner,
                "bit_position": 62 - bit_idx,
                "bit_value": bit,
            })
            winners[r_idx].append(winner)
            bit_idx += 1

    # Rounds 2-4: Within each region
    for rnd in range(1, 4):  # Round of 32, Sweet 16, Elite 8
        new_winners = {r: [] for r in range(4)}
        for r_idx, region in enumerate(REGION_ORDER):
            teams = winners[r_idx]
            for i in range(0, len(teams), 2):
                team_a = teams[i]
                team_b = teams[i + 1]
                bit = int(bits[bit_idx])
                winner = team_a if bit == 0 else team_b
                results.append({
                    "round": ROUND_NAMES[rnd],
                    "region": region,
                    "team_a": team_a,
                    "team_b": team_b,
                    "winner": winner,
                    "bit_position": 62 - bit_idx,
                    "bit_value": bit,
                })
                new_winners[r_idx].append(winner)
                bit_idx += 1
        winners = new_winners

    # Final Four: 2 games
    ff_winners = []
    for r_a, r_b in FF_MATCHUPS:
        team_a = winners[r_a][0]
        team_b = winners[r_b][0]
        bit = int(bits[bit_idx])
        winner = team_a if bit == 0 else team_b
        label = f"{REGION_ORDER[r_a]} vs {REGION_ORDER[r_b]}"
        results.append({
            "round": ROUND_NAMES[4],
            "region": label,
            "team_a": team_a,
            "team_b": team_b,
            "winner": winner,
            "bit_position": 62 - bit_idx,
            "bit_value": bit,
        })
        ff_winners.append(winner)
        bit_idx += 1

    # Championship
    team_a = ff_winners[0]
    team_b = ff_winners[1]
    bit = int(bits[bit_idx])
    winner = team_a if bit == 0 else team_b
    results.append({
        "round": ROUND_NAMES[5],
        "region": "Championship",
        "team_a": team_a,
        "team_b": team_b,
        "winner": winner,
        "bit_position": 62 - bit_idx,
        "bit_value": bit,
    })

    return results


def print_bracket(results: list[dict]):
    """Pretty-print decoded bracket results."""
    current_round = ""
    for g in results:
        if g["round"] != current_round:
            current_round = g["round"]
            print(f"\n{'='*60}")
            print(f"  {current_round}")
            print(f"{'='*60}")

        region = g["region"]
        loser = g["team_b"] if g["winner"] == g["team_a"] else g["team_a"]
        bit = g["bit_value"]
        pos = g["bit_position"]

        print(f"  [{region:20s}]  {g['winner']:15s} def. {loser:15s}  (bit {pos}: {bit})")

    # Print champion
    champ = results[-1]["winner"]
    print(f"\n{'*'*60}")
    print(f"  CHAMPION: {champ}")
    print(f"{'*'*60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python decode_bracket.py <63-bit string>")
        print("Example: python decode_bracket.py 011000100000000000000010000010000111000000100111001100000001000")
        sys.exit(1)

    bits = sys.argv[1].strip().replace(" ", "").replace("_", "")
    results = decode(bits)
    print_bracket(results)
