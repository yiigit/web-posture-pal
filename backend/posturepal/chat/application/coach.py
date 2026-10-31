class PersonalCoach:
    def __init__(self, activity, provider):
        self.activity = activity
        self.provider = provider

    def context(self, user, day):
        progress = self.activity.progress(user.id, day, days=7)
        return {
            'profile': {'display_name': user.display_name, 'timezone': user.timezone},
            'as_of': day.isoformat(),
            'activity_source': 'Self-reported; retained history only, not measured exercise',
            'progress': {key: progress[key] for key in
                         ('window_days', 'totals', 'points', 'level', 'level_progress', 'awards', 'history')},
        }

    def reply(self, user, day, messages):
        return self.provider.reply(self.context(user, day), messages)
