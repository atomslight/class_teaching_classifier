from pathlib import Path

import pytest

from class_quality.vtt import parse_vtt_file


@pytest.fixture
def strong_segments():
    return parse_vtt_file(Path(__file__).parent / "fixtures" / "strong_class.vtt")


@pytest.fixture
def weak_segments():
    return parse_vtt_file(Path(__file__).parent / "fixtures" / "weak_class.vtt")
