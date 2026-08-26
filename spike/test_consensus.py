import sys
from pathlib import Path

# Add spike to path so we can import 04_consensus
SPIKE = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE))

from importlib.machinery import SourceFileLoader
# Load 04_consensus.py module directly since it starts with numbers
consensus_module = SourceFileLoader("consensus_mod", str(SPIKE / "04_consensus.py")).load_module()
consensus_plate = consensus_module.consensus_plate


def test_clean_agreement():
    reads = [
        {"frame": 1, "text": "KA05MH1234", "conf": 0.9},
        {"frame": 2, "text": "KA05MH1234", "conf": 0.95},
        {"frame": 3, "text": "KA05MH1234", "conf": 0.92},
    ]
    res = consensus_plate(reads)
    assert res["plate_text"] == "KA05MH1234"
    assert res["consensus_method"] == "character_vote"


def test_substitution_noise():
    # 3 reads: true plate is KA05MH1234
    reads = [
        {"frame": 1, "text": "KAO5MH1234", "conf": 0.8},  # O instead of 0
        {"frame": 2, "text": "KA0SMH1234", "conf": 0.85}, # S instead of 5
        {"frame": 3, "text": "KA05MH1234", "conf": 0.95}, # Perfect
        {"frame": 4, "text": "KA05MHI234", "conf": 0.75}, # I instead of 1
    ]
    res = consensus_plate(reads)
    # Positions: 
    # K: K(0.8) + K(0.85) + K(0.95) + K(0.75) -> K
    # A: A... -> A
    # pos 2: O(0.8), 0(0.85), 0(0.95), 0(0.75) -> 0 wins (0.85+0.95+0.75 = 2.55 vs 0.8)
    # pos 3: 5(0.8), S(0.85), 5(0.95), 5(0.75) -> 5 wins (0.8+0.95+0.75 = 2.5 vs 0.85)
    # pos 4: M
    # pos 5: H
    # pos 6: 1(0.8), 1(0.85), 1(0.95), I(0.75) -> 1 wins
    assert res["plate_text"] == "KA05MH1234"


def test_mixed_lengths():
    # modal length is 10 (KA05MH1234)
    reads = [
        {"frame": 1, "text": "KA05MH1234", "conf": 0.9},   # len 10
        {"frame": 2, "text": "KA05MH12345", "conf": 0.85}, # len 11 (within 1, included)
        {"frame": 3, "text": "KA05MH123", "conf": 0.92},   # len 9 (within 1, included)
        {"frame": 4, "text": "KA05MH1234", "conf": 0.95},  # len 10
        {"frame": 5, "text": "KA05", "conf": 0.5},         # len 4 (discarded)
    ]
    res = consensus_plate(reads)
    assert res["plate_text"] == "KA05MH1234" # the 11th char only has 1 vote, and since modal len is 10, it's truncated
    assert res["consensus_method"] == "character_vote"


def test_all_empty():
    reads = [
        {"frame": 1, "text": "", "conf": 0.0},
        {"frame": 2, "text": "   ", "conf": 0.0},
    ]
    res = consensus_plate(reads)
    assert res["plate_text"] == ""
    assert res["consensus_method"] == "single_frame"


def test_single_read():
    reads = [
        {"frame": 1, "text": "KA05MH1234", "conf": 0.9},
    ]
    res = consensus_plate(reads)
    assert res["plate_text"] == "KA05MH1234"
    assert res["consensus_method"] == "single_frame"


def test_voting_tie():
    # Tie between 'B' and '8' at pos 2
    # Confidences are perfectly equal
    reads = [
        {"frame": 1, "text": "KAB5MH1234", "conf": 0.9},
        {"frame": 2, "text": "KA85MH1234", "conf": 0.9},
        {"frame": 3, "text": "KAX5MH1234", "conf": 0.1},
    ]
    res = consensus_plate(reads)
    # Python max() returns the first one encountered in the case of a tie
    # so it should be 'B' or '8' depending on dict ordering
    assert res["plate_text"][2] in ("B", "8")
    assert res["consensus_method"] == "character_vote"


if __name__ == "__main__":
    tests = [
        test_clean_agreement,
        test_substitution_noise,
        test_mixed_lengths,
        test_all_empty,
        test_single_read,
        test_voting_tie
    ]
    
    passed = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
            passed += 1
        except AssertionError:
            print(f"FAIL: {test.__name__}")
        except Exception as e:
            print(f"ERROR: {test.__name__} - {e}")
            
    print(f"\n{passed}/{len(tests)} tests passed.")
