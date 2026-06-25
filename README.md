# QueueStorm Warmup API

This is a mock hackathon submission for the bKash SUST CSE Carnival 2026. 
It is a fast, AI-powered customer support ticket classification API using FastAPI and Meta's Llama-3 (via Groq).

## Tech Stack
- **Framework:** FastAPI (Python)
- **LLM:** Meta Llama-3-8b-8192 (via Groq API)
- **Validation:** Pydantic

## How to Run Locally
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Set your Groq API key: 
   - Linux/Mac: `export GROQ_API_KEY="your_api_key"`
   - Windows: `set GROQ_API_KEY="your_api_key"`
4. Run the server: `uvicorn main:app --reload`
5. Visit `http://127.0.0.1:8000/docs` to test the API.