import os
import httpx
from typing import List, Dict
from app.config import get_settings

# Groq OpenAI-compatible endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"  # Updated to the latest stable Llama 3.3

# RapidCover Knowledge Base - System Prompt
SYSTEM_PROMPT = """You are RapidBot, the official AI assistant for RapidCover. 
RapidCover provides instant parametric disruption insurance for gig delivery partners.

YOUR RULES:
1. ONLY answer questions about RapidCover's insurance, payouts, eligibility, and zones.
2. If a user asks anything else (trivia, jokes, other apps), politely refocus them on RapidCover help.
3. NEVER mention Groq, Grok, or being an AI model. You are RapidBot.
4. Be concise, sharp, and professional.

RAPIDCOVER FACTS:
- ELIGIBILITY (7-Day Rule): Partners need 7 active delivery days in the last 30 to buy a premium plan (Flex, Standard, or Pro). Delhi partners are currently exempt.
- TIERS & PAYOUTS: 
  * Flex: Rs. 250 max daily payout.
  * Standard: Rs. 400 max daily payout.
  * Pro: Rs. 500 max daily payout.
- TRIGGERS:
  * Rain: Rs. 50/hr (triggered after 30 mins).
  * Heat: Rs. 40/hr (triggered after 4 hours above 40°C).
  * AQI: Rs. 45/hr (triggered after 3 hours above 300).
- ZONES: Active in 10 Mumbai zones (MUM-001 to MUM-010).
- KYC: Aadhaar and PAN needed for higher limits and secure transfers.
- PAYOUTS: Hit your bank account instantly via UPI once a trigger is confirmed.
"""

async def get_rapidbot_response(messages: List[Dict[str, str]]) -> str:
    settings = get_settings()
    api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        return "RapidBot is currently resting (API key missing). Please check your config."

    # Filter messages: Some APIs (OpenAI standard) require the first message after 'system' to be 'user'.
    # We strip any leading 'assistant' messages from the history tracker.
    filtered_messages = []
    found_first_user = False
    for m in messages:
        if m.get("role") == "user":
            found_first_user = True
        if found_first_user:
            filtered_messages.append(m)

    # Prepare chat payload with system prompt reinforcement
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *filtered_messages[-6:]  # Keep last 3 exchanges (6 messages) for context
        ],
        "temperature": 0.2, # Keep it factual
        "max_tokens": 1024
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GROQ_API_URL, json=payload, headers=headers)
            if response.status_code != 200:
                print(f"Groq API Error Output: {response.text}")
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        print(f"HTTP Status Error: {e.response.status_code} - {e.response.text}")
        return "I'm experiencing a protocol mismatch with the RapidCover network. Retrying..."
    except Exception as e:
        print(f"General AI Service Error: {e}")
        return "I'm having trouble connecting to the RapidCover network right now. Please try again in 3... 2... 1..."
