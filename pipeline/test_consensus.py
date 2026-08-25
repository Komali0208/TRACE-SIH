"""Unit tests for pipeline.consensus.vote_consensus."""

import sys
import os

# Ensure the pipeline package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.consensus import vote_consensus


class TestVoteConsensus:
    """Test suite for multi-frame character-level consensus voting."""

    def test_empty_reads(self):
        text, conf, method = vote_consensus([])
        assert text == ""
        assert conf == 0.0
        assert method == "single_frame"

    def test_all_empty_strings(self):
        reads = [
            {"text": "", "conf": 0.5},
            {"text": "", "conf": 0.3},
        ]
        text, conf, method = vote_consensus(reads)
        assert text == ""
        assert method == "single_frame"

    def test_single_read_fallback(self):
        reads = [{"text": "KA05MH1234", "conf": 0.9}]
        text, conf, method = vote_consensus(reads)
        assert text == "KA05MH1234"
        assert conf == 0.9
        assert method == "single_frame"

    def test_two_reads_fallback(self):
        reads = [
            {"text": "KA05MH1234", "conf": 0.8},
            {"text": "KA05MH1235", "conf": 0.9},
        ]
        text, conf, method = vote_consensus(reads)
        # Should pick the higher-confidence read
        assert text == "KA05MH1235"
        assert conf == 0.9
        assert method == "single_frame"

    def test_three_identical_reads_character_vote(self):
        reads = [
            {"text": "KA05MH1234", "conf": 0.9},
            {"text": "KA05MH1234", "conf": 0.85},
            {"text": "KA05MH1234", "conf": 0.88},
        ]
        text, conf, method = vote_consensus(reads)
        assert text == "KA05MH1234"
        assert method == "character_vote"
        # Mean of 0.9, 0.85, 0.88
        assert abs(conf - 0.8766666) < 0.01

    def test_majority_vote_resolves_disagreement(self):
        """Two reads agree on a character, one disagrees — majority wins."""
        reads = [
            {"text": "KA05MH1234", "conf": 0.9},
            {"text": "KA05MH1234", "conf": 0.85},
            {"text": "KA05MH1Z34", "conf": 0.8},  # 'Z' at position 7
        ]
        text, conf, method = vote_consensus(reads)
        assert text == "KA05MH1234"  # '2' should win at position 7
        assert method == "character_vote"

    def test_confidence_weighting_breaks_ties(self):
        """When count is tied, higher total confidence wins."""
        reads = [
            {"text": "KA05MH1234", "conf": 0.5},
            {"text": "KA05MH1834", "conf": 0.9},  # '8' at position 7 with high conf
            {"text": "KA05MH1834", "conf": 0.85}, # '8' again
        ]
        text, conf, method = vote_consensus(reads)
        # Position 7: '2' has 0.5 weight, '8' has 0.9+0.85=1.75 → '8' wins
        assert text == "KA05MH1834"
        assert method == "character_vote"

    def test_length_tolerance_filters_outliers(self):
        """Reads more than ±1 off modal length are discarded."""
        reads = [
            {"text": "KA05MH1234", "conf": 0.9},   # len 10 (modal)
            {"text": "KA05MH1234", "conf": 0.85},   # len 10
            {"text": "KA05MH1234", "conf": 0.88},   # len 10
            {"text": "KA05MH12",   "conf": 0.7},    # len 8 — off by 2, filtered
            {"text": "KA05MH1234567", "conf": 0.6},  # len 13 — off by 3, filtered
        ]
        text, conf, method = vote_consensus(reads)
        assert text == "KA05MH1234"
        assert method == "character_vote"

    def test_plus_minus_one_length_kept(self):
        """Reads within ±1 of modal length are kept (but aligned ones match vote_len)."""
        reads = [
            {"text": "KA05MH1234", "conf": 0.9},    # len 10 (modal)
            {"text": "KA05MH1234", "conf": 0.85},   # len 10
            {"text": "KA05MH1234", "conf": 0.88},   # len 10
            {"text": "KA05MH123",  "conf": 0.7},    # len 9 — within ±1, kept but not aligned
        ]
        text, conf, method = vote_consensus(reads)
        assert text == "KA05MH1234"
        assert method == "character_vote"

    def test_all_reads_filtered_out(self):
        """If after length filter fewer than 3 remain, fall back to best."""
        reads = [
            {"text": "KA05MH1234", "conf": 0.9},    # len 10
            {"text": "KA05", "conf": 0.7},            # len 4 — way off
            {"text": "KA0", "conf": 0.6},              # len 3 — way off
        ]
        text, conf, method = vote_consensus(reads)
        # Modal len is 10 (only one with len 10), others are off by >1
        # Only 1 read survives → single_frame
        assert text == "KA05MH1234"
        assert method == "single_frame"


def run_tests():
    """Simple test runner without pytest dependency."""
    test = TestVoteConsensus()
    methods = [m for m in dir(test) if m.startswith("test_")]
    passed = 0
    failed = 0
    for name in methods:
        try:
            getattr(test, name)()
            print(f"  PASS {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  FAIL {name}: UNEXPECTED {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    return failed == 0


if __name__ == "__main__":
    print("Running consensus voting tests...\n")
    success = run_tests()
    sys.exit(0 if success else 1)

