# TrustVault Threat Model



## 1. Purpose and Scope



This document identifies important assets, potential attackers, security risks, existing controls, and residual risks in TrustVault.



## 2. Assets to Protect



\- User credentials and password hashes.

\- JWT signing secrets and authentication tokens.

\- Uploaded documents and stored files.

\- Document ownership and sharing permissions.

\- Audit events and their integrity.

\- User and document metadata.



## 3. Threat Actors



\- Unauthenticated attackers targeting protected endpoints.

\- Authenticated users attempting to access other users' documents.

\- Recipients attempting actions beyond their granted permissions.

\- Attackers uploading unexpected or oversized files.

\- Attackers who compromise application secrets, the database, or the server.



## 4. Threats and Mitigations



### T1: Unauthorized API Access



\*\*Threat:\*\* An unauthenticated user or an attacker with an invalid or expired token attempts to access protected endpoints.



\*\*Existing controls:\*\* Protected routes use JWT authentication. Invalid or expired tokens are rejected, and inactive accounts are not accepted.



\*\*Residual risk:\*\* Token theft remains possible if a token or client device is compromised. Token revocation and refresh-token workflows are not currently implemented.



### T2: Cross-User Document Access



\*\*Threat:\*\* A user attempts to list, download, modify, or share documents belonging to another user.



\*\*Existing controls:\*\* Document routes enforce ownership or explicit permissions. Automated tests cover unauthorized downloads, read-only access, sharing restrictions, and permission revocation.



\*\*Residual risk:\*\* Every new document endpoint must apply the appropriate authorization checks and have dedicated tests.



### T3: Excessive Sharing Permissions



\*\*Threat:\*\* A recipient receives edit access without read access, or a non-owner attempts to grant or revoke permissions.



\*\*Existing controls:\*\* Only document owners can manage sharing. Edit permission requires read permission. Revocation removes the permission, and subsequent requests check current database permissions.



\*\*Residual risk:\*\* Concurrent permission changes and future permission types require additional testing.



### T4: Malicious or Oversized Uploads



\*\*Threat:\*\* An attacker uploads an oversized file, uses a misleading filename, or submits content that does not match the claimed file type.



\*\*Existing controls:\*\* Uploads have a 5 MB limit, an allowlist of supported content types, sanitized filenames, unique stored filenames, and basic signature checks for PDF, PNG, and JPEG files.



\*\*Residual risk:\*\* Signature checks do not replace malware scanning or comprehensive file validation. Production should consider resource quotas, malware scanning, and controlled file storage.



### T5: Audit Log Modification



\*\*Threat:\*\* An attacker modifies audit events or event ordering to hide unauthorized activity.



\*\*Existing controls:\*\* Audit events are linked using SHA-256 hashes. Chain verification detects changes to event contents or broken links. Denied document operations are audited.



\*\*Residual risk:\*\* A hash chain stored in the same database is not fully tamper-proof. An attacker with sufficient database access may rewrite events and recompute hashes. Production should export audit records to a separately controlled, append-only or tamper-resistant logging system.



### T6: Credential or Signing-Secret Compromise



\*\*Threat:\*\* An attacker obtains password data or the JWT signing secret.



\*\*Existing controls:\*\* Passwords are stored as hashes. The JWT secret is loaded from environment configuration rather than hard-coded in application source. Local environment files and database artifacts are ignored by Git.



\*\*Residual risk:\*\* A weak or exposed secret can compromise token security. Production should use secret management, rotate compromised secrets, enforce TLS, and protect deployment configuration.



### T7: Database or Server Compromise



\*\*Threat:\*\* An attacker gains operating-system, database, or application-server access and reads or modifies stored documents and records.



\*\*Existing controls:\*\* Application-level authentication and authorization restrict normal API access.



\*\*Residual risk:\*\* Application permissions do not protect against every privileged server or database attacker. Production needs least-privilege service accounts, protected backups, monitoring, patching, and restricted database and filesystem access.



## 5. Security Verification



The automated test suite covers authentication, document permission checks, sharing and revocation, denied-operation auditing, and audit-chain integrity.



Run the suite from the backend directory:



```powershell

python -m pytest -q

```



Extend security tests whenever a new route, role, permission, or document operation is introduced.



## 6. Out of Scope and Future Work



\- Malware scanning and advanced file-format validation.

\- Rate limiting and automated abuse detection.

\- Production secret management and key rotation.

\- Centralized tamper-resistant audit-log storage.

\- Deployment hardening, TLS, monitoring, and backup recovery.

\- Multi-factor authentication and token revocation.



## 7. Security Reporting



Do not publish credentials, signing secrets, private documents, or exploitable vulnerability details in public issue reports. Report security concerns privately to the project maintainer.
