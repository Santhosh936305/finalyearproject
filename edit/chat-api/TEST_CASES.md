# Test Cases - Gemini Chat API

This document provides a comprehensive test plan for the chat application, covering API functionality, UI behavior, and edge cases.

## Test Matrix

| Case ID | Category | Feature | Test Scenario | Input Data | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **API-01** | Backend | Chat API | Send valid prompt | `{"message": "What is Python?"}` | Status 200, returns AI response text. | Pending |
| **API-02** | Backend | Validation | Send empty message | `{"message": ""}` | Status 400, returns "Message is required". | Pending |
| **API-03** | Backend | Session | New session creation | POST `/api/chat/new` | Status 200, returns a unique `session_id`. | Pending |
| **API-04** | Backend | Session | Clear session history | POST `/api/chat/clear` | Status 200, deletes session data on server. | Pending |
| **UI-01** | Frontend | Chat Window | Send user message | Type "Hello" + Enter | Message appears in bubble on right side. | Pending |
| **UI-02** | Frontend | Loading | AI Processing | Send any message | "Loading..." dots animation appears. | Pending |
| **UI-03** | Frontend | Display | AI Response | Wait for API reply | AI message appears in bubble on left side. | Pending |
| **UI-04** | Frontend | Layout | Auto-scroll | Long conversation | Chat automatically scrolls to the bottom. | Pending |
| **UI-05** | Frontend | Interaction| Clear Chat Button | Click "Clear" + Confirm | Chat history is wiped from the screen. | Pending |
| **UI-06** | Frontend | Input | Empty Send | Click Send with no input | No message bubble added, no API call. | Pending |
| **ERR-01** | Reliability| API Error | Disconnect Network | Send any message | UI displays error message "Failed to connect". | Pending |
| **ERR-02** | Reliability| Gemini Error | Invalid API Key | Send any message | Server returns 500, UI shows "Error: [Details]".| Pending |

## Execution Summary
- **Total Cases:** 12
- **Manual Tests:** 6
- **Automated Tests:** 6
- **Tools Used:** Pytest (API), Manual Browser testing (UI)
