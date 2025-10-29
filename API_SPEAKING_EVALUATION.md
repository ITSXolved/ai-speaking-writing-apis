# Speaking Evaluation API Reference

## Base URL
```
http://localhost:8000
```

## Endpoints

### 1. Evaluate Speaking Session

Evaluates speaking performance from a complete session's conversation data using LLM analysis.

**Endpoint**: `POST /speaking/evaluate`

**Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "session_id": "string (UUID)",
  "language": "string (default: english)",
  "user_level": "string (default: intermediate)",
  "user_id": "string (UUID, optional)",
  "save_evaluation": "boolean (default: true)"
}
```

**Response** (200 OK):
```json
{
  "evaluation_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "abc-123-def-456",
  "total_turns": 25,
  "overall_score": 78,
  "scores": {
    "fluency": 75,
    "pronunciation": 80,
    "vocabulary": 78,
    "grammar": 76,
    "coherence": 82,
    "comprehension": 79
  },
  "strengths": [
    "Good conversational flow and natural pacing",
    "Clear pronunciation of common words",
    "Active participation and engagement"
  ],
  "improvements": [
    "Expand vocabulary range for complex topics",
    "Work on complex sentence structures",
    "Improve grammar accuracy in past tense"
  ],
  "suggestions": [
    "Practice with native speakers daily for 15-20 minutes",
    "Record yourself speaking and review for pronunciation",
    "Focus on learning common idioms and expressions",
    "Study advanced grammar patterns systematically",
    "Listen to podcasts in the target language"
  ],
  "conversation_summary": "The conversation covered daily routines, hobbies, and future plans. Student showed good comprehension and actively participated.",
  "feedback_summary": "Great progress! Your conversational skills are developing well. Focus on expanding your vocabulary and working on more complex grammatical structures to reach the next level.",
  "fluency_level": "intermediate",
  "vocabulary_range": "moderate",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Error Responses**:

- `400 Bad Request`: Invalid session_id format
```json
{
  "detail": "Invalid session_id format"
}
```

- `500 Internal Server Error`: Evaluation failed
```json
{
  "detail": "Evaluation failed: [error message]"
}
```

---

### 2. Get Speaking Tips

Retrieves personalized speaking improvement tips for a specific language and proficiency level.

**Endpoint**: `GET /speaking/tips`

**Query Parameters**:
- `language` (string, optional): Target language (default: "english")
- `proficiency_level` (string, optional): User proficiency level (default: "intermediate")

**Example Request**:
```
GET /speaking/tips?language=english&proficiency_level=intermediate
```

**Response** (200 OK):
```json
{
  "language": "english",
  "proficiency_level": "intermediate",
  "tips": [
    "Practice speaking daily for at least 15 minutes",
    "Record yourself and listen back to identify areas for improvement",
    "Focus on pronunciation by mimicking native speakers",
    "Don't be afraid to make mistakes - they're part of learning",
    "Use language learning apps with speaking exercises",
    "Find a conversation partner or join a language exchange",
    "Think in the target language to improve fluency",
    "Learn common phrases and expressions for natural conversation",
    "Watch movies or shows in the target language with subtitles",
    "Practice speaking about topics that interest you"
  ]
}
```

**Error Response**:

- `500 Internal Server Error`: Failed to retrieve tips
```json
{
  "detail": "Failed to retrieve speaking tips"
}
```

---

### 3. Get Evaluation by Session ID

Retrieves the most recent speaking evaluation for a specific session.

**Endpoint**: `GET /speaking/evaluation/{session_id}`

**Path Parameters**:
- `session_id` (string, UUID): The session ID to retrieve evaluation for

**Example Request**:
```
GET /speaking/evaluation/abc-123-def-456
```

**Response** (200 OK):
```json
{
  "evaluation_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "abc-123-def-456",
  "total_turns": 25,
  "overall_score": 78,
  "scores": { ... },
  "strengths": [ ... ],
  "improvements": [ ... ],
  "suggestions": [ ... ],
  "conversation_summary": "...",
  "feedback_summary": "...",
  "fluency_level": "intermediate",
  "vocabulary_range": "moderate",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Error Response**:

- `404 Not Found`: Evaluation not found
```json
{
  "detail": "Evaluation not found"
}
```

---

### 4. Get User Evaluations

Retrieves all speaking evaluations for a specific user with pagination support.

**Endpoint**: `GET /speaking/evaluations/user/{user_id}`

**Path Parameters**:
- `user_id` (string, UUID): The user ID

**Query Parameters**:
- `limit` (integer, optional): Maximum number of results (default: 20)
- `offset` (integer, optional): Number of results to skip (default: 0)

**Example Request**:
```
GET /speaking/evaluations/user/user-123?limit=10&offset=0
```

**Response** (200 OK):
```json
[
  {
    "evaluation_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "abc-123",
    "total_turns": 25,
    "overall_score": 78,
    "scores": { ... },
    "strengths": [ ... ],
    "improvements": [ ... ],
    "suggestions": [ ... ],
    "conversation_summary": "...",
    "feedback_summary": "...",
    "fluency_level": "intermediate",
    "vocabulary_range": "moderate",
    "created_at": "2025-01-15T10:30:00Z"
  },
  {
    "evaluation_id": "660e8400-e29b-41d4-a716-446655440001",
    "session_id": "def-456",
    "total_turns": 30,
    "overall_score": 82,
    ...
  }
]
```

**Error Response**:

- `500 Internal Server Error`: Failed to retrieve evaluations
```json
{
  "detail": "Failed to retrieve evaluations"
}
```

---

### 5. Delete Evaluation

Deletes a specific speaking evaluation.

**Endpoint**: `DELETE /speaking/evaluation/{evaluation_id}`

**Path Parameters**:
- `evaluation_id` (string, UUID): The evaluation ID to delete

**Example Request**:
```
DELETE /speaking/evaluation/550e8400-e29b-41d4-a716-446655440000
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Evaluation deleted successfully"
}
```

**Error Responses**:

- `404 Not Found`: Evaluation not found
```json
{
  "detail": "Evaluation not found"
}
```

- `500 Internal Server Error`: Failed to delete
```json
{
  "detail": "Failed to delete evaluation"
}
```

---

## Data Models

### SpeakingEvaluationRequest
```typescript
{
  session_id: string;        // UUID of the session to evaluate
  language: string;          // Target language (e.g., "english")
  user_level: string;        // Proficiency level (e.g., "intermediate")
  user_id?: string;          // Optional user UUID
  save_evaluation: boolean;  // Whether to save to database
}
```

### SpeakingEvaluationResponse
```typescript
{
  evaluation_id: string;           // Unique evaluation ID
  session_id: string;              // Session ID that was evaluated
  total_turns: number;             // Number of user speaking turns
  overall_score: number;           // Overall score (0-100)
  scores: {                        // Detailed scores
    fluency: number;               // 0-100
    pronunciation: number;         // 0-100
    vocabulary: number;            // 0-100
    grammar: number;               // 0-100
    coherence: number;             // 0-100
    comprehension: number;         // 0-100
  };
  strengths: string[];             // List of identified strengths
  improvements: string[];          // Areas for improvement
  suggestions: string[];           // Specific actionable suggestions
  conversation_summary: string;    // What the conversation was about
  feedback_summary: string;        // Overall feedback and encouragement
  fluency_level: string;           // beginner|elementary|intermediate|upper-intermediate|advanced
  vocabulary_range: string;        // limited|basic|moderate|good|extensive
  created_at: string;              // ISO 8601 timestamp
}
```

---

## Code Examples

### Python
```python
import httpx
import asyncio

async def evaluate_session(session_id: str, user_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/speaking/evaluate",
            json={
                "session_id": session_id,
                "language": "english",
                "user_level": "intermediate",
                "user_id": user_id,
                "save_evaluation": True
            }
        )
        return response.json()

result = asyncio.run(evaluate_session("abc-123", "user-456"))
print(f"Overall Score: {result['overall_score']}/100")
```

### JavaScript/TypeScript
```typescript
async function evaluateSpeaking(sessionId: string, userId: string) {
  const response = await fetch('http://localhost:8000/speaking/evaluate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      language: 'english',
      user_level: 'intermediate',
      user_id: userId,
      save_evaluation: true,
    }),
  });

  const data = await response.json();
  console.log(`Overall Score: ${data.overall_score}/100`);
  return data;
}
```

### cURL
```bash
# Evaluate a session
curl -X POST "http://localhost:8000/speaking/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123",
    "language": "english",
    "user_level": "intermediate",
    "user_id": "user-456",
    "save_evaluation": true
  }'

# Get speaking tips
curl "http://localhost:8000/speaking/tips?language=english&proficiency_level=intermediate"

# Get evaluation by session ID
curl "http://localhost:8000/speaking/evaluation/abc-123"

# Get user evaluations
curl "http://localhost:8000/speaking/evaluations/user/user-456?limit=10"

# Delete evaluation
curl -X DELETE "http://localhost:8000/speaking/evaluation/550e8400-e29b-41d4-a716-446655440000"
```

---

## Response Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created (for POST endpoints) |
| 400 | Bad Request - Invalid input data |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Service initialization failed |

---

## Rate Limiting

Currently no rate limiting is enforced, but it's recommended for production:
- Evaluation endpoint: 10 requests per minute per user
- Tips endpoint: 20 requests per minute per user

---

## Notes

1. **Session Data Required**: The session must have conversation turns in the database
2. **Minimum Turns**: For meaningful evaluation, sessions should have at least 5-10 user turns
3. **Async Processing**: All endpoints are async for better performance
4. **Background Saves**: Database saves happen in background tasks
5. **LLM Dependencies**: Requires valid GEMINI_API_KEY environment variable

---

## Interactive Documentation

View interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
