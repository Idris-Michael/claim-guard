import pytest

from claim_guard.claims import find_claims


def keys(text: str) -> list[tuple[str, str]]:
    return [c.key for c in find_claims(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("conversion rate up 34%", [("percent", "34")]),
        ("a +34 % lift", [("percent", "34")]),
        ("grew 34 per cent", [("percent", "34")]),
        ("cut costs by 12.50 percent", [("percent", "12.5")]),
        ("a 3x return", [("multiplier", "3")]),
        ("3.0× more demos", [("multiplier", "3")]),
        ("4 times the traffic", [("multiplier", "4")]),
        ("bookings doubled", [("multiplier", "2")]),
        ("a ROAS of 4.2", [("multiplier", "4.2")]),
        ("a 4.2x ROAS", [("multiplier", "4.2")]),
        ("£12k in extra revenue", [("money", "GBP:12000")]),
        ("$1.2 million in pipeline", [("money", "USD:1200000")]),
        ("saved them £8,400", [("money", "GBP:8400")]),
        ("1,200 new leads", [("count", "1200:lead")]),
        # found in the wild set (model-chosen wording), run 1 missed all three
        ("viewings roughly triple in a quarter", [("multiplier", "3")]),
        ("Ads returned £4.20 for every £1 spent", [("multiplier", "4.2")]),
        ("adding [£240k] in pipeline", [("money", "GBP:240000")]),
        ("38 qualified sign-ups", [("count", "38:signup")]),
    ],
)
def test_result_claims_reduce_to_the_same_key_however_they_are_written(text, expected):
    assert keys(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Audits cost £150–£400 per project.",
        "Retainers start at £99 a month.",
        "Founded in 2019, a team of 12 in London.",
        "Call 020 7946 0958 or reply by 14 March.",
        "Runs on Python 3.12 and GA4.",
        "We work with 3 people on your side.",
        "Purchases were double counting in GA4.",
    ],
)
def test_prices_dates_and_versions_are_not_claims(text):
    # The guard must never mangle a price or a date: those are facts about us, not results.
    assert find_claims(text) == []


def test_overlapping_patterns_yield_one_claim():
    assert len(find_claims("ROAS of 4.2x")) == 1


def test_context_stays_inside_the_claims_own_sentence():
    # Run 1 regression: the line below leaked "roas" into this claim's context.
    (c, _) = find_claims("- Kestrel: 140% more enquiries.\n- Halden: ROAS of 4.2")
    assert c.context == frozenset({"enquiries"})


def test_context_records_what_the_number_measures():
    (c,) = find_claims("cost per lead fell 40% in a month")
    assert "cost" in c.context and "lead" in c.context
