# Wordjog Lead routing API

FastAPI-based REST API framework for reading data from PostgreSQL and creating records in a CRM system.

## Twenty CRM Routing Example

The following diagram illustrates routing in action within Twenty CRM:

![Twenty CRM Routing Example](Architecture/Routing.png)

*Example of routing workflow in Twenty CRM showing how leads are processed and routed to sales agents*

## Project Structure

```
src/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   │
│   ├── api/                    # API routes
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py       # Main API router
│   │       ├── dependencies.py # API-specific dependencies
│   │       └── endpoints/       # Individual endpoint modules
│   │           ├── __init__.py
│   │           └── leads.py    # Leads API endpoints
│   │
│   ├── core/                   # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py          # Application settings
│   │   └── dependencies.py    # Shared dependencies (e.g., get_db)
│   │
│   ├── database/               # Database connection management
│   │   ├── __init__.py
│   │   ├── connection.py      # Database engine and connection pool
│   │   ├── session.py         # Session management
│   │   ├── models/            # SQLAlchemy database models
│   │   │   ├── __init__.py
│   │   │   ├── base.py        # Base model class
│   │   │   └── database.py    # Database models (Lead, etc.)
│   │   └── sqls/              # SQL scripts
│   │       ├── 01_create_leads_table.sql
│   │       ├── 02_insert_sample_leads.sql
│   │       ├── 03_drop_leads_table.sql
│   │       └── README.md
│   │
│   ├── schemas/                # Pydantic schemas for validation
│   │   ├── __init__.py
│   │   ├── base.py            # Base schema classes
│   │   ├── leads.py           # Lead API request/response schemas
│   │   └── twenty_crm.py      # Twenty CRM API schemas
│   │
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── lead_service.py    # Lead service with CRM sync logic
│   │   └── llm_service.py     # LLM service for OpenAI-compatible APIs
│   │
│   ├── external/               # External API clients
│   │   └── crm/
│   │       ├── __init__.py
│   │       ├── client.py      # CRM REST API client
│   │       └── twenty_crm.py # Twenty CRM utilities and conversions
│   │
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── logging.py         # Logging configuration
│       ├── exceptions.py       # Custom exception classes
│
├── requirements.txt            # Python dependencies
├── config.yaml                 # Application configuration (not in git)
└── config.yaml.example         # Configuration template
```

## Architecture Overview

### Layer Separation

1. **API Layer** (`app/api/`): Handles HTTP requests/responses, routing, and validation
2. **Service Layer** (`app/services/`): Contains business logic and orchestrates operations
3. **External Layer** (`app/external/`): Manages interactions with external APIs (CRM)
4. **Models** (`app/database/models/`): SQLAlchemy ORM models for database tables
5. **Schemas** (`app/schemas/`): Pydantic models for request/response validation

### Data Flow

```
Request → API Endpoint → Service → Database (SQLAlchemy queries)
                              ↓
                         CRM Client → External CRM API (Twenty CRM)
```

## Setup

### Using pyproject.toml
Please install uv first: https://docs.astral.sh/uv/installation/
1. **Install the project in editable mode:**

Or using `uv` (faster):
   ```bash
   uv venv
   uv sync
   ```
   Or
   Using `pip` (slower):
   ```bash
   pip install -e .
   ```

2. **Configure application settings:**
   - Update `config.yaml`
   - Update with your database, CRM API, and LLM API credentials

3. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   Or using the module directly:
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Usage Examples

### Creating a Service

```python
# app/services/lead_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models.database import Lead
from app.external.crm.client import CRMClient
from app.external.crm.twenty_crm import lead_to_twenty_crm

class LeadService:
    """Service for managing leads and syncing to Twenty CRM"""
    
    def __init__(self, db: Session):
        self.db = db
        self.crm_client = CRMClient()
    
    def get_all_leads(self, skip: int = 0, limit: int = 100) -> List[Lead]:
        """Get all leads from the database"""
        return self.db.query(Lead).offset(skip).limit(limit).all()
    
    async def sync_lead_to_crm(self, lead: Lead) -> dict:
        """Sync a single lead to Twenty CRM"""
        crm_data = lead_to_twenty_crm(lead)
        response = await self.crm_client.create_record(
            endpoint="rest/people",
            data=crm_data,
            params={"upsert": True}
        )
        return response
```

### Creating an Endpoint

```python
# app/api/v1/endpoints/leads.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.services.lead_service import LeadService
from app.schemas.leads import LeadListResponse

router = APIRouter()

@router.get("/leads", response_model=LeadListResponse)
async def get_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    leads = service.get_all_leads(skip=skip, limit=limit)
    return {
        "total": len(leads),
        "skip": skip,
        "limit": limit,
        "leads": leads
    }
```

### Using the LLM Service

```python
# app/services/llm_service.py usage examples
from app.services.llm_service import LLMService

# Initialize the LLM service
llm_service = LLMService()

# Example 1: Simple prompt (easiest way)
response = await llm_service.simple_prompt(
    prompt="What is the capital of France?",
    system_prompt="You are a helpful assistant."
)
print(response)  # "The capital of France is Paris."

# Example 2: Advanced chat completion with custom parameters
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain quantum computing in simple terms."}
]
response = await llm_service.chat_completion(
    messages=messages,
    model="gemma3:12b",  # Override default model
    temperature=0.8,     # More creative responses
    max_tokens=500       # Limit response length
)
print(response["choices"][0]["message"]["content"])

# Example 3: Streaming responses
async for chunk in llm_service.chat_completion_stream(
    messages=[
        {"role": "user", "content": "Write a short story about a robot."}
    ],
    model="gemma3:12b"
):
    # Process streaming chunks
    print(chunk, end="", flush=True)

# Example 4: Using in a service class
class ContentService:
    def __init__(self):
        self.llm_service = LLMService()
    
    async def generate_summary(self, text: str) -> str:
        prompt = f"Summarize the following text in 2-3 sentences:\n\n{text}"
        return await self.llm_service.simple_prompt(
            prompt=prompt,
            system_prompt="You are a text summarization expert."
        )
```

**LLM Configuration** (`config.yaml`):
```yaml
llm:
  base_url: "https://192.168.1.22:11434/v1"  # Your OpenAI-compatible API URL
  api_key: null  # API key if required (set to null if not needed)
  model: "gemma3:12b"  # Default model to use
  timeout: 60  # Request timeout in seconds
  max_tokens: 1000  # Maximum tokens in response
  temperature: 0.7  # Temperature (0.0-2.0)
  stream: false  # Enable streaming responses
```

**Compatible Services:**
- OpenAI API
- Ollama (local models)
- Anthropic Claude (with compatible wrapper)
- Any OpenAI-compatible API endpoint

## Key Features

- ✅ Clean separation of concerns
- ✅ YAML-based configuration
- ✅ Database connection pooling with SQLAlchemy
- ✅ Async CRM API client (Twenty CRM)
- ✅ LLM service for OpenAI-compatible APIs (OpenAI, Ollama, etc.)
- ✅ Type-safe with Pydantic schemas for validation
- ✅ Schema-based validation for CRM API requests
- ✅ Structured logging with rich formatting
- ✅ Custom exception handling
- ✅ API versioning support
- ✅ CORS configuration
- ✅ Response models for all API endpoints

## API Endpoints

### Leads

- `GET /api/v1/leads` - Get all leads (with pagination)
- `GET /api/v1/leads/{lead_id}` - Get a specific lead by lead_id
- `POST /api/v1/leads/sync` - Sync all leads to Twenty CRM
- `POST /api/v1/leads/{lead_id}/sync` - Sync a single lead to Twenty CRM

### Health Check

- `GET /health` - Health check endpoint with database pool status

## Next Steps

1. Add more database models in `app/database/models/database.py` as needed
2. Create additional service classes in `app/services/` for new entities
3. Create new endpoint modules in `app/api/v1/endpoints/`
4. Add request schemas in `app/schemas/` for POST/PUT endpoints
5. Add authentication/authorization as needed
6. Set up database migrations with Alembic
7. Add unit tests for services and endpoints