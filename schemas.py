from pydantic import BaseModel, Field
from typing import Literal


class DayPlan(BaseModel):
    day_number: int = Field(ge=1)
    morning: str
    afternoon: str
    evening: str
    places: list[str]
    food_suggestion: str


class TripBudget(BaseModel):
    accommodation: float = Field(ge=0)
    food: float = Field(ge=0)
    transportation: float = Field(ge=0)
    activities: float = Field(ge=0)
    extras: float = Field(ge=0)
    flights: float | None
    currency: str


class TripPlan(BaseModel):
    title: str
    destination: str
    duration_days: int = Field(ge=1)
    interests: list[str]
    summary: str
    days: list[DayPlan]
    budget: TripBudget
    practical_tips: list[str]


class TravelResponse(BaseModel):
    status: Literal["needs_info", "ready"]
    question: str | None
    trip: TripPlan | None


class BudgetToolInput(BaseModel):
    accommodation: float = Field(ge=0, le=100000)
    food: float = Field(ge=0, le=100000)
    transportation: float = Field(ge=0, le=100000)
    activities: float = Field(ge=0, le=100000)
    extras: float = Field(ge=0, le=100000)


class ToolResponse(BaseModel):
    answer: str
    tool_used: Literal[
        "calculate_trip_budget",
        "suggest_activities",
        "none"
    ]