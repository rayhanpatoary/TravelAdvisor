"""Notebook models, with runtime validation shared by the API and tools."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Annotated[float, Field(ge=0, le=100000, allow_inf_nan=False, strict=True)]
Text = Annotated[str, Field(min_length=1, max_length=4000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DayPlan(StrictModel):
    day_number: int = Field(ge=1, le=30, strict=True)
    morning: Text
    afternoon: Text
    evening: Text
    places: list[Text] = Field(min_length=1, max_length=20)
    food_suggestion: Text


class TripBudget(StrictModel):
    accommodation: Money
    food: Money
    transportation: Money
    activities: Money
    extras: Money
    flights: Money | None
    currency: Literal["EUR"]


class TripPlan(StrictModel):
    title: Text
    destination: Text
    duration_days: int = Field(ge=1, le=30, strict=True)
    interests: list[Text] = Field(min_length=1, max_length=20)
    summary: Text
    days: list[DayPlan] = Field(min_length=1, max_length=30)
    budget: TripBudget
    practical_tips: list[Text] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def matching_days(self):
        if [day.day_number for day in self.days] != list(range(1, self.duration_days + 1)):
            raise ValueError("Daily plans must match duration in order without duplicates.")
        return self


class TravelResponse(StrictModel):
    status: Literal["needs_info", "ready"]
    question: Text | None
    trip: TripPlan | None

    @model_validator(mode="after")
    def matching_status(self):
        if self.status == "ready" and (self.trip is None or self.question is not None):
            raise ValueError("A ready response needs a trip and no question.")
        if self.status == "needs_info" and (not self.question or self.trip is not None):
            raise ValueError("A needs_info response needs a question and no trip.")
        return self


class BudgetToolInput(StrictModel):
    accommodation: Money
    food: Money
    transportation: Money
    activities: Money
    extras: Money
    flights: Money | None = None


class BudgetValues(StrictModel):
    """Explicit user figures; absent values are not silently treated as zero."""
    accommodation: Money | None = None
    food: Money | None = None
    transportation: Money | None = None
    activities: Money | None = None
    extras: Money | None = None
    flights: Money | None = None


class ActivityToolInput(StrictModel):
    destination: Annotated[str, Field(min_length=1, max_length=120)]
    interests: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(min_length=1, max_length=20)


class BudgetToolResult(StrictModel):
    costs: BudgetToolInput
    total: Annotated[float, Field(ge=0, le=600000, allow_inf_nan=False, strict=True)]
    flights_included: bool = Field(strict=True)
    currency: Literal["EUR"]


class ActivityToolResult(StrictModel):
    source: Literal["local_database"]
    supported_destination: bool = Field(strict=True)
    fallback: Text
    destination: Text
    interests: list[Text]
    suggested_activities: list[Text]


class ToolResponse(StrictModel):
    answer: Annotated[str, Field(min_length=1)]
    tool_used: Literal["calculate_trip_budget", "suggest_activities", "none"]


class ChatRequest(StrictModel):
    message: Annotated[str, Field(min_length=1, max_length=8000)]
    previous_response_id: Annotated[str, Field(pattern=r"^resp_[A-Za-z0-9_-]{1,250}$")] | None = None
    expected_budget: BudgetValues | None = None
    budget_context: Annotated[str, Field(max_length=5000)] | None = None
