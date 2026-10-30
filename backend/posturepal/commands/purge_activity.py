"""Purge expired account activity without logging personal data."""
from posturepal.shared.infrastructure.database import Database
from posturepal.activity.infrastructure.repository import ActivityRepository
from posturepal.activity.application.tracker import ActivityTracker

if __name__=='__main__':
    repository=ActivityRepository(Database.configured())
    count=repository.purge(ActivityTracker.today())
    print(f'Removed {count} expired daily activity rows.')
