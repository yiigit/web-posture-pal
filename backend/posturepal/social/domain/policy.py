"""Social content is private unless explicitly shared with accepted friends."""
def can_view(*, owner, viewer, audience, sharing_enabled, friends, blocked):
    return owner == viewer or (not blocked and sharing_enabled and audience == 'friends' and friends)
