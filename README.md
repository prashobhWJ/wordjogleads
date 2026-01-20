# Carnance API

FastAPI-based REST API framework for reading data from PostgreSQL and creating records in a CRM system.

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
│   │           └── example.py  # Example endpoint (replace with your endpoints)
│   │
│   ├── core/                   # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py          # Application settings
│   │   └── dependencies.py    # Shared dependencies (e.g., get_db)
│   │
│   ├── database/               # Database connection management
│   │   ├── __init__.py
│   │   ├── connection.py      # Database engine creation
│   │   └── session.py         # Session management
│   │
│   ├── models/                 # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── base.py            # Base model class
│   │   └── database.py        # Your database models
│   │
│   ├── schemas/                # Pydantic schemas for validation
│   │   ├── __init__.py
│   │   └── base.py            # Base schema classes
│   │
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   └── base_service.py    # Base service class
│   │
│   ├── repositories/           # Data access layer
│   │   ├── __init__.py
│   │   └── base_repository.py # Base repository class
│   │
│   ├── external/               # External API clients
│   │   └── crm/
│   │       ├── __init__.py
│   │       ├── client.py      # CRM REST API client
│   │       └── models.py      # CRM API models
│   │
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── logging.py         # Logging configuration
│       ├── helpers.py         # General helper functions
│       └── exceptions.py      # Custom exception classes
│
├── requirements.txt            # Python dependencies
├── config.yaml                 # Application configuration (not in git)
└── config.yaml.example         # Configuration template
```

## Architecture Overview

### Layer Separation

1. **API Layer** (`app/api/`): Handles HTTP requests/responses, routing, and validation
2. **Service Layer** (`app/services/`): Contains business logic and orchestrates operations
3. **Repository Layer** (`app/repositories/`): Handles direct database access and queries
4. **External Layer** (`app/external/`): Manages interactions with external APIs (CRM)
5. **Models** (`app/models/`): SQLAlchemy ORM models for database tables
6. **Schemas** (`app/schemas/`): Pydantic models for request/response validation

### Data Flow

```
Request → API Endpoint → Service → Repository → Database
                              ↓
                         CRM Client → External CRM API
```

## Setup

### Option 1: Using pyproject.toml (Recommended)

1. **Install the project in editable mode:**
   ```bash
   pip install -e .
   ```
   
   Or using `uv` (faster):
   ```bash
   uv pip install -e .
   ```

2. **Configure application settings:**
   - Copy `config.yaml.example` to `config.yaml`
   - Update with your database and CRM API credentials

3. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   Or using the module directly:
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Option 2: Using requirements.txt

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure application settings:**
   - Copy `config.yaml.example` to `config.yaml`
   - Update with your database and CRM API credentials

3. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Usage Examples

### Creating a Service

```python
# app/services/contact_service.py
from app.services.base_service import BaseService
from app.models.database import Contact
from app.external.crm.client import CRMClient
from app.external.crm.models import CRMContactCreate

class ContactService(BaseService):
    def __init__(self, db):
        super().__init__(db, Contact)
        self.crm_client = CRMClient()
    
    async def create_contact_with_crm(self, contact_data):
        # Create in database
        db_contact = self.create(**contact_data.dict())
        
        # Create in CRM
        crm_data = CRMContactCreate(
            first_name=contact_data.first_name,
            last_name=contact_data.last_name,
            email=contact_data.email
        )
        crm_response = await self.crm_client.create_record(
            "/contacts",
            crm_data.dict()
        )
        
        return db_contact, crm_response
```

### Creating an Endpoint

```python
# app/api/v1/endpoints/contacts.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.services.contact_service import ContactService

router = APIRouter()

@router.post("/contacts")
async def create_contact(
    contact_data: ContactCreate,
    db: Session = Depends(get_db)
):
    service = ContactService(db)
    return await service.create_contact_with_crm(contact_data)
```

## Key Features

- ✅ Clean separation of concerns
- ✅ YAML-based configuration
- ✅ Database connection pooling
- ✅ Async CRM API client
- ✅ Type-safe with Pydantic schemas
- ✅ Base classes for services and repositories
- ✅ Structured logging
- ✅ Custom exception handling
- ✅ API versioning support
- ✅ CORS configuration

## Next Steps

1. Replace example models in `app/models/database.py` with your actual database models
2. Create your service classes in `app/services/`
3. Create your endpoint modules in `app/api/v1/endpoints/`
4. Customize the CRM client in `app/external/crm/client.py` based on your CRM API
5. Add authentication/authorization as needed
6. Set up database migrations with Alembic
