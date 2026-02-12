# Tajdo Online Store Backend

This is a full-featured backend for the Tajdo Online Store, built with **Python** and **FastAPI**.

## Features

- **FastAPI**: High-performance web framework for building APIs.
- **SQLAlchemy**: Powerful SQL toolkit and Object-Relational Mapper (ORM).
- **PostgreSQL**: Robust and scalable relational database (schema provided).
- **Pydantic**: Data validation and settings management using Python type annotations.
- **Modular Architecture**: Clean separation of concerns with models, schemas, and API routes.
- **Authentication**: JWT-based authentication for secure API access.
- **Alembic**: Database migration tool for managing schema changes.

## Project Structure

```text
tajdo_backend/
├── alembic/            # Alembic migration scripts
├── app/
│   ├── api/            # API route handlers
│   ├── core/           # Core configuration and security
│   ├── db/             # Database session and connection
│   ├── models/         # SQLAlchemy database models
│   ├── schemas/        # Pydantic data validation schemas
│   ├── services/       # Business logic layer
│   └── main.py         # Application entry point
├── requirements.txt    # Project dependencies
├── .env.example        # Example environment variables
└── README.md           # Project documentation
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL instance (running and accessible)

### Installation

1.  **Clone the repository** (or copy the files).
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up environment variables**:
    Create a `.env` file in the root directory (or rename `.env.example` to `.env`) and add your database URL:
    ```env
    DATABASE_URL=postgresql://user:password@localhost/dbname
    SECRET_KEY=your-super-secret-key
    ```
    Replace `user`, `password`, `localhost`, and `dbname` with your PostgreSQL credentials. Also, replace `your-super-secret-key` with a strong, random secret key.

4.  **Run database migrations**:
    ```bash
    alembic upgrade head
    ```
    This will create all necessary tables in your PostgreSQL database based on the SQLAlchemy models.

5.  **Run the application**:
    ```bash
    uvicorn app.main:app --reload
    ```

## API Documentation

Once the application is running, you can access the interactive API documentation at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Best Practices Followed

- **Type Hinting**: Extensive use of Python type hints for better code quality and IDE support.
- **Dependency Injection**: Used for database sessions and other components.
- **Asynchronous Support**: Leveraging FastAPI's async capabilities for high performance.
- **Schema Validation**: Strict data validation using Pydantic.
- **Clean Code**: Organized directory structure and clear naming conventions.
- **Authentication**: Secure JWT-based authentication.
- **Database Migrations**: Managed with Alembic for controlled schema evolution.
