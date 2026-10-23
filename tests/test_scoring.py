import pytest

from class_quality.schemas import EvidenceEvent
from class_quality.scoring import DeterministicRubricScorer, _label


@pytest.mark.parametrize(
    ("score", "expected"),
    [(0, "Poor"), (44.9, "Poor"), (45, "Average"), (59.9, "Average"), (60, "Good"), (74.9, "Good"), (75, "Excellent")],
)
def test_label_thresholds(score, expected):
    assert _label(score) == expected


def test_repeated_rapport_events_do_not_inflate_distinct_kind_count():
    events = [
        EvidenceEvent(
            dimension="rapport",
            kind="rapport_exchange",
            start_sec=index * 10,
            end_sec=index * 10 + 2,
            evidence_quote=f"Hello class {index}",
            observation="The transcript shows a welcome exchange.",
        )
        for index in range(3)
    ]
    result = DeterministicRubricScorer().score("synthetic.vtt", 600, events)
    one_event_result = DeterministicRubricScorer().score("synthetic.vtt", 600, events[:1])
    rapport = next(item for item in result.dimensions if item.name == "rapport")
    one_event_rapport = next(item for item in one_event_result.dimensions if item.name == "rapport")
    assert rapport.event_count == 3
    assert rapport.score == 100
    assert rapport.score == one_event_rapport.score
