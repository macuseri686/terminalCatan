from __future__ import annotations

from typing import List
import random


DevCard = str  # "knight", "road_building", "year_of_plenty", "monopoly", "victory_point"


def build_standard_deck() -> List[DevCard]:
    deck: List[DevCard] = []
    deck += ["knight"] * 14
    deck += ["victory_point"] * 5
    deck += ["road_building"] * 2
    deck += ["year_of_plenty"] * 2
    deck += ["monopoly"] * 2
    random.shuffle(deck)
    return deck

