# TrustVault - Secure Document Access and Audit Platform

TrustVault is a FastAPI-based application for securely uploading, sharing, and accessing documents with per-document permissions and an auditable record of important actions.

## Features

- **Authentication:** User registration and login using password hashing and JWT bearer tokens.
- **Document upload:** Supports PDF, plain text, PNG, and JPEG files, with a 5 MB upload limit.
- **Document listing:** Lists documents owned by the current user and documents shared with read access.
- **Access control:** Document owners can grant read or edit permissions to registered users.
- **Metadata editing:** Owners and users with edit permission can update a document's category.
- **Permission revocation:** Owners can revoke a user's document access.
- **Audit logging:** Records important document actions, including successful operations and selected denied access attempts.
- **Audit integrity:** Audit events use a SHA-256 hash chain that can be checked for modifications.
- **Automated tests:** Includes tests for authentication, document permissions, and audit-chain integrity.

## Technology Stack

- Python
- FastAPI
- SQLAlchemy
- SQLite
- JWT authentication
- Argon2 password hashing through `pwdlib`
- Pytest and FastAPI TestClient

## Project Structure

```text
trustvault/
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ auth/
â”‚   â”‚   â”œâ”€â”€ audit/
â”‚   â”‚   â”œâ”€â”€ documents/
â”‚   â”‚   â”œâ”€â”€ database.py
â”‚   â”‚   â”œâ”€â”€ main.py
â”‚   â”‚   â””â”€â”€ models.py
â”‚   â”œâ”€â”€ tests/
â”‚   â”œâ”€â”€ init_db.py
â”‚   â””â”€â”€ .env                 # Create locally; do not commit
â”œâ”€â”€ .gitignore
â””â”€â”€ README.md
```

## Prerequisites

- Python 3.11 or compatible
- PowerShell on Windows, or an equivalent terminal
- Git

## Local Setup

Open PowerShell and navigate to the backend directory:

```powershell
cd C:\Users\harin\trustvault\backend
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the required packages:

```powershell
python -m pip install fastapi "uvicorn[standard]" sqlalchemy python-dotenv "PyJWT" "pwdlib[argon2]" python-multipart email-validator pytest httpx
```

Create a local `.env` file containing a strong, randomly generated secret:

```text
TRUSTVAULT_SECRET_KEY=replace-with-a-long-random-secret
```

Generate a suitable secret locally with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Replace the example value with the generated secret. Never commit `.env` or disclose the secret.

## Initialize the Database

From the `backend` directory, with the virtual environment activated:

```powershell
python init_db.py
```

This creates the database tables defined by the SQLAlchemy models. The current application uses SQLite for local development.

## Run the Application

From the same directory:

```powershell
uvicorn app.main:app --reload
```

The local API is available at:

- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs

## API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register` | Register a user |
| POST | `/auth/login` | Authenticate and obtain a token |
| GET | `/auth/me` | Retrieve the authenticated user's information |
| POST | `/documents/upload` | Upload a document |
| GET | `/documents` | List owned and accessible documents |
| PATCH | `/documents/{document_id}` | Update document category |
| GET | `/documents/{document_id}/download` | Download a document if authorized |
| POST | `/documents/{document_id}/share` | Grant or update document permissions |
| DELETE | `/documents/{document_id}/share/{user_id}` | Revoke a user's document access |

Use the interactive API documentation at `/docs` to inspect request schemas and responses.

### Typical Workflow

1. Register two separate users.
2. Log in as the document owner and copy the returned access token.
3. In Swagger UI, authorize requests with the owner's bearer token.
4. Upload a supported document.
5. Grant another registered user read or edit access.
6. Log in as the recipient and verify their permitted operations.
7. Revoke the recipient's access and verify that subsequent unauthorized requests are denied.

## Permission Model

- **Owner:** Can upload, download, update document metadata, share documents, and revoke document access.
- **Read-only recipient:** Can list and download documents shared with read permission.
- **Edit recipient:** Can read the document and update its category.
- **Unauthorized user:** Cannot download or edit another user's document without the required permission.

Permissions are checked on the server. Hiding an action in a user interface would not replace these checks.

## Audit Logging

Important document operations are recorded in the audit log. The audit service links events using SHA-256 hashes and provides a function to verify the chain.

A hash chain can help detect modifications, but it is not a complete guarantee against a privileged attacker who can rewrite the entire database and recompute hashes. Production deployments should consider independently protected audit storage.

## Run Tests

From the `backend` directory:

```powershell
python -m pytest -q
```

The current development test suite has passed 14 tests. Run the command again after making changes to confirm the current result.

## Security Considerations

- Keep `TRUSTVAULT_SECRET_KEY` private and use a unique, strong value.
- Do not commit `.env`, local databases, virtual environments, or uploaded documents.
- The current upload limit is 5 MB.
- Supported upload formats are PDF, plain text, PNG, and JPEG.
- SQLite and local filesystem storage are intended for the current development implementation.
- A production deployment should add operational monitoring, protected backups, hardened secret management, and independently protected audit storage.
- Do not claim the audit chain is immune to privileged database tampering.

## Current Scope and Limitations

The project includes a FastAPI backend and a React/Vite graphical frontend. The frontend supports login, document listing, upload, download, search, and navigation between owned and shared documents. Document editing currently updates metadata (the category), not the uploaded file's contents.

Production hosting, deployment hardening, and any features not listed above must be verified separately before being represented as complete.

## License

Add the license required by the project owner or challenge instructions before distributing this project.
