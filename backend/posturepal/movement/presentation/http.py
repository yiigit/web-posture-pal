"""Validated HTTP contracts and authorization for the movement context."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from posturepal.movement.application.library import MovementLibrary
from posturepal.movement.domain.models import Exercise, DuplicateExercise, MissingExercise

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Step = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class ExerciseWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Annotated[Text, Field(max_length=100)]
    area: Literal['Neck', 'Shoulders', 'Back', 'Wrists', 'Legs', 'Full body']
    duration: int = Field(ge=5, le=3600, strict=True)
    description: Text
    steps: list[Step] = Field(min_length=1, max_length=20)
    position: Literal['Seated', 'Standing', 'Seated or standing']
    symbol: Literal['neck', 'shoulders', 'twist', 'chest', 'wrists', 'reach', 'legs', 'walk']

    def entity(self, exercise_id):
        return Exercise(id=exercise_id, **self.model_dump(exclude={'steps'}), steps=tuple(self.steps))


class ExerciseCreate(ExerciseWrite):
    id: str = Field(pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', min_length=1, max_length=80)

    def entity(self, exercise_id=None):
        data = self.model_dump(exclude={'id'})
        return Exercise(id=self.id, **{**data, 'steps': tuple(data['steps'])})


def create_router(library: MovementLibrary, require_admin) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['Movement library'])
    secured = [Depends(require_admin)]

    @router.get('/admin/session', dependencies=secured)
    def session():
        return {'role': 'admin'}

    @router.get('/admin/dashboard', dependencies=secured)
    def dashboard():
        return library.dashboard()

    @router.get('/exercises', response_model=list[Exercise])
    def list_exercises(q: str = '', area: str = ''):
        return library.search(q, area)

    @router.get('/exercises/{exercise_id}', response_model=Exercise)
    def get_exercise(exercise_id: str):
        exercise = library.get(exercise_id)
        if exercise is None:
            raise HTTPException(404, 'Exercise not found')
        return exercise

    @router.post('/exercises', response_model=Exercise, status_code=201, dependencies=secured)
    def create_exercise(payload: ExerciseCreate):
        try:
            return library.create(payload.entity())
        except DuplicateExercise:
            raise HTTPException(409, 'Exercise ID already exists') from None

    @router.put('/exercises/{exercise_id}', response_model=Exercise, dependencies=secured)
    def update_exercise(exercise_id: str, payload: ExerciseWrite):
        try:
            return library.update(payload.entity(exercise_id))
        except MissingExercise:
            raise HTTPException(404, 'Exercise not found') from None

    @router.delete('/exercises/{exercise_id}', status_code=204, dependencies=secured)
    def delete_exercise(exercise_id: str):
        try:
            library.delete(exercise_id)
        except MissingExercise:
            raise HTTPException(404, 'Exercise not found') from None
        return Response(status_code=204)

    return router
