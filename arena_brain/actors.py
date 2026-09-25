from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActorProfile:
    actor_id: str
    role: str
    authority: str
    pace: str
    detail_appetite: str
    warmth: str
    challenge_style: str
    action_bias: str


ACTORS: dict[str, ActorProfile] = {
    "priya": ActorProfile(
        actor_id="priya",
        role="Service Owner",
        authority="high",
        pace="fast",
        detail_appetite="medium",
        warmth="medium",
        challenge_style="indirect",
        action_bias="high",
    ),
    "marcus": ActorProfile(
        actor_id="marcus",
        role="Test Lead",
        authority="medium",
        pace="medium",
        detail_appetite="high",
        warmth="medium",
        challenge_style="direct",
        action_bias="medium",
    ),
    "dana": ActorProfile(
        actor_id="dana",
        role="Integration SME",
        authority="medium",
        pace="medium",
        detail_appetite="high",
        warmth="medium",
        challenge_style="low",
        action_bias="medium",
    ),
}


def get_actor(actor_id: str | None) -> ActorProfile | None:
    if actor_id is None:
        return None
    return ACTORS.get(actor_id.lower())

