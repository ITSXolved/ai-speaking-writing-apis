# Complete API Endpoints Documentation

## Overview
This document provides a comprehensive reference for all API endpoints available in the Ziya LRG (Learning, Reading, Grammar) API. The API is built with FastAPI and follows RESTful principles.

**Base URL:** `/api/v1`

**Authentication:** All endpoints (except meta endpoints) require authentication via JWT token passed in the Authorization header.

---

## Table of Contents
1. [Session Management](#1-session-management)
2. [XP & Streaks](#2-xp--streaks)
3. [Skill Mastery](#3-skill-mastery)
4. [Listening Evaluation](#4-listening-evaluation)
5. [Dashboard & Analytics](#5-dashboard--analytics)
6. [Content Management](#6-content-management)
7. [Unified APIs](#7-unified-apis)
8. [Meta Endpoints](#8-meta-endpoints)

---

## 1. Session Management

### 1.1 Start Session
**Endpoint:** `POST /api/v1/sessions`

**Description:** Start a new test session for LRG activities.

**Authentication:** Required

**Request Body:**
```json
{
  "user_id": "uuid",
  "modality": "listening|reading|grammar",
  "day_code": "day1"
}
```

**Response:** `201 Created`
```json
{
  "session_id": "uuid",
  "user_id": "uuid",
  "modality": "listening",
  "day_code": "day1",
  "started_at": "2025-01-15T10:30:00Z"
}
```

**Use Case:** Called when user starts a new learning session. The session_id is used to submit answers later.

---

### 1.2 Submit Session
**Endpoint:** `POST /api/v1/sessions/{session_id}/submit`

**Description:** Submit completed session with answers. Triggers XP calculation, streak updates, and badge awards.

**Authentication:** Required

**Path Parameters:**
- `session_id`: UUID of the session

**Request Body:**
```json
{
  "duration_sec": 300,
  "answers": [
    {
      "question_id": "q1",
      "user_answer": "answer",
      "correct_answer": "answer",
      "is_correct": true,
      "skill": "vocabulary",
      "time_taken_sec": 30
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "score_pct": 85.5,
  "xp_earned": 30,
  "badges_earned": ["first_session"],
  "streak_updated": true,
  "current_streak": 5
}
```

**Use Case:** Called when user completes a session. Automatically calculates performance metrics and rewards.

---

### 1.3 Get Session Details
**Endpoint:** `GET /api/v1/sessions/{session_id}`

**Description:** Retrieve detailed information about a specific session.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "user_id": "uuid",
  "modality": "listening",
  "day_code": "day1",
  "started_at": "2025-01-15T10:30:00Z",
  "completed_at": "2025-01-15T10:35:00Z",
  "duration_sec": 300,
  "score_pct": 85.5,
  "answers": [...]
}
```

**Use Case:** Review past session performance and answers.

---

### 1.4 Get User Sessions
**Endpoint:** `GET /api/v1/sessions`

**Description:** Get paginated list of user's session history.

**Authentication:** Required

**Query Parameters:**
- `limit`: Number of sessions per page (default: 10, max: 100)
- `offset`: Pagination offset (default: 0)

**Response:** `200 OK`
```json
{
  "sessions": [...],
  "limit": 10,
  "offset": 0,
  "count": 10
}
```

**Use Case:** Display user's learning history and progress over time.

---

## 2. XP & Streaks

### 2.1 Get User XP
**Endpoint:** `GET /api/v1/users/{user_id}/xp`

**Description:** Get user's total XP, today's XP, and level progression.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "total_xp": 1250,
  "today_xp": 50,
  "current_level": 5,
  "xp_to_next_level": 250,
  "level_progress_pct": 60
}
```

**Use Case:** Display XP progress in user profile or dashboard.

---

### 2.2 Get Daily XP Breakdown
**Endpoint:** `GET /api/v1/users/{user_id}/xp/daily`

**Description:** Get detailed breakdown of XP earned today.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "date": "2025-01-15",
  "xp_earned_today": 50,
  "xp_goal": 100,
  "goal_completion_pct": 50,
  "sessions_today": 2,
  "breakdown": [
    {
      "source": "session_complete",
      "amount": 20,
      "occurred_at": "2025-01-15T10:35:00Z"
    }
  ]
}
```

**Use Case:** Show daily progress toward XP goals.

---

### 2.3 Get User Level
**Endpoint:** `GET /api/v1/users/{user_id}/level`

**Description:** Get detailed level information.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "current_level": 5,
  "level_name": "Intermediate",
  "total_xp": 1250,
  "xp_to_next_level": 250,
  "progress_pct": 60
}
```

**Use Case:** Display level badge and progress bar.

---

### 2.4 Get Streak Information
**Endpoint:** `GET /api/v1/users/{user_id}/streak`

**Description:** Get current streak, longest streak, and streak status.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "current_streak": 7,
  "longest_streak": 15,
  "last_active_date": "2025-01-15",
  "is_active_today": true,
  "streak_status": "active|at_risk|broken"
}
```

**Use Case:** Display streak information and motivate daily practice.

---

### 2.5 Get Daily Progress
**Endpoint:** `GET /api/v1/users/{user_id}/daily-progress`

**Description:** Get comprehensive daily progress including XP, sessions, and goals.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "date": "2025-01-15",
  "xp_earned": 50,
  "sessions_completed": 2,
  "time_spent_sec": 600,
  "perfect_day": false,
  "goals_met": ["daily_session"]
}
```

**Use Case:** Dashboard daily summary card.

---

### 2.6 Get Streak Calendar
**Endpoint:** `GET /api/v1/users/{user_id}/streak-calendar`

**Description:** Get calendar view of activity for a specific month.

**Authentication:** Required

**Query Parameters:**
- `month`: Optional month in format YYYY-MM (default: current month)

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "month": "2025-01",
  "days": [
    {
      "date": "2025-01-15",
      "sessions": 2,
      "xp_earned": 50,
      "is_perfect_day": false
    }
  ],
  "current_streak": 7,
  "perfect_days": 5
}
```

**Use Case:** Display activity calendar/heatmap.

---

## 3. Skill Mastery

### 3.1 Get Session Mastery
**Endpoint:** `GET /api/v1/sessions/{session_id}/mastery`

**Description:** Get skill-by-skill mastery breakdown for a session.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "overall_score_pct": 85.5,
  "duration_sec": 300,
  "skills": [
    {
      "skill": "vocabulary",
      "correct": 8,
      "total": 10,
      "mastery_pct": 80,
      "mastery_level": "proficient"
    }
  ],
  "mastery_distribution": {
    "mastered": 2,
    "proficient": 3,
    "developing": 1,
    "beginner": 0
  }
}
```

**Use Case:** Show detailed performance breakdown after completing a session.

---

### 3.2 Get User Skill Progress
**Endpoint:** `GET /api/v1/users/{user_id}/skills/progress`

**Description:** Get cumulative skill progress for a specific modality.

**Authentication:** Required

**Query Parameters:**
- `modality`: listening|reading|grammar (required)
- `from_day`: Optional start day (e.g., "day1")
- `to_day`: Optional end day (e.g., "day10")

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "modality": "listening",
  "skills": [
    {
      "skill": "vocabulary",
      "times_practiced": 15,
      "correct_total": 120,
      "attempts_total": 150,
      "mastery_pct": 80,
      "trend": "improving|stable|declining"
    }
  ]
}
```

**Use Case:** Track long-term skill development and identify strengths/weaknesses.

---

### 3.3 Get Mastery Overview
**Endpoint:** `GET /api/v1/users/{user_id}/mastery-overview`

**Description:** Get complete mastery overview across all modalities.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "listening": {
    "overall_mastery_pct": 75,
    "skills": [...]
  },
  "reading": {
    "overall_mastery_pct": 82,
    "skills": [...]
  },
  "grammar": {
    "overall_mastery_pct": 70,
    "skills": [...]
  }
}
```

**Use Case:** High-level overview of all learning areas.

---

## 4. Listening Evaluation

### 4.1 Start Listening Session
**Endpoint:** `POST /api/v1/listening/sessions`

**Description:** Start a new listening-specific session with audio.

**Authentication:** Required

**Request Body:**
```json
{
  "user_id": "uuid",
  "day_code": "day1",
  "audio_url": "https://storage.example.com/audio.mp3"
}
```

**Response:** `201 Created`
```json
{
  "session_id": "uuid",
  "user_id": "uuid",
  "day_code": "day1",
  "audio_url": "https://...",
  "started_at": "2025-01-15T10:30:00Z"
}
```

**Use Case:** Start a listening comprehension test.

---

### 4.2 Submit Listening Session
**Endpoint:** `POST /api/v1/listening/sessions/{session_id}/submit`

**Description:** Submit listening session with listening-specific metrics.

**Authentication:** Required

**Request Body:**
```json
{
  "answers": [...],
  "duration_sec": 300,
  "score_pct": 85.5,
  "xp_earned": 30,
  "audio_replay_count": 3,
  "completed_at": "2025-01-15T10:35:00Z"
}
```

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "score_pct": 85.5,
  "xp_earned": 30,
  "skill_mastery_updated": true,
  "audio_replay_count": 3
}
```

**Use Case:** Track how many times audio was replayed for analysis.

---

### 4.3 Get Listening Session
**Endpoint:** `GET /api/v1/listening/sessions/{session_id}`

**Description:** Get detailed listening session with audio replay data.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "day_code": "day1",
  "audio_url": "https://...",
  "audio_replay_count": 3,
  "duration_sec": 300,
  "score_pct": 85.5,
  "answers": [...]
}
```

**Use Case:** Review listening session performance.

---

### 4.4 Get Listening Session Mastery
**Endpoint:** `GET /api/v1/listening/sessions/{session_id}/mastery`

**Description:** Get skill mastery breakdown for listening session.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "overall_score_pct": 85.5,
  "audio_replay_count": 3,
  "skills": [...],
  "mastery_distribution": {...}
}
```

**Use Case:** Analyze listening-specific skill performance.

---

### 4.5 Get User Listening Progress
**Endpoint:** `GET /api/v1/listening/users/{user_id}/progress`

**Description:** Get comprehensive listening skill progress over time.

**Authentication:** Required

**Query Parameters:**
- `from_day`: Optional start day
- `to_day`: Optional end day

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "overall_mastery_pct": 75,
  "total_sessions": 20,
  "avg_audio_replays": 2.5,
  "skills": [
    {
      "skill": "main_idea",
      "mastery_pct": 80,
      "avg_time_per_question_sec": 45,
      "trend": "improving"
    }
  ]
}
```

**Use Case:** Track listening skill development over time.

---

### 4.6 Get Listening Analytics
**Endpoint:** `GET /api/v1/listening/users/{user_id}/analytics`

**Description:** Get comprehensive analytics for listening activities.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "total_sessions": 20,
  "avg_score_pct": 82,
  "total_duration_sec": 6000,
  "avg_audio_replays": 2.5,
  "strongest_skills": ["vocabulary", "main_idea"],
  "weakest_skills": ["inference"],
  "improvement_rate": 5.2
}
```

**Use Case:** Generate insights and recommendations for listening practice.

---

## 5. Dashboard & Analytics

### 5.1 Get Dashboard Summary
**Endpoint:** `GET /api/v1/dashboard/summary`

**Description:** Get comprehensive dashboard with all key metrics.

**Authentication:** Required

**Query Parameters:**
- `window`: Time window - 7d|30d|90d (default: 7d)

**Response:** `200 OK`
```json
{
  "streak_days": 7,
  "xp": {
    "total": 1250,
    "today": 50,
    "level": 5
  },
  "weekly_activity": {
    "sessions": 10,
    "time_sec": 3000,
    "days_active": 5
  },
  "accuracy_trend": [
    {"date": "2025-01-15", "accuracy": 85.5}
  ],
  "recent_results": [...],
  "badges": [...],
  "last_activity": "2025-01-15T10:35:00Z"
}
```

**Use Case:** Main dashboard view with all key information.

---

### 5.2 Get Modality Detail
**Endpoint:** `GET /api/v1/dashboard/detail/{modality}`

**Description:** Get detailed analytics for a specific modality.

**Authentication:** Required

**Path Parameters:**
- `modality`: listening|reading|grammar

**Response:** `200 OK`
```json
{
  "modality": "listening",
  "total_sessions": 20,
  "avg_accuracy": 82,
  "time_spent_sec": 6000,
  "accuracy_trend": [...],
  "topic_breakdown": [...],
  "best_performance": {...}
}
```

**Use Case:** Deep dive into specific learning area.

---

### 5.3 Get User Progress
**Endpoint:** `GET /api/v1/dashboard/progress`

**Description:** Get overall user progress metrics.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "total_xp": 1250,
  "current_streak": 7,
  "badges_earned": 15,
  "total_sessions": 50,
  "last_activity": "2025-01-15T10:35:00Z"
}
```

**Use Case:** User profile progress summary.

---

## 6. Content Management

### 6.1 Reading Content

#### Create Reading
**Endpoint:** `POST /api/v1/reading`

**Description:** Create new reading content for a day.

**Request Body:**
```json
{
  "day_code": "day1",
  "title": "Reading Title",
  "passage": "Text content...",
  "questions": [...],
  "difficulty_level": "beginner|intermediate|advanced"
}
```

**Response:** `201 Created`

#### Get Readings by Day
**Endpoint:** `GET /api/v1/reading/day/{day_code}`

**Query Parameters:**
- `difficulty_level`: Optional filter

**Response:** List of reading contents

#### Get Reading by ID
**Endpoint:** `GET /api/v1/reading/{reading_id}`

**Response:** Single reading content

#### Update Reading
**Endpoint:** `PUT /api/v1/reading/{reading_id}`

**Response:** Updated reading content

#### Delete Reading
**Endpoint:** `DELETE /api/v1/reading/{reading_id}`

**Response:** `204 No Content`

---

### 6.2 Listening Content

#### Create Listening
**Endpoint:** `POST /api/v1/listening`

**Description:** Create listening content with audio file upload.

**Request:** Multipart form data
- `payload`: JSON string with listening data
- `audio_file`: Audio file (MP3, WAV, etc.)

**Response:** `201 Created`
```json
{
  "listening_id": "uuid",
  "day_code": "day1",
  "audio_url": "https://...",
  "difficulty_level": "intermediate"
}
```

#### Get Listenings by Day
**Endpoint:** `GET /api/v1/listening/day/{day_code}`

**Query Parameters:**
- `difficulty_level`: Optional filter

#### Get Listening by ID
**Endpoint:** `GET /api/v1/listening/{listening_id}`

#### Update Listening
**Endpoint:** `PUT /api/v1/listening/{listening_id}`

**Request:** Multipart form data (audio file optional)

#### Delete Listening
**Endpoint:** `DELETE /api/v1/listening/{listening_id}`

---

### 6.3 Grammar Content

#### Create Grammar
**Endpoint:** `POST /api/v1/grammar`

**Request Body:**
```json
{
  "day_code": "day1",
  "topic": "Present Tense",
  "questions": [...],
  "difficulty_level": "beginner"
}
```

**Response:** `201 Created`

#### Get Grammar by Day
**Endpoint:** `GET /api/v1/grammar/day/{day_code}`

#### Get Grammar by ID
**Endpoint:** `GET /api/v1/grammar/{grammar_id}`

#### Update Grammar
**Endpoint:** `PUT /api/v1/grammar/{grammar_id}`

#### Delete Grammar
**Endpoint:** `DELETE /api/v1/grammar/{grammar_id}`

---

### 6.4 Writing Content

#### Create Writing
**Endpoint:** `POST /api/v1/writing`

**Request Body:**
```json
{
  "day_code": "day1",
  "topic": "Describe your day",
  "prompt": "Write about...",
  "difficulty_level": "intermediate"
}
```

**Response:** `201 Created`

#### Get Writings by Day
**Endpoint:** `GET /api/v1/writing/day/{day_code}`

#### Get Writing by ID
**Endpoint:** `GET /api/v1/writing/{writing_id}`

#### Update Writing
**Endpoint:** `PUT /api/v1/writing/{writing_id}`

#### Delete Writing
**Endpoint:** `DELETE /api/v1/writing/{writing_id}`

---

### 6.5 Speaking Content

#### Create Speaking
**Endpoint:** `POST /api/v1/speaking`

**Request Body:**
```json
{
  "day_code": "day1",
  "topic": "Introduce yourself",
  "teaching_mode_code": "conversation",
  "difficulty_level": "beginner"
}
```

**Response:** `201 Created`

#### Get Speaking by Day
**Endpoint:** `GET /api/v1/speaking/day/{day_code}`

#### Get Speaking by ID
**Endpoint:** `GET /api/v1/speaking/{speaking_id}`

#### Update Speaking
**Endpoint:** `PUT /api/v1/speaking/{speaking_id}`

#### Delete Speaking
**Endpoint:** `DELETE /api/v1/speaking/{speaking_id}`

---

## 7. Unified APIs

These endpoints combine data from multiple activity types (LRG, Writing, Speaking).

### 7.1 Get Unified Stats
**Endpoint:** `GET /api/v1/unified/stats`

**Description:** Get combined statistics across all activities.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "total_xp": 1250,
  "current_streak": 7,
  "longest_streak": 15,
  "lrg_sessions": 30,
  "writing_evaluations": 10,
  "speaking_sessions": 5,
  "lrg_time_sec": 9000
}
```

**Use Case:** Overview of all learning activities.

---

### 7.2 Get Unified Dashboard
**Endpoint:** `GET /api/v1/unified/dashboard`

**Description:** Comprehensive dashboard combining all activity types.

**Authentication:** Required

**Query Parameters:**
- `days`: Number of days to include (default: 7, max: 365)

**Response:** `200 OK`
```json
{
  "summary": {
    "total_activities": 45,
    "total_time_minutes": 300,
    "avg_score": 82
  },
  "by_activity": {
    "lrg": {...},
    "writing": {...},
    "speaking": {...}
  },
  "recent_activities": [...]
}
```

**Use Case:** Unified view of all learning activities.

---

### 7.3 Get Activity Timeline
**Endpoint:** `GET /api/v1/unified/timeline`

**Description:** Chronological timeline of all activities.

**Authentication:** Required

**Query Parameters:**
- `limit`: Items per page (default: 20, max: 100)
- `offset`: Pagination offset (default: 0)

**Response:** `200 OK`
```json
{
  "activities": [
    {
      "type": "lrg_session",
      "timestamp": "2025-01-15T10:35:00Z",
      "details": {...}
    }
  ],
  "limit": 20,
  "offset": 0,
  "total": 100
}
```

**Use Case:** Activity feed showing all learning events.

---

### 7.4 Get Comprehensive Progress
**Endpoint:** `GET /api/v1/unified/progress`

**Description:** Detailed progress report across all activities.

**Authentication:** Required

**Query Parameters:**
- `period`: weekly|monthly|all_time (default: weekly)

**Response:** `200 OK`
```json
{
  "period": "weekly",
  "total_activities": 15,
  "total_time_minutes": 120,
  "lrg_avg_accuracy": 85,
  "writing_avg_score": 80,
  "consistency_score": 75,
  "improvements": [...],
  "areas_for_focus": [...]
}
```

**Use Case:** Progress reports and performance analysis.

---

### 7.5 Get Week Comparison
**Endpoint:** `GET /api/v1/unified/comparison`

**Description:** Compare current week with previous week.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "current_week": {...},
  "previous_week": {...},
  "changes": {
    "total_activities": 5,
    "total_time_minutes": 30,
    "avg_score": 3.5
  }
}
```

**Use Case:** Show improvement trends week over week.

---

### 7.6 Get Achievements Summary
**Endpoint:** `GET /api/v1/unified/achievements`

**Description:** Summary of badges, streaks, XP, and milestones.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "badges": {
    "earned": 15,
    "recent": [...],
    "categories": {
      "streaks": 5,
      "performance": 7,
      "volume": 3
    }
  },
  "streaks": {
    "current": 7,
    "longest": 15,
    "at_risk": false
  },
  "xp": {
    "total": 1250,
    "rank": "Bronze",
    "next_rank_at": 2000
  },
  "milestones": {
    "total_activities": 50,
    "total_time_hours": 5
  }
}
```

**Use Case:** Gamification and achievement tracking.

---

### 7.7 Get Learning Insights
**Endpoint:** `GET /api/v1/unified/insights`

**Description:** AI-generated insights and recommendations.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "strengths": ["vocabulary", "reading comprehension"],
  "improvements": ["Practice more consistently"],
  "focus_areas": ["grammar", "listening"],
  "recommendations": [
    {
      "type": "consistency",
      "message": "Try to practice daily for better retention",
      "priority": "high"
    }
  ],
  "trends": {
    "consistency": {
      "score": 75,
      "trend": "stable"
    },
    "performance": {
      "lrg": 85,
      "writing": 80,
      "overall_trend": "improving"
    }
  }
}
```

**Use Case:** Personalized learning recommendations.

---

## 8. Meta Endpoints

### 8.1 List All Endpoints
**Endpoint:** `GET /api/v1/meta/endpoints`

**Description:** Returns a list of all available API endpoints.

**Authentication:** Not required

**Response:** `200 OK`
```json
{
  "count": 50,
  "routes": [
    {
      "path": "/api/v1/sessions",
      "methods": ["GET", "POST"],
      "name": "start_session",
      "summary": "Start a new test session",
      "tags": ["sessions"]
    }
  ]
}
```

**Use Case:** API discovery and documentation.

---

## Authentication

All endpoints (except meta endpoints) require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

The token contains the `user_id` which is automatically extracted and used for authorization checks.

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request format"
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
  "detail": "Cannot access another user's data"
}
```

### 404 Not Found
```json
{
  "detail": "Session not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error message"
}
```

---

## Configuration

Key settings from `app/core/config.py`:

- **Base XP per session:** 20
- **Accuracy bonus threshold:** 80%
- **Accuracy bonus XP:** 10
- **Default page size:** 10
- **Max page size:** 100
- **Timezone:** Asia/Kolkata

---

## Common Workflows

### Workflow 1: Complete a Learning Session
1. `POST /api/v1/sessions` - Start session
2. User completes questions
3. `POST /api/v1/sessions/{session_id}/submit` - Submit answers
4. Receive XP, badges, streak update
5. `GET /api/v1/sessions/{session_id}/mastery` - View skill breakdown

### Workflow 2: View Daily Progress
1. `GET /api/v1/dashboard/summary?window=7d` - Get dashboard
2. `GET /api/v1/users/{user_id}/daily-progress` - Get today's details
3. `GET /api/v1/users/{user_id}/streak` - Check streak status

### Workflow 3: Track Skill Improvement
1. `GET /api/v1/users/{user_id}/mastery-overview` - Overall mastery
2. `GET /api/v1/users/{user_id}/skills/progress?modality=listening` - Specific modality
3. `GET /api/v1/listening/users/{user_id}/analytics` - Detailed analytics

### Workflow 4: Review Achievements
1. `GET /api/v1/unified/achievements` - All achievements
2. `GET /api/v1/users/{user_id}/xp` - XP and level
3. `GET /api/v1/users/{user_id}/streak-calendar` - Activity calendar

---

## Notes

- All timestamps are in ISO 8601 format with timezone
- UUIDs are used for all IDs
- Pagination follows offset/limit pattern
- User authorization is enforced - users can only access their own data
- Content creation endpoints are admin-only (though authentication is commented out in current implementation)
- Audio files are stored in Supabase storage buckets

---

**Version:** 1.0
**Last Updated:** January 2025
**API Base URL:** `/api/v1`
