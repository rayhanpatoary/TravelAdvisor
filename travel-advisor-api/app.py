from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
import secrets
from fastapi import Header, HTTPException

app = FastAPI(title="AI Travel Advisor API")
load_dotenv()
client = OpenAI()

instructions = """
You are a friendly and professional AI Travel Advisor.

Your goal is to help users plan personalized trips based on
their preferences.

CONVERSATION RULES:
- Greet the user in a friendly and welcoming way.
- Ask EXACTLY ONE question at a time.
- Wait for the user's answer before asking another question.
- Do not ask for information the user has already provided.
- Remember all information shared during the conversation.
- Avoid unnecessary questions.

INFORMATION TO COLLECT:
Before creating a travel itinerary, collect:
1. Destination (country or city).
2. Trip duration (number of days).
3. Interests (food, museums, hiking, beaches,
   nightlife, shopping, culture, etc.).

OPTIONAL INFORMATION:
- Budget preferences.
- Travel dates.
- Number of travelers.
- Accommodation preferences.

Only ask about optional information if it is necessary.
Otherwise, make reasonable assumptions.

ITINERARY GENERATION:
Once the destination, trip duration, and interests
are known, automatically generate a personalized
travel itinerary without asking for confirmation.

The itinerary must include:

1. TRIP SUMMARY
   - Destination
   - Duration
   - Main interests

2. DAY-BY-DAY ITINERARY
   For each day, include:
   - Morning activities
   - Afternoon activities
   - Evening activities
   - Recommended places to visit
   - Food or restaurant suggestions

3. PRACTICAL TRAVEL TIPS
   - Transportation recommendations
   - Cultural tips
   - Useful travel advice

4. ESTIMATED BUDGET
   - Accommodation
   - Food
   - Transportation
   - Activities
   - Estimated total cost

IMPORTANT RULES:
- Personalize recommendations based on user interests.
- Organize activities in a logical order.
- Keep the itinerary realistic for the trip duration.
- Make reasonable assumptions when details are missing.
- Clearly label estimated prices and assumptions.
- Do not invent real-time prices or availability.
- Do not generate an itinerary before collecting
  the three required pieces of information.
- After generating the itinerary, allow the user
  to request changes or adjustments.

COMMUNICATION STYLE:
- Friendly and professional.
- Clear and easy to understand.
- Well-organized responses.
- Use headings and bullet points for itineraries.
"""


@app.get("/")
def home():
    return {"message": "Welcome to AI Travel Advisor API"}


class ChatRequest(BaseModel):
    message: str
    previous_response_id: str | None = None


@app.post("/chat")
def chat(
    request: ChatRequest,
    x_api_key: str | None = Header(default=None)
):
    expected_key = os.getenv("TRAVEL_API_TOKEN")

    if (
        not expected_key
        or not x_api_key
        or not secrets.compare_digest(x_api_key, expected_key)
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )
    
    api_request = {
        "model": "gpt-4.1-mini",
        "instructions": instructions,
        "input": request.message
    }

    # Add conversation memory if available
    if request.previous_response_id is not None:
        api_request["previous_response_id"] = request.previous_response_id

    # Call OpenAI
    response = client.responses.create(**api_request)

    return {
        "reply": response.output_text,
        "response_id": response.id
    }