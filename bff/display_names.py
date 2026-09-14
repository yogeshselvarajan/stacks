# bff/display_names.py
"""Human-readable display names for the demo dataset's internal IDs
(room_id, patron_id, item_id), used only to shape read-endpoint
responses -- never the data model or DynamoDB schema itself. Kept as a
lookup layer, not a data-model change, so it carries zero risk to Plan
3's already-provisioned tables or its currently-running soak test.

Every getter falls back to the raw id when it has no mapping, so an id
this module has never heard of (a new fixture, a live soak-test record)
degrades to showing its raw id rather than crashing or disappearing.
"""
from __future__ import annotations

_ROOM_NAMES: dict[str, str] = {
    "room_a": "Story Room",
    "room_b": "Community Room B",
}

_PATRON_NAMES: dict[str, str] = {
    "patron_recurring": "Library Programs Team",
    "patron_renter": "Community Book Club",
    "patron_teen_group": "Teen Coding Club",
    "patron_walkin": "Walk-in Patron",
    "patron_overdue_1": "Maria Chen",
    "patron_overdue_2": "James Okafor",
    "patron_overdue_3": "Priya Nair",
    "patron_overdue_4": "Sam Whitfield",
    "patron_ill_1": "Devi Kapoor",
    "patron_ill_2": "Marcus Lindqvist",
    "patron_ill_3": "Aaliyah Robinson",
    "patron_ill_4": "Tom Sackville",
    "patron_ill_5": "Fatima Idris",
    # Plan 3's real, currently-running Overdue Sequencer soak test writes
    # this record directly to DynamoDB (scripts/seed_overdue_soak_case.py)
    # -- named honestly here rather than given a fake patron name, so it
    # never reads as a real person in a demo.
    "patron_soak_test": "Soak-Test Patron (system check, not a real patron)",
}

_ITEM_TITLES: dict[str, str] = {
    "item_1": "The Great Gatsby",
    "item_2": "Educated: A Memoir",
    "item_3": "Sapiens: A Brief History of Humankind",
    "item_4": "The Girl with the Dragon Tattoo",
    "item_soak_test": "Soak-Test Verification Item",
}


def room_name(room_id: str) -> str:
    return _ROOM_NAMES.get(room_id, room_id)


def patron_name(patron_id: str) -> str:
    return _PATRON_NAMES.get(patron_id, patron_id)


def item_title(item_id: str) -> str:
    return _ITEM_TITLES.get(item_id, item_id)
