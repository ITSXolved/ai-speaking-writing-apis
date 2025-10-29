## Competency Tracking with Day Codes - Complete Guide

## Overview

The Competency Tracking system allows you to save and retrieve speaking and writing evaluation results organized by **day codes** (e.g., day1, day2, day3). This enables tracking user progress across a curriculum structure.

## Database Changes

### Migration Required

Run the SQL migration to add `day_code` fields:

```bash
# migrations/add_day_code_to_evaluations.sql
```

This adds:
- `day_code` column to `speaking_evaluations` table
- `day_code` column to `writing_evaluations` table
- Foreign key constraints to `study_days` table
- Indexes for better query performance

### Updated Tables

**`speaking_evaluations`**
```sql
- id (uuid, PK)
- user_id (uuid)
- session_id (uuid)
- day_code (text) ← NEW
- language (varchar)
- user_level (varchar)
- total_turns (int)
- scores (jsonb)
- strengths (jsonb)
- improvements (jsonb)
- suggestions (jsonb)
- conversation_summary (text)
- overall_score (int)
- feedback_summary (text)
- fluency_level (varchar)
- vocabulary_range (varchar)
- created_at (timestamp)
- updated_at (timestamp)
```

**`writing_evaluations`**
```sql
- id (uuid, PK)
- user_id (text)
- day_code (text) ← NEW
- original_text (text)
- language (text)
- writing_type (text)
- user_level (text)
- scores (jsonb)
- strengths (array)
- improvements (array)
- suggestions (array)
- improved_version (text)
- overall_score (int)
- feedback_summary (text)
- created_at (timestamp)
- updated_at (timestamp)
```

## API Endpoints

### Base URL
```
/api/competency
```

---

### 1. Save Speaking Evaluation

**POST** `/api/competency/speaking/save`

Save a speaking evaluation result with day_code tracking.

**Request Body:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "session_id": "123e4567-e89b-12d3-a456-426614174001",
  "day_code": "day1",
  "language": "english",
  "user_level": "intermediate",
  "total_turns": 10,
  "scores": {
    "fluency": 75,
    "pronunciation": 80,
    "vocabulary": 70,
    "grammar": 78
  },
  "strengths": [
    "Good pronunciation of complex words",
    "Natural conversation flow"
  ],
  "improvements": [
    "Use more varied vocabulary",
    "Practice past tense forms"
  ],
  "suggestions": [
    "Practice daily conversations for 10 minutes",
    "Listen to native speakers"
  ],
  "conversation_summary": "Discussed daily routines and weekend plans",
  "overall_score": 76,
  "feedback_summary": "Good progress with conversation skills",
  "fluency_level": "intermediate",
  "vocabulary_range": "adequate"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "evaluation_id": "987e6543-e21b-12d3-a456-426614174002",
  "day_code": "day1",
  "overall_score": 76,
  "message": "Speaking evaluation saved successfully"
}
```

---

### 2. Save Writing Evaluation

**POST** `/api/competency/writing/save`

Save a writing evaluation result with day_code tracking.

**Request Body:**
```json
{
  "user_id": "user123",
  "day_code": "day1",
  "original_text": "My favorite hobby is reading book. I like read mystery and science fiction.",
  "language": "english",
  "writing_type": "general",
  "user_level": "intermediate",
  "scores": {
    "grammar": 70,
    "vocabulary": 75,
    "coherence": 80,
    "mechanics": 65
  },
  "strengths": [
    "Clear main idea",
    "Good sentence structure"
  ],
  "improvements": [
    "Use 'books' (plural)",
    "Correct: 'I like reading' or 'I like to read'"
  ],
  "suggestions": [
    "Practice plural forms",
    "Read more English texts"
  ],
  "improved_version": "My favorite hobby is reading books. I like reading mystery and science fiction novels.",
  "overall_score": 72,
  "feedback_summary": "Good writing with minor grammar improvements needed"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "evaluation_id": "987e6543-e21b-12d3-a456-426614174003",
  "day_code": "day1",
  "overall_score": 72,
  "message": "Writing evaluation saved successfully"
}
```

---

### 3. Get User Competency (All Days)

**GET** `/api/competency/user/{user_id}`

Get user's progress across all available days.

**Example Request:**
```bash
curl http://localhost:8000/api/competency/user/user123
```

**Response (200 OK):**
```json
{
  "user_id": "user123",
  "total_days_available": 30,
  "days_completed": 5,
  "progress_by_day": [
    {
      "day_code": "day1",
      "speaking_completed": true,
      "writing_completed": true,
      "speaking_score": 76,
      "writing_score": 72,
      "speaking_evaluation_id": "987e6543-e21b-12d3-a456-426614174002",
      "writing_evaluation_id": "987e6543-e21b-12d3-a456-426614174003",
      "completed_at": "2025-10-27T14:30:00Z"
    },
    {
      "day_code": "day2",
      "speaking_completed": true,
      "writing_completed": false,
      "speaking_score": 80,
      "writing_score": null,
      "speaking_evaluation_id": "987e6543-e21b-12d3-a456-426614174004",
      "writing_evaluation_id": null,
      "completed_at": "2025-10-28T10:15:00Z"
    },
    {
      "day_code": "day3",
      "speaking_completed": false,
      "writing_completed": false,
      "speaking_score": null,
      "writing_score": null,
      "speaking_evaluation_id": null,
      "writing_evaluation_id": null,
      "completed_at": null
    }
  ],
  "average_speaking_score": 78.0,
  "average_writing_score": 72.0
}
```

---

### 4. Get User Progress for Specific Day

**GET** `/api/competency/user/{user_id}/day/{day_code}`

Get user's progress for a single day.

**Example Request:**
```bash
curl http://localhost:8000/api/competency/user/user123/day/day1
```

**Response (200 OK):**
```json
{
  "day_code": "day1",
  "speaking_completed": true,
  "writing_completed": true,
  "speaking_score": 76,
  "writing_score": 72,
  "speaking_evaluation_id": "987e6543-e21b-12d3-a456-426614174002",
  "writing_evaluation_id": "987e6543-e21b-12d3-a456-426614174003",
  "completed_at": "2025-10-27T14:30:00Z"
}
```

---

### 5. Get Day Statistics

**GET** `/api/competency/day/{day_code}/stats`

Get statistics for a specific day across all users.

**Example Request:**
```bash
curl http://localhost:8000/api/competency/day/day1/stats
```

**Response (200 OK):**
```json
{
  "day_code": "day1",
  "total_users_attempted": 150,
  "speaking_completions": 120,
  "writing_completions": 110,
  "average_speaking_score": 75.5,
  "average_writing_score": 73.2,
  "top_performers": [
    {
      "user_id": "user456",
      "speaking_score": 95,
      "writing_score": 92,
      "combined_score": 93.5
    },
    {
      "user_id": "user789",
      "speaking_score": 90,
      "writing_score": 91,
      "combined_score": 90.5
    }
  ]
}
```

---

## Usage Examples

### Example 1: Save Evaluation After Speaking Session

```python
import requests

# After completing a speaking session and getting evaluation
evaluation_data = {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "session_id": "session-uuid",
    "day_code": "day1",  # Current day
    "language": "english",
    "user_level": "intermediate",
    "total_turns": 10,
    "scores": {
        "fluency": 75,
        "pronunciation": 80,
        "vocabulary": 70,
        "grammar": 78
    },
    "strengths": ["Good pronunciation"],
    "improvements": ["Use varied vocabulary"],
    "suggestions": ["Practice daily"],
    "conversation_summary": "Discussed hobbies",
    "overall_score": 76,
    "feedback_summary": "Good progress",
    "fluency_level": "intermediate",
    "vocabulary_range": "adequate"
}

response = requests.post(
    "http://localhost:8000/api/competency/speaking/save",
    json=evaluation_data
)

if response.status_code == 201:
    result = response.json()
    print(f"Saved! Evaluation ID: {result['evaluation_id']}")
```

### Example 2: Check User Progress Dashboard

```python
import requests

# Get user's complete progress
user_id = "user123"
response = requests.get(
    f"http://localhost:8000/api/competency/user/{user_id}"
)

if response.status_code == 200:
    data = response.json()

    print(f"User: {data['user_id']}")
    print(f"Days Completed: {data['days_completed']}/{data['total_days_available']}")
    print(f"Avg Speaking Score: {data['average_speaking_score']}")
    print(f"Avg Writing Score: {data['average_writing_score']}")

    print("\nProgress by Day:")
    for day in data['progress_by_day']:
        status = "✓" if day['speaking_completed'] and day['writing_completed'] else "○"
        print(f"{status} {day['day_code']}: Speaking={day['speaking_score']}, Writing={day['writing_score']}")
```

### Example 3: Check if User Completed Today's Tasks

```python
import requests

user_id = "user123"
current_day = "day5"

response = requests.get(
    f"http://localhost:8000/api/competency/user/{user_id}/day/{current_day}"
)

if response.status_code == 200:
    day_progress = response.json()

    if day_progress['speaking_completed'] and day_progress['writing_completed']:
        print(f"✓ User completed {current_day}!")
        print(f"Speaking: {day_progress['speaking_score']}/100")
        print(f"Writing: {day_progress['writing_score']}/100")
    else:
        print(f"User hasn't completed {current_day} yet")
        if not day_progress['speaking_completed']:
            print("- Speaking task pending")
        if not day_progress['writing_completed']:
            print("- Writing task pending")
```

---

## Frontend Integration

### React Example

```typescript
// Save evaluation
const saveEvaluation = async (type: 'speaking' | 'writing', data: any) => {
  const endpoint = `/api/competency/${type}/save`;

  const response = await fetch(`http://localhost:8000${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error('Failed to save evaluation');
  }

  return response.json();
};

// Get user progress
const getUserProgress = async (userId: string) => {
  const response = await fetch(
    `http://localhost:8000/api/competency/user/${userId}`
  );

  if (!response.ok) {
    throw new Error('Failed to fetch progress');
  }

  return response.json();
};

// React Component
function ProgressDashboard({ userId }: { userId: string }) {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    getUserProgress(userId).then(setProgress);
  }, [userId]);

  if (!progress) return <div>Loading...</div>;

  return (
    <div>
      <h2>Your Progress</h2>
      <p>Completed: {progress.days_completed}/{progress.total_days_available} days</p>
      <p>Avg Speaking: {progress.average_speaking_score}/100</p>
      <p>Avg Writing: {progress.average_writing_score}/100</p>

      <div className="day-grid">
        {progress.progress_by_day.map(day => (
          <DayCard key={day.day_code} day={day} />
        ))}
      </div>
    </div>
  );
}
```

---

## Testing

Run the test notebook:

```bash
jupyter notebook test_competencies_endpoints.ipynb
```

Or use curl:

```bash
# Test saving speaking evaluation
curl -X POST http://localhost:8000/api/competency/speaking/save \
  -H "Content-Type: application/json" \
  -d @test_speaking_data.json

# Test getting user progress
curl http://localhost:8000/api/competency/user/user123
```

---

## Error Handling

### 404 Not Found
```json
{
  "detail": "No data found for day day1"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to save speaking evaluation: Database connection error"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "overall_score"],
      "msg": "ensure this value is less than or equal to 100",
      "type": "value_error.number.not_le"
    }
  ]
}
```

---

## Best Practices

1. **Always include day_code** when saving evaluations
2. **Use UUID for user_id** in speaking evaluations (matches auth.users)
3. **Use text for user_id** in writing evaluations (legacy format)
4. **Check if day exists** in `study_days` table before saving
5. **Cache user progress** on frontend to reduce API calls
6. **Poll for updates** if showing real-time progress
7. **Handle missing scores gracefully** (null when not completed)

---

## Performance Tips

1. **Indexes are created** on user_id and day_code for fast queries
2. **Use pagination** if fetching many users' progress
3. **Cache day statistics** (updated hourly is sufficient)
4. **Batch save operations** when possible

---

## Next Steps

1. Run the SQL migration
2. Test the endpoints with Postman or curl
3. Integrate into your frontend application
4. Set up monitoring for evaluation saves
5. Create admin dashboard using day statistics

---

**Last Updated**: 2025-10-29
**Version**: 1.0.0
