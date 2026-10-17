"""Bounded Responses API tool workflow, adapted from the merged notebook."""
import json
import re
from openai import OpenAI
from pydantic import ValidationError
from schemas import (BudgetToolInput, BudgetValues, ActivityToolInput, TravelResponse,
    ToolResponse, BudgetToolResult, ActivityToolResult)
from tools import BUDGET_TOOL, ACTIVITIES_TOOL, calculate_trip_budget, suggest_activities, verify_budget_arguments
from prompts import SYSTEM_PROMPT
from budget_context import extract_budget_values


class EngineError(Exception):
    def __init__(self, code, message, status=502):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def execute_tool(call, expected_budget):
    try:
        arguments = json.loads(call.arguments)
        if not isinstance(arguments, dict):
            raise ValueError()
        if call.name == "calculate_trip_budget":
            validated = BudgetToolInput.model_validate(arguments)
            if not verify_budget_arguments(validated.model_dump(), expected_budget):
                raise EngineError("budget_mismatch", "The AI attempted to change your supplied costs. Please try again.")
            return BudgetToolResult.model_validate(calculate_trip_budget(**validated.model_dump())).model_dump(exclude_none=True)
        if call.name == "suggest_activities":
            validated = ActivityToolInput.model_validate(arguments)
            return ActivityToolResult.model_validate(suggest_activities(**validated.model_dump())).model_dump()
        raise EngineError("unknown_tool", "The AI requested an unsupported operation. Please try again.")
    except (ValueError, TypeError, ValidationError):
        raise EngineError("invalid_tool_arguments", "The AI supplied invalid tool arguments. Please try again.") from None


def check_response(response):
    if getattr(response, "status", None) != "completed":
        raise EngineError("incomplete_response", "The AI could not complete the response. Try a shorter trip.")
    if not re.fullmatch(r"resp_[A-Za-z0-9_-]{1,250}", response.id or ""):
        raise EngineError("invalid_response", "The AI returned an invalid conversation ID.")


def process_travel_message(message, previous_response_id=None, expected_budget=None, client=None, duration_days=None):
    expected = BudgetValues.model_validate(expected_budget or {}).model_dump(exclude_none=True)
    labelled = extract_budget_values(message)
    if any(key in expected and expected[key] != value for key, value in labelled.items()):
        raise EngineError("budget_conflict", "Please confirm matching message and budget form costs.", 422)
    expected.update(labelled)
    # At most two calls, each with a 24-second SDK timeout, under the proxy timeout.
    client = client or OpenAI(max_retries=0, timeout=24.0)
    instructions = SYSTEM_PROMPT + "\nAuthoritative whole-trip user costs (EUR): " + json.dumps(expected)
    if duration_days:
        instructions += f"\nRequested duration: {duration_days} days."
    request = dict(model="gpt-4.1-mini", instructions=instructions, input=message,
        text_format=TravelResponse, tools=[BUDGET_TOOL, ACTIVITIES_TOOL],
        tool_choice="auto", parallel_tool_calls=False, max_output_tokens=12000)
    if previous_response_id:
        request["previous_response_id"] = previous_response_id
    response = parse_response(client, **request)
    check_response(response)
    calls = [item for item in response.output if item.type == "function_call"]
    tool_names, budget_result = [], None
    if calls:
        if len(calls) > 4 or len({call.call_id for call in calls}) != len(calls):
            raise EngineError("invalid_tool_calls", "The AI requested too many or duplicate operations.")
        # Validate/execute only an explicit allowlist. No eval, network, files or shell tools.
        outputs = []
        for call in calls:
            result = execute_tool(call, expected)
            if call.name == "calculate_trip_budget":
                budget_result = result
            tool_names.append(call.name)
            outputs.append(dict(type="function_call_output", call_id=call.call_id, output=json.dumps(result)))
        response = parse_response(client, model="gpt-4.1-mini", instructions=instructions,
            previous_response_id=response.id, input=outputs, text_format=TravelResponse,
            tools=[BUDGET_TOOL, ACTIVITIES_TOOL], tool_choice="none", max_output_tokens=12000)
        check_response(response)
        if any(item.type == "function_call" for item in response.output):
            raise EngineError("tool_loop", "The AI could not finish after using its tools.")
    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise EngineError("invalid_response", "The AI did not return a usable travel plan. Please rephrase your request.")
    try:
        parsed = TravelResponse.model_validate(parsed)
    except ValidationError:
        raise EngineError("invalid_response", "The AI returned an inconsistent itinerary. Please try again.") from None
    trip = parsed.trip
    details = None
    if trip:
        if duration_days and trip.duration_days != duration_days:
            raise EngineError("duration_mismatch", "The generated itinerary did not match your requested duration. Please try again.")
        costs = trip.budget.model_dump(exclude={"currency"})
        if not verify_budget_arguments(costs, expected):
            raise EngineError("budget_mismatch", "The itinerary changed your supplied costs. Please try again.")
        if budget_result and (not verify_budget_arguments(costs, budget_result["costs"]) or
                costs["flights"] != budget_result["costs"].get("flights")):
            raise EngineError("budget_mismatch", "The itinerary did not match the budget tool result. Please try again.")
        # Even when no function call was selected, all displayed arithmetic is Python.
        details = calculate_trip_budget(**costs)
        details["sources"] = {key: "user_supplied" if key in expected else "ai_estimate"
            for key in details["costs"]}
        if "calculate_trip_budget" not in tool_names:
            tool_names.append("calculate_trip_budget")
        reply = format_trip_reply(trip, details)
    else:
        reply = parsed.question
        if budget_result:
            reply += f"\n\nCalculated budget: EUR {budget_result['total']:.2f} (known costs only)."
            details = budget_result
            details["sources"] = {key: "user_supplied" if key in expected else "ai_estimate"
                for key in details["costs"]}
    # Retain the teammate's answer alias for notebook callers; HTTP also returns reply.
    tool = tool_names[-1] if tool_names else "none"
    compatible = ToolResponse(answer=reply, tool_used=tool)
    return dict(reply=compatible.answer, answer=compatible.answer, response_id=response.id,
        status=parsed.status, trip=trip.model_dump() if trip else None,
        tool_used=compatible.tool_used, tools_used=list(dict.fromkeys(tool_names)),
        budget_details=details)


def process_budget_request(message, expected_budget=None):
    return process_travel_message(message, expected_budget=expected_budget)


def parse_response(client, **request):
    try:
        return client.responses.parse(**request)
    except ValidationError:
        raise EngineError("invalid_response", "The AI returned an inconsistent itinerary. Please try again.") from None


def format_trip_reply(trip, details):
    """Keep complete readable itineraries for clients that only understand reply."""
    lines = [f"# {trip.title}", f"{trip.destination} · {trip.duration_days} days",
        trip.summary, "Interests: " + ", ".join(trip.interests)]
    for day in trip.days:
        lines.extend([f"## Day {day.day_number}", f"- **Morning:** {day.morning}",
            f"- **Afternoon:** {day.afternoon}", f"- **Evening:** {day.evening}",
            "- **Places:** " + ", ".join(day.places), f"- **Food:** {day.food_suggestion}"])
    lines.append("## Budget (EUR, whole trip)")
    for key, value in details["costs"].items():
        source = "User supplied, amount checked" if details["sources"][key] == "user_supplied" else "AI estimate"
        lines.append(f"- **{key.title()}:** EUR {value:.2f} ({source})")
    lines.append(f"**Total of known costs: EUR {details['total']:.2f}**")
    if not details["flights_included"]:
        lines.append("Flights unknown and excluded. Estimates are not live booking prices.")
    lines.append("## Practical tips")
    lines.extend("- " + tip for tip in trip.practical_tips)
    return "\n\n".join(lines)
