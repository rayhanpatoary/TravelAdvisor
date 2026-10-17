"""FastAPI entry point. Importing this module never calls OpenAI."""
import os
import secrets
import re
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from openai import (OpenAIError, RateLimitError, AuthenticationError, APITimeoutError,
    APIConnectionError, BadRequestError, NotFoundError)
from pydantic import ValidationError
from schemas import ChatRequest
from travel_engine import process_travel_message, EngineError
from budget_context import decode_context, encode_context, extract_budget_values

root = Path(__file__).resolve().parent
load_dotenv(root / ".env")
load_dotenv(root.parent / ".env")
app = FastAPI(title="AI Travel Advisor API", version="2.0.0")


def failure(status, code, message):
    return JSONResponse(status_code=status, content={"error": message, "code": code},
        headers={"Cache-Control": "no-store"})


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, _exception):
    # Pydantic's default errors can echo user input; keep public errors minimal.
    return failure(422, "invalid_request", "Please check your message, conversation ID and non-negative EUR costs.")


@app.get("/")
def home():
    return {"message": "Welcome to AI Travel Advisor API"}


@app.post("/chat")
def chat(request: ChatRequest, x_api_key: str | None = Header(default=None)):
    token = os.getenv("TRAVEL_API_TOKEN")
    if not token:
        return failure(503, "missing_configuration", "The travel service is not configured.")
    if not x_api_key or not secrets.compare_digest(x_api_key.encode(), token.encode()):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not os.getenv("OPENAI_API_KEY"):
        return failure(503, "missing_configuration", "The AI service is not configured.")
    try:
        context = decode_context(request.budget_context, request.previous_response_id, token)
        values = context["values"]
        durations = re.findall(r"\b(\d+)\s*[- ]?\s*days?\b", request.message, re.I)
        duration = int(durations[0]) if durations else context["duration_days"]
        if duration is not None and not 1 <= duration <= 30:
            return failure(422, "invalid_duration", "Please plan a trip segment between 1 and 30 days.")
        supplied = request.expected_budget.model_dump(exclude_none=True) if request.expected_budget else {}
        extracted = extract_budget_values(request.message)
        if any(key in supplied and supplied[key] != value for key, value in extracted.items()):
            return failure(422, "budget_conflict", "Message costs conflict with the budget form. Please confirm matching amounts.")
        values.update(extracted)
        values.update(supplied)
        result = process_travel_message(request.message, request.previous_response_id, values, duration_days=duration)
        result["budget_context"] = encode_context(values, result["response_id"], token, duration)
        return JSONResponse(content=result, headers={"Cache-Control": "no-store"})
    except RateLimitError as error:
        body = getattr(error, "body", None)
        details = body.get("error", body) if isinstance(body, dict) else {}
        details = details if isinstance(details, dict) else {}
        categories = {getattr(error, "code", None), details.get("code"), details.get("type")}
        quota = "insufficient_quota" in categories or "exceeded your current quota" in str(error).lower()
        return failure(429, "quota_exhausted" if quota else "rate_limited",
            "The AI service has no available credits. The site owner needs to check billing." if quota
            else "The AI service is busy. Please wait before trying again.")
    except AuthenticationError:
        return failure(503, "ai_configuration", "The AI service credentials need attention from the site owner.")
    except APITimeoutError:
        return failure(504, "ai_timeout", "The AI request timed out. Please try a shorter trip.")
    except APIConnectionError:
        return failure(502, "ai_connection", "Could not connect to the AI service.")
    except (BadRequestError, NotFoundError):
        return failure(400, "invalid_conversation", "The AI could not use this request or conversation. Please start a new trip.")
    except EngineError as error:
        return failure(error.status, error.code, error.message)
    except ValidationError:
        return failure(422, "invalid_budget", "Please enter valid non-negative whole-trip EUR costs.")
    except ValueError:
        # Only our own deterministic input/context validation reaches this handler.
        return failure(422, "invalid_budget_context", "Check your EUR amounts and conflicting values. If the context expired, start a new trip.")
    except OpenAIError:
        return failure(502, "ai_error", "The AI service could not complete the request.")
    except Exception:
        # Do not leak SDK exceptions, tokens, prompts, or upstream response bodies.
        return failure(502, "unexpected_response", "The travel service could not complete the request.")
