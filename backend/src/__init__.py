"""
Co-Code GGW Health Platform Backend

Structured following the monolithic REST API pattern:
- config/     Application config, environment variables, database setup
- middleware/ Authentication, authorization, rate limiting
- models/     Database schemas / ORM models and Pydantic schemas
- controllers/ Request/response handlers (business logic delegation)
- routes/     Endpoint definitions and route grouping
- utils/      Reusable helpers (formatters, token helpers)
- services/   Business logic and data processing
"""
