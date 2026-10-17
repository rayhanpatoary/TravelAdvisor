from decimal import Decimal, ROUND_HALF_UP
from schemas import BudgetToolInput, BudgetValues, ActivityToolInput


def calculate_trip_budget(
    accommodation: float,
    food: float,
    transportation: float,
    activities: float,
    extras: float,
    flights: float | None = None,
) -> dict:

    validated = BudgetToolInput(accommodation=accommodation, food=food,
        transportation=transportation, activities=activities, extras=extras, flights=flights)
    costs = validated.model_dump(exclude_none=True)
    total = sum(Decimal(str(value)) for value in costs.values())

    return {
        "costs": costs,
        "total": float(total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
        "flights_included": flights is not None,
        "currency": "EUR"
    }


BUDGET_TOOL = {
    "type": "function",
    "name": "calculate_trip_budget",
    "description": "Calculate whole-trip costs in EUR: five expense categories plus flights when known. Unknown flights must be null.",
    "parameters": {
        "type": "object",
        "properties": {
            "accommodation": {"type": "number"},
            "food": {"type": "number"},
            "transportation": {"type": "number"},
            "activities": {"type": "number"},
            "extras": {"type": "number"}
        },
        "required": [
            "accommodation",
            "food",
            "transportation",
            "activities",
            "extras"
        ],
        "additionalProperties": False
    },
    "strict": True
}

# Include optional flights consistently in strict tool calls and the Python total.
BUDGET_TOOL["parameters"]["properties"]["flights"] = {"type": ["number", "null"]}
BUDGET_TOOL["parameters"]["required"].append("flights")


def verify_budget_arguments(
    arguments: dict,
    expected: dict
) -> bool:

    try:
        actual = BudgetToolInput.model_validate(arguments).model_dump()
        reference = BudgetValues.model_validate(expected).model_dump(exclude_none=True)
        return all(actual[key] == value for key, value in reference.items())
    except (ValueError, TypeError):
        return False


def suggest_activities(
    destination: str,
    interests: list[str]
) -> dict:

    validated = ActivityToolInput(destination=destination, interests=interests)
    destination = validated.destination.title()
    interests = [interest.lower() for interest in validated.interests]
    activities_database = {
        "Rome": {
            "history": [
                "Visit the Colosseum",
                "Explore the Roman Forum"
            ],
            "food": [
                "Join a pasta cooking class",
                "Explore traditional Roman restaurants"
            ],
            "culture": [
                "Visit the Vatican Museums",
                "Explore Piazza Navona"
            ]
        },

        "Paris": {
            "history": [
                "Visit the Palace of Versailles",
                "Explore the Musée Carnavalet"
            ],
            "food": [
                "Join a French pastry workshop",
                "Explore local food markets"
            ],
            "culture": [
                "Visit the Louvre Museum",
                "Explore Montmartre"
            ]
        }
    }

    destination_activities = activities_database.get(
        destination, {}
    )

    suggestions = []

    for interest in interests:
        suggestions.extend(
            destination_activities.get(
                interest.lower(), []
            )
        )

    return {
        "source": "local_database",
        "supported_destination": destination in activities_database,
        "fallback": "Use clearly labelled AI suggestions if no local matches are available.",
        "destination": destination,
        "interests": interests,
        "suggested_activities": suggestions
    }


ACTIVITIES_TOOL = {
    "type": "function",
    "name": "suggest_activities",
    "description": (
        "Suggest activities based on a travel destination "
        "and the user's interests. Currently supports Rome and Paris."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "Destination city. Rome/Paris have local data; other places return a fallback indicator."
            },
            "interests": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": (
                    "Travel interests such as history, food or culture."
                )
            }
        },
        "required": [
            "destination",
            "interests"
        ],
        "additionalProperties": False
    },
    "strict": True
}
