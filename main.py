import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from groq import Groq

# --- ENUMS ---
class Channel(str, Enum):
    app = "app"
    sms = "sms"
    call_center = "call_center"
    merchant_portal = "merchant_portal"

class Locale(str, Enum):
    bn = "bn"
    en = "en"
    mixed = "mixed"

class CaseType(str, Enum):
    wrong_transfer = "wrong_transfer"
    payment_failed = "payment_failed"
    refund_request = "refund_request"
    phishing_or_social_engineering = "phishing_or_social_engineering"
    other = "other"

class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class Department(str, Enum):
    customer_support = "customer_support"
    dispute_resolution = "dispute_resolution"
    payments_ops = "payments_ops"
    fraud_risk = "fraud_risk"

# --- PYDANTIC MODELS ---
class TicketRequest(BaseModel):
    ticket_id: str
    channel: Optional[Channel] = None
    locale: Optional[Locale] = None
    message: str

class TicketResponse(BaseModel):
    ticket_id: str
    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str
    human_review_required: bool
    confidence: float = Field(..., ge=0.0, le=1.0)

# --- FASTAPI APP & GROQ CLIENT ---
app = FastAPI(title="QueueStorm Warmup API - Groq Version")

# Initialize Groq client. It will automatically look for the GROQ_API_KEY environment variable.
client = Groq() 

# --- LLM LOGIC ---
def analyze_ticket_with_llm(message: str):
    """Uses Groq (Llama-3) to classify the ticket message and output strict JSON."""
    
    prompt = f"""
    You are an expert customer support routing AI for a digital finance company (bKash).
    Analyze the following customer message: "{message}"

    Return a JSON object with EXACTLY these keys and correct values based on the rules:
    - "case_type": (must be exactly one of: "wrong_transfer", "payment_failed", "refund_request", "phishing_or_social_engineering", "other")
    - "severity": (must be exactly one of: "low", "medium", "high", "critical")
    - "department": (must be exactly one of: "customer_support", "dispute_resolution", "payments_ops", "fraud_risk")
    - "agent_summary": A 1-2 sentence neutral summary of the issue.
    - "confidence": A float between 0.0 and 1.0 representing your confidence.

    ROUTING RULES:
    1. "phishing_or_social_engineering": Suspicious calls, SMS, or someone asking for PIN, OTP, or password. (Severity: critical, Dept: fraud_risk)
    2. "wrong_transfer": Money sent to the wrong recipient. (Severity: high, Dept: dispute_resolution)
    3. "payment_failed": Transaction failed but balance may be deducted. (Severity: high, Dept: payments_ops)
    4. "refund_request": Customer is asking for a refund. (Severity: low, Dept: customer_support)
    5. "other": Anything else. (Severity: low, Dept: customer_support)

    SAFETY RULE (CRITICAL):
    The "agent_summary" MUST NEVER ask the customer to share PIN, OTP, password, or full card number. 
    """

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192", # Free and insanely fast
            messages=[
                {"role": "system", "content": "You are a backend server that outputs strictly valid JSON matching the requested schema."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0 # Deterministic responses
        )
        
        # Parse the JSON string returned by Groq into a Python dictionary
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"LLM Error: {e}")
        # Fallback if the LLM fails or API key is missing
        return {
            "case_type": "other",
            "severity": "low",
            "department": "customer_support",
            "agent_summary": "System fallback: Error processing message.",
            "confidence": 0.0
        }

# --- ENDPOINTS ---

@app.get("/")
def home():
    # Redirect root to docs page
    return RedirectResponse(url="/docs")

@app.get("/health")
def health_check():
    """Return a simple service health response"""
    return {"status": "healthy"}

@app.post("/sort-ticket", response_model=TicketResponse)
def sort_ticket(ticket: TicketRequest):
    """Accept one CRM ticket and return a structured classification using LLM"""
    
    # 1. Ask Groq to process the text
    llm_result = analyze_ticket_with_llm(ticket.message)
    
    # 2. Check rule: Flag human review if critical OR phishing
    needs_review = False
    if llm_result["severity"] == "critical" or llm_result["case_type"] == "phishing_or_social_engineering":
        needs_review = True
        
    # 3. Build response using Pydantic
    try:
        return TicketResponse(
            ticket_id=ticket.ticket_id,
            case_type=llm_result["case_type"],
            severity=llm_result["severity"],
            department=llm_result["department"],
            agent_summary=llm_result["agent_summary"],
            human_review_required=needs_review,
            confidence=float(llm_result["confidence"])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM produced invalid schema: {str(e)}")