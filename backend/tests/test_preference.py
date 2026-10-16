import pytest

from floodroute.risk import DEFAULT_ALPHA, BodyPart, TravellerProfile
from floodroute.risk.preference import DEFAULT_PREFERENCE, RoutePreference, explain


def test_preferences_get_stricter_in_order():
    alphas = [p.alpha for p in RoutePreference]
    assert alphas == sorted(alphas) and len(set(alphas)) == len(alphas)
    assert DEFAULT_PREFERENCE.alpha == DEFAULT_ALPHA  # "Balanced" is the routing default


@pytest.mark.parametrize(
    "preference, metres",
    [
        (RoutePreference.SHORTEST, 20),  # 0.5 × 0.754 × 50 = 18.9
        (RoutePreference.BALANCED, 75),  # 2 × 0.754 × 50 = 75.4
        (RoutePreference.AVOID_WATER, 190),  # 5 × 0.754 × 50 = 188.5
        (RoutePreference.DRIEST, 570),  # 15 × 0.754 × 50 = 565.6
    ],
)
def test_explanation_for_an_adult_with_an_ankle_limit(preference, metres):
    # Limit 6.63 cm; the example uses 75% of it, 5 cm, so R = 0.05 / 0.0663 = 0.754.
    text = explain(preference.alpha, TravellerProfile(1.70, BodyPart.ANKLE))
    assert "50 m of water 5 cm deep (up to the ankle)" in text
    assert f"about {metres} m further" in text


def test_explanation_follows_the_travellers_own_limit():
    text = explain(2.0, TravellerProfile(1.70, BodyPart.MID_CALF))  # limit 27.5 cm, example 21 cm
    assert "21 cm deep (up to the mid calf)" in text and "about 75 m further" in text


def test_no_effect_for_people_who_will_not_wade():
    for profile in (TravellerProfile(1.70), TravellerProfile(1.70, BodyPart.MID_CALF, uses_wheelchair=True)):
        assert "no effect" in explain(5.0, profile)
