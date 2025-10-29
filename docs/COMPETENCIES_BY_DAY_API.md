# Competencies by Day API Documentation

## Overview
This document describes the new endpoint for retrieving skill competencies (mastery breakdown) for listening, reading, and grammar by specific day.

**Endpoint:** `GET /api/v1/users/{user_id}/competencies/{modality}/day/{day_code}`

**Authentication:** Required (JWT token)

---

## Endpoint Details

### URL Structure
```
GET /api/v1/users/{user_id}/competencies/{modality}/day/{day_code}
```

### Path Parameters
- **user_id** (UUID, required): The user's unique identifier
- **modality** (string, required): One of: `listening`, `reading`, or `grammar`
- **day_code** (string, required): Specific day in format `dayN` (e.g., `day1`, `day5`, `day10`)

### Headers
```
Authorization: Bearer <your-jwt-token>
Content-Type: application/json
```

---

## API Call Examples

### 1. Get Listening Competencies for Day 1

**Request:**
```bash
GET http://localhost:8080/api/v1/users/550e8400-e29b-41d4-a716-446655440000/competencies/listening/day/day1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "modality": "listening",
  "date_range": "day1",
  "skills": [
    {
      "skill": "details",
      "sessions_practiced": 2,
      "total_questions": 8,
      "correct_answers": 6,
      "overall_mastery_pct": 75,
      "mastery_level": "proficient",
      "trend": "stable",
      "avg_time_per_question": 42.5
    },
    {
      "skill": "inference",
      "sessions_practiced": 2,
      "total_questions": 5,
      "correct_answers": 3,
      "overall_mastery_pct": 60,
      "mastery_level": "developing",
      "trend": "stable",
      "avg_time_per_question": 55.2
    },
    {
      "skill": "main_idea",
      "sessions_practiced": 2,
      "total_questions": 6,
      "correct_answers": 5,
      "overall_mastery_pct": 83,
      "mastery_level": "proficient",
      "trend": "stable",
      "avg_time_per_question": 38.7
    },
    {
      "skill": "vocabulary",
      "sessions_practiced": 1,
      "total_questions": 4,
      "correct_answers": 4,
      "overall_mastery_pct": 100,
      "mastery_level": "advanced",
      "trend": "stable",
      "avg_time_per_question": 25.0
    }
  ]
}
```

---

### 2. Get Reading Competencies for Day 5

**Request:**
```bash
GET http://localhost:8080/api/v1/users/550e8400-e29b-41d4-a716-446655440000/competencies/reading/day/day5
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "modality": "reading",
  "date_range": "day5",
  "skills": [
    {
      "skill": "comprehension",
      "sessions_practiced": 3,
      "total_questions": 15,
      "correct_answers": 12,
      "overall_mastery_pct": 80,
      "mastery_level": "proficient",
      "trend": "stable",
      "avg_time_per_question": 62.3
    },
    {
      "skill": "inference",
      "sessions_practiced": 3,
      "total_questions": 10,
      "correct_answers": 7,
      "overall_mastery_pct": 70,
      "mastery_level": "developing",
      "trend": "stable",
      "avg_time_per_question": 75.8
    },
    {
      "skill": "vocabulary",
      "sessions_practiced": 2,
      "total_questions": 12,
      "correct_answers": 10,
      "overall_mastery_pct": 83,
      "mastery_level": "proficient",
      "trend": "stable",
      "avg_time_per_question": 48.5
    }
  ]
}
```

---

### 3. Get Grammar Competencies for Day 10

**Request:**
```bash
GET http://localhost:8080/api/v1/users/550e8400-e29b-41d4-a716-446655440000/competencies/grammar/day/day10
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "modality": "grammar",
  "date_range": "day10",
  "skills": [
    {
      "skill": "articles",
      "sessions_practiced": 1,
      "total_questions": 8,
      "correct_answers": 6,
      "overall_mastery_pct": 75,
      "mastery_level": "proficient",
      "trend": "stable",
      "avg_time_per_question": 35.2
    },
    {
      "skill": "prepositions",
      "sessions_practiced": 2,
      "total_questions": 10,
      "correct_answers": 8,
      "overall_mastery_pct": 80,
      "mastery_level": "proficient",
      "trend": "stable",
      "avg_time_per_question": 28.9
    },
    {
      "skill": "pronouns",
      "sessions_practiced": 2,
      "total_questions": 7,
      "correct_answers": 5,
      "overall_mastery_pct": 71,
      "mastery_level": "developing",
      "trend": "stable",
      "avg_time_per_question": 42.1
    },
    {
      "skill": "verb_tenses",
      "sessions_practiced": 2,
      "total_questions": 12,
      "correct_answers": 11,
      "overall_mastery_pct": 92,
      "mastery_level": "advanced",
      "trend": "stable",
      "avg_time_per_question": 31.5
    }
  ]
}
```

---

## Response Fields

### Root Level
- **modality** (string): The competency area - `listening`, `reading`, or `grammar`
- **date_range** (string): The specific day code (e.g., `day1`, `day5`)
- **skills** (array): List of skill competency details

### Skill Detail Object
- **skill** (string): Name of the skill (e.g., `vocabulary`, `comprehension`, `verb_tenses`)
- **sessions_practiced** (integer): Number of sessions where this skill was practiced on this day
- **total_questions** (integer): Total number of questions for this skill on this day
- **correct_answers** (integer): Number of correct answers for this skill on this day
- **overall_mastery_pct** (integer): Mastery percentage (0-100) for this skill on this day
- **mastery_level** (string): Mastery level - `beginner`, `developing`, `proficient`, or `advanced`
- **trend** (string): Trend indicator - `stable` (always for single day queries)
- **avg_time_per_question** (float): Average time spent per question in seconds

---

## Mastery Levels

The mastery percentage is mapped to levels as follows:

| Mastery %   | Level        |
|-------------|--------------|
| 0-49%       | beginner     |
| 50-74%      | developing   |
| 75-89%      | proficient   |
| 90-100%     | advanced     |

---

## Error Responses

### 400 Bad Request - Invalid Modality
```json
{
  "detail": "Modality must be 'listening', 'reading', or 'grammar'"
}
```

### 400 Bad Request - Invalid Day Code
```json
{
  "detail": "Day code must be in format 'dayN' (e.g., 'day1', 'day10')"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Cannot view another user's competencies"
}
```

### 404 Not Found - No Data for Day
```json
{
  "modality": "listening",
  "date_range": "day99",
  "skills": []
}
```

---

## Use Cases

### 1. Daily Progress Dashboard
Display skill-by-skill breakdown after completing a day's activities:
```
User completes Day 3 listening exercises
→ Call: GET /users/{id}/competencies/listening/day/day3
→ Show strengths and weaknesses for that specific day
```

### 2. Day-by-Day Review
Allow users to review their performance on any past day:
```
User wants to review their reading skills from Day 7
→ Call: GET /users/{id}/competencies/reading/day/day7
→ Show detailed skill breakdown for that day
```

### 3. Skill Tracking Over Days
Compare performance across multiple days:
```
Fetch competencies for day1, day2, day3, etc.
→ Build charts showing skill improvement over time
```

---

## Code Examples

### Python (requests)
```python
import requests

BASE_URL = "http://localhost:8080/api/v1"
USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TOKEN = "your-jwt-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Get listening competencies for day 1
response = requests.get(
    f"{BASE_URL}/users/{USER_ID}/competencies/listening/day/day1",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    print(f"Modality: {data['modality']}")
    print(f"Day: {data['date_range']}")
    print(f"\nSkills:")
    for skill in data['skills']:
        print(f"  - {skill['skill']}: {skill['overall_mastery_pct']}% ({skill['mastery_level']})")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

### JavaScript (fetch)
```javascript
const BASE_URL = "http://localhost:8080/api/v1";
const USER_ID = "550e8400-e29b-41d4-a716-446655440000";
const TOKEN = "your-jwt-token";

async function getCompetencies(modality, dayCode) {
  const response = await fetch(
    `${BASE_URL}/users/${USER_ID}/competencies/${modality}/day/${dayCode}`,
    {
      headers: {
        "Authorization": `Bearer ${TOKEN}`,
        "Content-Type": "application/json"
      }
    }
  );

  if (response.ok) {
    const data = await response.json();
    console.log(`${data.modality} - ${data.date_range}`);
    data.skills.forEach(skill => {
      console.log(`${skill.skill}: ${skill.overall_mastery_pct}% (${skill.mastery_level})`);
    });
  } else {
    console.error(`Error: ${response.status} - ${await response.text()}`);
  }
}

// Usage
getCompetencies("reading", "day5");
```

### cURL
```bash
# Listening competencies for day 1
curl -X GET \
  "http://localhost:8080/api/v1/users/550e8400-e29b-41d4-a716-446655440000/competencies/listening/day/day1" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json"

# Reading competencies for day 5
curl -X GET \
  "http://localhost:8080/api/v1/users/550e8400-e29b-41d4-a716-446655440000/competencies/reading/day/day5" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json"

# Grammar competencies for day 10
curl -X GET \
  "http://localhost:8080/api/v1/users/550e8400-e29b-41d4-a716-446655440000/competencies/grammar/day/day10" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json"
```

---

## Implementation Notes

### Data Source
- The endpoint aggregates data from all sessions for the specified user, modality, and day
- It pulls from the `lrg_sessions`, `lrg_answers`, and `lrg_session_skills` tables
- Skills are calculated based on actual performance in that day's sessions

### Performance
- The endpoint performs multiple database queries but is optimized for day-specific filtering
- Results are calculated on-demand (not cached)
- For large datasets, consider adding pagination if needed

### Trend Field
- For single-day queries, `trend` is always `"stable"`
- To get actual trends (improving/declining), use the range endpoint:
  ```
  GET /api/v1/users/{user_id}/skills/progress?modality=listening&from_day=day1&to_day=day10
  ```

---

## Related Endpoints

### Get Competencies Across Multiple Days
```
GET /api/v1/users/{user_id}/skills/progress?modality=listening&from_day=day1&to_day=day10
```

### Get Overall Mastery Across All Modalities
```
GET /api/v1/users/{user_id}/mastery-overview
```

### Get Session-Specific Mastery
```
GET /api/v1/sessions/{session_id}/mastery
```

---

## Summary

This endpoint provides a powerful way to retrieve skill competencies for a specific day, making it easy to:
- ✅ Track daily progress in listening, reading, and grammar
- ✅ Identify strengths and weaknesses for each day
- ✅ Build day-by-day skill progression dashboards
- ✅ Generate personalized feedback based on daily performance

**Endpoint Format:**
```
GET /api/v1/users/{user_id}/competencies/{modality}/day/{day_code}
```

**Supported Modalities:** `listening`, `reading`, `grammar`

**Day Format:** `day1`, `day2`, `day3`, ... `dayN`
