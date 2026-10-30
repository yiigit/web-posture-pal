from fastapi import APIRouter

from posturepal.breaks.application.coach import BreakCoach
from posturepal.breaks.domain.models import BreakRoutine, PostureCheck, DailyHabit


def create_break_router(coach: BreakCoach) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['Break coaching'])

    @router.get('/breaks', response_model=list[BreakRoutine])
    def routines():
        return coach.routines()

    @router.get('/posture-checks', response_model=list[PostureCheck])
    def checks():
        return coach.checks()

    @router.get('/daily-habits', response_model=list[DailyHabit])
    def habits():
        return coach.habits()

    return router
