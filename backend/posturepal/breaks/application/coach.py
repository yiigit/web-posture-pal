"""Break coaching content, independent of exercise catalog mutations."""
from posturepal.breaks.domain.models import BreakRoutine, PostureCheck, DailyHabit


class BreakCoach:
    def routines(self) -> list[BreakRoutine]:
        return [
            BreakRoutine('standard', 'Standard break', 'Step away, change position, and return refreshed.', 120,
                         ('Pause your work and relax your hands.', 'Stand up if comfortable, or change your seated position.',
                          'Walk at an easy pace or gently move your feet while seated.', 'Return when ready and settle into a comfortable position.'),
                         'Adapt the movement to your space and ability. Stop if uncomfortable.'),
            BreakRoutine('pain-relief', 'Pain relief', 'A gentle comfort break for a tense workday.', 90,
                         ('Pause the activity that feels uncomfortable.', 'Find a supported position and let your shoulders relax.',
                          'Take a few natural breaths. Only move within a comfortable range.', 'Adjust your setup before returning to work.'),
                         'A comfort break, not treatment. Do not stretch through pain. Stop if symptoms worsen; seek medical advice for persistent or severe pain.'),
            BreakRoutine('strength', 'Strength break', 'A short, controlled seated leg movement.', 120,
                         ('Use a sturdy chair without wheels, with feet flat on the floor.',
                          'Sit comfortably upright. Slowly straighten one leg as far as comfortable.',
                          'Lower it with control. Alternate legs for a few easy repetitions.', 'Rest whenever needed; the timer is a guide, not a repetition target.'),
                         'Start gently. Skip this routine if it is unsuitable for you, and stop if it causes pain or dizziness.'),
            BreakRoutine('movement-habit', 'Movement habit', 'Connect a small movement to something you already do.', 60,
                         ('Pick a cue: finishing a task, a call ending, or getting a drink.',
                          'When that cue happens, change position or take a short walk if comfortable.',
                          'Choose a small action you can repeat without pressure.', 'Notice the action you completed and carry on with your day.'),
                         'Choose an action that is comfortable and accessible for you.'),
        ]

    def checks(self) -> list[PostureCheck]:
        return [
            PostureCheck('desk', 'At your desk', (
                'Feet supported on the floor or a footrest.',
                'Back comfortably supported; shoulders relaxed.',
                'Keyboard and mouse close enough to keep elbows near your body.',
                'Screen positioned so you can look ahead without craning your neck.',
                'Change position regularly rather than holding one rigid posture.',
            )),
            PostureCheck('phone', 'Using your phone', (
                'Support your arms and bring the screen toward a comfortable viewing height.',
                'Relax your shoulders and avoid holding your neck bent for long periods.',
                'Use a headset or speaker for calls instead of pinching the phone against your shoulder.',
                'Switch hands, pause scrolling, and change position when comfortable.',
            )),
        ]

    def habits(self) -> list[DailyHabit]:
        return [
            DailyHabit('first-task', 'Start with a position change', 'After your first task, stand or adjust your seated position.'),
            DailyHabit('walk-reset', 'Take a movement break', 'Between tasks, walk a little or move comfortably while seated.'),
            DailyHabit('desk-check', 'Check your desk setup', 'When you sit down, check your support and screen position.'),
            DailyHabit('phone-check', 'Reset your phone posture', 'Before a call or scrolling session, relax and support your arms.'),
        ]
