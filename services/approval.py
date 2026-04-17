"""Approval workflow transitions + decision log audit trail."""
from __future__ import annotations

from models import ContentIdea, DecisionLogEntry, IdeaStatus
from storage import get_repository


ALLOWED_TRANSITIONS: dict[IdeaStatus, set[IdeaStatus]] = {
    IdeaStatus.DRAFT: {IdeaStatus.NEEDS_REVIEW, IdeaStatus.REJECTED},
    IdeaStatus.NEEDS_REVIEW: {
        IdeaStatus.APPROVED,
        IdeaStatus.REJECTED,
        IdeaStatus.DRAFT,
    },
    IdeaStatus.APPROVED: {IdeaStatus.SCHEDULED, IdeaStatus.REJECTED, IdeaStatus.NEEDS_REVIEW},
    IdeaStatus.SCHEDULED: {IdeaStatus.POSTED, IdeaStatus.APPROVED, IdeaStatus.REJECTED},
    IdeaStatus.POSTED: set(),
    IdeaStatus.REJECTED: {IdeaStatus.DRAFT},
}


class ApprovalError(ValueError):
    pass


def transition_idea_status(
    idea: ContentIdea,
    new_status: IdeaStatus,
    *,
    actor: str = "user",
    note: str = "",
) -> ContentIdea:
    if new_status == idea.status:
        return idea
    allowed = ALLOWED_TRANSITIONS.get(idea.status, set())
    if new_status not in allowed:
        raise ApprovalError(
            f"Cannot move idea {idea.id} from {idea.status.value} to {new_status.value}"
        )
    old = idea.status
    idea.status = new_status
    idea.touch()

    repo = get_repository()
    repo.save_idea(idea)
    repo.add_decision(
        DecisionLogEntry(
            entity_type="idea",
            entity_id=idea.id,
            action=f"transition:{old.value}->{new_status.value}",
            from_status=old.value,
            to_status=new_status.value,
            actor=actor,
            note=note,
        )
    )
    return idea
