# Database Schema - Gemini Chat API

This document outlines the proposed database structure for the Gemini Chat application to support persistent storage.

## Tables

### 1. Users
Stores user account information for authentication.

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for each user. |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL | The user's login name. |
| `email` | VARCHAR(100) | UNIQUE, NOT NULL | User's email address. |
| `password_hash` | VARCHAR(255) | NOT NULL | Securely hashed password. |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Timestamp when the account was created. |

### 2. ChatSessions
Stores metadata for individual chat conversations.

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `session_id` | VARCHAR(255) | PRIMARY KEY | Unique UUID or ID for the session. |
| `user_id` | INTEGER | FOREIGN KEY (Users.user_id) | Owner of this chat session. |
| `title` | VARCHAR(255) | DEFAULT 'New Chat' | User-defined or auto-generated chat title. |
| `model_name` | VARCHAR(50) | NOT NULL | The version of Gemini model used (e.g., 'gemini-2.5-flash'). |
| `is_active` | BOOLEAN | DEFAULT TRUE | Status of the session. |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | When the session started. |

### 3. Messages
Stores the actual dialogue history within each session.

| Field Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `message_id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for each message. |
| `session_id` | VARCHAR(255) | FOREIGN KEY (ChatSessions.session_id) | Reference to the chat session. |
| `sender_type` | ENUM('user', 'ai') | NOT NULL | Identifies if message is from Human or AI. |
| `message_content`| TEXT | NOT NULL | The actual text of the message. |
| `is_error` | BOOLEAN | DEFAULT FALSE | Flag indicating if the AI response failed. |
| `timestamp` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Exact time the message was recorded. |

---

## Entity Relationship Diagram (ERD) Concept
- **Users** can have **Multiple ChatSessions** (1:N).
- **ChatSessions** contains **Multiple Messages** (1:N).
