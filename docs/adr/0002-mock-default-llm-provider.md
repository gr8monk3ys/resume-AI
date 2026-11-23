# LLM providers are pluggable and default to a mock

All AI features go through `backend/app/services/llm_service.py`, which adapts OpenAI, Anthropic, Google, Ollama and a Mock provider behind one interface. `LLM_PROVIDER` defaults to `mock`, so the app, the tests and CI run with no API keys and no network; a real provider is opt-in through `.env`. ATS scoring stays algorithmic and does not call an LLM.
