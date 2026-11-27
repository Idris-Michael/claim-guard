from pathlib import Path

from claim_guard import PLACEHOLDER, VerifiedSource, guard
from claim_guard.baseline import baseline_guard
from claim_guard.cli import main

FACTS = """
- Northgate Dental: cost per lead fell 40% after the GA4 rebuild.
- Halden Outdoor: ROAS of 4.2 on Shopping over 90 days.
- Kestrel Legal: 140% more enquiries from organic search.
"""


def test_verified_claims_survive_in_any_spelling():
    r = guard("We cut cost per lead by 40 % and hit a 4.2x ROAS.", FACTS)
    assert r.removed == []
    assert PLACEHOLDER not in r.text


def test_invented_claims_are_replaced():
    r = guard("Clients typically see a 340% lift and £50k in new revenue.", FACTS)
    assert r.removed == ["340%", "£50k"]
    assert "340" not in r.text and "50k" not in r.text
    assert f"{PLACEHOLDER} in new revenue" in r.text  # the sentence still reads


def test_a_near_miss_value_is_not_verified_by_a_longer_number():
    # The substring check let "40%" through because "140%" is in the facts. Values must match exactly.
    facts = "Kestrel Legal: 140% more enquiries from organic search."
    draft = "Enquiries rose 40% and leads 1.4x."
    assert guard(draft, facts).removed == ["40%", "1.4x"]
    _, baseline_removed = baseline_guard(draft, facts)
    assert baseline_removed == ["1.4x"]  # the old guard's blind spot, kept as a regression record


def test_strict_mode_rejects_a_verified_value_used_for_a_different_metric():
    draft = "Our clients see 40% more sales."
    assert guard(draft, FACTS, "value").removed == []
    r = guard(draft, FACTS, "strict")
    assert r.removed == ["40%"]
    assert r.findings[0].reason == "value is verified, but for a different metric"


def test_strict_mode_keeps_a_verified_value_for_the_same_metric():
    assert guard("Cost per lead fell 40%.", FACTS, "strict").removed == []


def test_strict_mode_does_not_punish_a_sentence_with_no_metric_word():
    assert guard("That project reached 40%.", FACTS, "strict").removed == []


def test_adjacent_placeholders_collapse_to_one():
    r = guard("A 300% / 5x improvement.", FACTS)
    assert r.text.count(PLACEHOLDER) == 1


def test_empty_source_fails_closed():
    assert guard("We cut cost per lead by 40%.", "").removed == ["40%"]


def test_prices_pass_through_untouched():
    draft = "The audit is £150–£400 and takes 3 days."
    assert guard(draft, "").text == draft


def test_a_parsed_source_can_be_reused():
    src = VerifiedSource(FACTS)
    assert guard("40% lower cost per lead", src).removed == []
    assert len(src.claims) == 3


def test_cli_exit_code_gates_a_pipeline(tmp_path: Path, capsys):
    facts = tmp_path / "facts.md"
    facts.write_text(FACTS, encoding="utf-8")
    ok = tmp_path / "ok.txt"
    ok.write_text("ROAS of 4.2 on Shopping.", encoding="utf-8")
    bad = tmp_path / "bad.txt"
    bad.write_text("A 9x ROAS, guaranteed.", encoding="utf-8")
    assert main([str(ok), "--facts", str(facts)]) == 0
    assert main([str(bad), "--facts", str(facts), "--strict"]) == 1
    err = capsys.readouterr().err
    assert "REMOVED" in err and "kept" in err


def test_cli_with_unreadable_facts_removes_everything(tmp_path: Path, capsys):
    d = tmp_path / "d.txt"
    d.write_text("ROAS of 4.2.", encoding="utf-8")
    assert main([str(d), "--facts", str(tmp_path / "missing.md")]) == 1
    assert "cannot read facts" in capsys.readouterr().err
