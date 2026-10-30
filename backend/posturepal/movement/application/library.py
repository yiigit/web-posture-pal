from posturepal.movement.domain.models import Exercise, ExerciseRepository

class MovementLibrary:
    def __init__(self, repository: ExerciseRepository):
        self.repository = repository

    def search(self, query: str = "", area: str = "") -> list[Exercise]:
        return [exercise for exercise in self.repository.all()
                if (not area or exercise.area.casefold() == area.casefold())
                and query.casefold() in f"{exercise.name} {exercise.description} {exercise.area}".casefold()]

    def get(self, exercise_id: str) -> Exercise | None:
        return next((exercise for exercise in self.repository.all() if exercise.id == exercise_id), None)

    def create(self, exercise: Exercise) -> Exercise:
        return self.repository.create(exercise)

    def update(self, exercise: Exercise) -> Exercise:
        return self.repository.update(exercise)

    def delete(self, exercise_id: str) -> None:
        self.repository.delete(exercise_id)

    def dashboard(self) -> dict:
        exercises = self.repository.all()
        areas = ('Neck', 'Shoulders', 'Back', 'Wrists', 'Legs', 'Full body')
        total_duration = sum(item.duration for item in exercises)
        return {
            'total_exercises': len(exercises),
            'total_duration_seconds': total_duration,
            'average_duration_seconds': round(total_duration / len(exercises)) if exercises else 0,
            'quick_breaks': sum(item.duration <= 60 for item in exercises),
            'body_areas': [{'area': area, 'count': sum(item.area == area for item in exercises)} for area in areas],
            'positions': [{'position': position, 'count': sum(item.position == position for item in exercises)}
                          for position in ('Seated', 'Standing', 'Seated or standing')],
        }
