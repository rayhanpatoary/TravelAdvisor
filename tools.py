def calculate_trip_budget(
    accommodation: float,
    food: float,
    transportation: float,
    activities: float,
    extras: float
) -> dict:

    costs = {
        "accommodation": accommodation,
        "food": food,
        "transportation": transportation,
        "activities": activities,
        "extras": extras
    }

    if any(value < 0 for value in costs.values()):
        raise ValueError("Budget values cannot be negative.")

    total = sum(costs.values())

    return {
        "costs": costs,
        "total": round(total, 2),
        "currency": "EUR"
    }


BUDGET_TOOL = {
    "type": "function",
    "name": "calculate_trip_budget",
    "description": "Calculate the total estimated trip budget from five expense categories in EUR.",
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


def verify_budget_arguments(
    arguments: dict,
    expected: dict
) -> bool:

    return all(
        arguments.get(key) == value
        for key, value in expected.items()
    )


def suggest_activities(
    destination: str,
    interests: list[str]
) -> dict:

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
                "description": "Destination city: Rome or Paris."
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