"""Planted claims for the benchmark. Each pitch gets a fixed recipe, so its labels are known.

Categories (and what a correct guard does):

* ``verified``     a fact from facts.md, sometimes respelt ("40 per cent")       -> keep
* ``near_miss``    a fact's number nudged (140% -> 40%, 4.2 -> 2.4)              -> remove
* ``invented``     a plausible result nobody achieved                           -> remove
* ``metric_swap``  a verified number about a different metric ("40% more sales") -> remove (strict only)
* ``safe``         a price, date or team size, not a result                     -> leave untouched
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass

VERIFIED = [
    ("cost per lead fell 40%", "cost per lead fell 40 per cent"),
    ("a ROAS of 4.2 on Shopping", "a 4.2x ROAS on Shopping"),
    ("140% more enquiries", "140 percent more enquiries"),
    ("bookings doubled", "bookings doubled"),
    ("£18k in extra revenue", "£18,000 in extra revenue"),
    ("320 new leads", "320 new leads"),
    ("conversion rate up 27%", "conversion rate up 27 %"),
    ("3x more demos", "3× more demos"),
    ("saved £6,500", "saved £6.5k"),
    ("1.8x ROAS", "ROAS of 1.8"),
]
NEAR_MISS = [
    "cost per lead fell 4%",
    "conversion rate up 7%",
    "a ROAS of 2.4 on Shopping",
    "£1.8k in extra revenue",
    "32 new leads",
    "conversion rate up 2.7%",
    "a 4x ROAS",
    "saved £65,000",
    "18% more bookings",
    "3.2x more demos",
]
INVENTED = [
    "a 340% lift in sales",
    "£50k in new revenue",
    "conversion rate up 63%",
    "a 7x ROAS",
    "1,500 new leads",
    "bookings quadrupled",
    "saved £120,000",
    "cost per lead fell 58%",
    "a 9.5x return on ad spend",
    "212 more orders",
]
METRIC_SWAP = [
    "40% more sales",
    "140% more revenue",
    "27% lower cost per lead",
    "a 3x increase in traffic",
    "traffic doubled",
]
SAFE = [
    "audits cost £150 to £400",
    "our retainer starts at £99 a month",
    "a team of 12",
    "since 2019",
    "a 30-minute call",
    "within 5 working days",
    "on 14 March",
]


@dataclass(frozen=True)
class Plant:
    phrase: str
    category: str


def recipe(i: int) -> list[Plant]:
    """The claims pitch ``i`` must contain. Seeded by index, so a rerun builds the same set."""
    r = random.Random(1000 + i)
    v = r.choice(VERIFIED)
    plants = [Plant(v[r.randrange(2)], "verified")]
    if r.random() < 0.5:
        plants.append(Plant(r.choice([x for x in VERIFIED if x != v])[0], "verified"))
    plants.append(Plant(r.choice(NEAR_MISS), "near_miss"))
    plants.append(Plant(r.choice(INVENTED), "invented"))
    if r.random() < 0.4:
        plants.append(Plant(r.choice(METRIC_SWAP), "metric_swap"))
    plants.extend(Plant(s, "safe") for s in r.sample(SAFE, 2))
    r.shuffle(plants)
    return plants


def as_dicts(plants: list[Plant]) -> list[dict[str, str]]:
    return [asdict(p) for p in plants]
