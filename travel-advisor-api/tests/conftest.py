import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def costs():
    return dict(accommodation=360, food=180, transportation=45, activities=95, extras=40)


@pytest.fixture
def trip(costs):
    return dict(title="Rome Discovery", destination="Rome", duration_days=1,
        interests=["history", "food"], summary="A day of Roman culture.",
        days=[dict(day_number=1, morning="Colosseum", afternoon="Roman Forum",
            evening="Trastevere", places=["Colosseum"], food_suggestion="Pasta")],
        budget={**costs, "flights": None, "currency": "EUR"}, practical_tips=["Book ahead."])
