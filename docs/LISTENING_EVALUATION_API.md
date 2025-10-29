# Listening Evaluation API Documentation

## Overview

This document provides comprehensive documentation for the **Listening Evaluation System**. The API supports skill-based evaluation, audio tracking, time duration monitoring, and mastery level calculation for listening comprehension tasks across Day 1 to Day 90.

---

## Table of Contents

1. [Listening Session APIs](#listening-session-apis)
2. [Listening Mastery & Analytics APIs](#listening-mastery--analytics-apis)
3. [Data Models](#data-models)
4. [Listening Skills Taxonomy](#listening-skills-taxonomy)
5. [Listening-Specific Features](#listening-specific-features)
6. [Usage Examples](#usage-examples)
7. [Best Practices](#best-practices)

---

## Listening Session APIs

### 1. Start Listening Session

**Endpoint:** `POST /api/v1/listening/sessions`

**Description:** Creates a new listening test session for a specific day with optional audio URL.

**Request Body:**
```json
{
  "user_id": "uuid",
  "day_code": "day1",
  "audio_url": "https://example.com/audio/day1-listening.mp3",
  "started_at": "2025-10-06T10:00:00Z"
}
```

**Response:** `201 Created`
```json
{
  "session_id": "uuid",
  "user_id": "uuid",
  "modality": "listening",
  "day_code": "day1",
  "audio_url": "https://example.com/audio/day1-listening.mp3",
  "started_at": "2025-10-06T10:00:00Z",
  "message": "Listening session started successfully"
}
```

---

### 2. Submit Listening Session

**Endpoint:** `POST /api/v1/listening/sessions/{session_id}/submit`

**Description:** Submit completed listening session with all answers. Each answer includes listening-specific fields like question type, audio timestamps, and skill evaluation.

**Request Body:**
```json
{
  "answers": [
    {
      "item_id": "q1",
      "question_type": "multiple_choice",
      "user_answer": "B",
      "correct_answer": "B",
      "is_correct": true,
      "time_spent_sec": 45,
      "skill": "main_idea",
      "audio_timestamp_start": 0,
      "audio_timestamp_end": 30,
      "topic": "lecture_economics"
    },
    {
      "item_id": "q2",
      "question_type": "fill_blank",
      "user_answer": "economic growth",
      "correct_answer": "economic growth",
      "is_correct": true,
      "time_spent_sec": 60,
      "skill": "vocabulary",
      "audio_timestamp_start": 15,
      "audio_timestamp_end": 25,
      "topic": "lecture_economics"
    },
    {
      "item_id": "q3",
      "question_type": "true_false",
      "user_answer": "true",
      "correct_answer": "false",
      "is_correct": false,
      "time_spent_sec": 30,
      "skill": "details",
      "audio_timestamp_start": 50,
      "audio_timestamp_end": 75,
      "topic": "lecture_economics"
    }
  ],
  "completed_at": "2025-10-06T10:15:00Z",
  "duration_sec": 900,
  "score_pct": 67,
  "xp_earned": 80,
  "audio_replay_count": 2
}
```

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "analytics_recorded": true,
  "xp_awarded": 80,
  "badges_awarded": [
    {
      "badge_key": "listening_streak_5",
      "title": "5-Day Listening Streak",
      "earned_at": "2025-10-06T10:15:00Z"
    }
  ],
  "streak_updated": true,
  "current_streak": 5,
  "skill_mastery_recorded": true,
  "message": "Listening session submitted successfully"
}
```

---

### 3. Get Listening Session Details

**Endpoint:** `GET /api/v1/listening/sessions/{session_id}`

**Description:** Retrieve complete listening session information including all answers and metadata.

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "user_id": "uuid",
  "modality": "listening",
  "day_code": "day1",
  "audio_url": "https://example.com/audio/day1-listening.mp3",
  "started_at": "2025-10-06T10:00:00Z",
  "completed_at": "2025-10-06T10:15:00Z",
  "duration_sec": 900,
  "score_pct": 67,
  "xp_earned": 80,
  "audio_replay_count": 2,
  "answers": [
    {
      "answer_id": "uuid",
      "item_id": "q1",
      "question_type": "multiple_choice",
      "user_answer": "B",
      "correct_answer": "B",
      "is_correct": true,
      "time_spent_sec": 45,
      "skill": "main_idea",
      "audio_timestamp_start": 0,
      "audio_timestamp_end": 30,
      "topic": "lecture_economics"
    }
  ]
}
```

---

## Listening Mastery & Analytics APIs

### 4. Get Listening Session Mastery

**Endpoint:** `GET /api/v1/listening/sessions/{session_id}/mastery`

**Description:** Returns skill-by-skill mastery breakdown for a completed listening session.

**Response:** `200 OK`
```json
{
  "session_id": "uuid",
  "modality": "listening",
  "day_code": "day1",
  "overall_score_pct": 67,
  "duration_sec": 900,
  "audio_replay_count": 2,
  "skills": [
    {
      "skill": "main_idea",
      "correct": 8,
      "total": 10,
      "mastery_pct": 80,
      "mastery_level": "proficient"
    },
    {
      "skill": "vocabulary",
      "correct": 5,
      "total": 6,
      "mastery_pct": 83,
      "mastery_level": "proficient"
    },
    {
      "skill": "details",
      "correct": 3,
      "total": 5,
      "mastery_pct": 60,
      "mastery_level": "developing"
    },
    {
      "skill": "inference",
      "correct": 4,
      "total": 6,
      "mastery_pct": 67,
      "mastery_level": "developing"
    }
  ],
  "mastery_levels": {
    "beginner": 0,
    "developing": 2,
    "proficient": 2,
    "advanced": 0
  }
}
```

---

### 5. Get User Listening Progress

**Endpoint:** `GET /api/v1/listening/users/{user_id}/progress`

**Description:** Track user's listening skill development across sessions with detailed statistics.

**Query Parameters:**
- `from_day` (optional): Starting day code (e.g., `day1`)
- `to_day` (optional): Ending day code (e.g., `day10`)

**Example:** `GET /api/v1/listening/users/{user_id}/progress?from_day=day1&to_day=day10`

**Response:** `200 OK`
```json
{
  "modality": "listening",
  "date_range": "day1-day10",
  "overall_mastery_pct": 75,
  "total_sessions": 10,
  "total_audio_replay_count": 18,
  "skills": [
    {
      "skill": "vocabulary",
      "sessions_practiced": 10,
      "total_questions": 60,
      "correct_answers": 52,
      "overall_mastery_pct": 87,
      "mastery_level": "proficient",
      "trend": "improving",
      "avg_time_per_question": 42.5
    },
    {
      "skill": "main_idea",
      "sessions_practiced": 10,
      "total_questions": 80,
      "correct_answers": 64,
      "overall_mastery_pct": 80,
      "mastery_level": "proficient",
      "trend": "stable",
      "avg_time_per_question": 55.2
    },
    {
      "skill": "details",
      "sessions_practiced": 9,
      "total_questions": 45,
      "correct_answers": 30,
      "overall_mastery_pct": 67,
      "mastery_level": "developing",
      "trend": "improving",
      "avg_time_per_question": 38.7
    },
    {
      "skill": "inference",
      "sessions_practiced": 8,
      "total_questions": 40,
      "correct_answers": 32,
      "overall_mastery_pct": 80,
      "mastery_level": "proficient",
      "trend": "stable",
      "avg_time_per_question": 65.3
    },
    {
      "skill": "speaker_purpose",
      "sessions_practiced": 7,
      "total_questions": 28,
      "correct_answers": 19,
      "overall_mastery_pct": 68,
      "mastery_level": "developing",
      "trend": "improving",
      "avg_time_per_question": 48.1
    }
  ]
}
```

---

### 6. Get Listening Analytics

**Endpoint:** `GET /api/v1/listening/users/{user_id}/analytics`

**Description:** Comprehensive listening analytics including improvement rate and skill comparison.

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "total_sessions": 25,
  "avg_score_pct": 78.5,
  "total_duration_sec": 22500,
  "total_audio_replays": 45,
  "strongest_skill": "vocabulary",
  "weakest_skill": "speaker_purpose",
  "improvement_rate": 15.3
}
```

---

## Data Models

### ListeningAnswerSubmission

```json
{
  "item_id": "string",
  "question_type": "multiple_choice | fill_blank | true_false | short_answer | matching",
  "user_answer": "string | null",
  "correct_answer": "string",
  "is_correct": "boolean",
  "time_spent_sec": "integer (≥0)",
  "skill": "vocabulary | main_idea | details | inference | speaker_purpose | tone | organization | connecting_ideas",
  "audio_timestamp_start": "integer | null (seconds)",
  "audio_timestamp_end": "integer | null (seconds)",
  "topic": "string | null"
}
```

### Question Types

| Type | Description | Example |
|------|-------------|---------|
| `multiple_choice` | Select from options A-D | "What is the main idea?" |
| `fill_blank` | Complete missing word/phrase | "The economy grew by ___%" |
| `true_false` | Binary true/false question | "The speaker supports the policy. T/F" |
| `short_answer` | Brief written response | "Why did the speaker mention...?" |
| `matching` | Match items from two lists | "Match speakers to their views" |

---

## Listening Skills Taxonomy

### Core Listening Skills

| Skill | Description | Example Question |
|-------|-------------|------------------|
| **vocabulary** | Word recognition and meaning in audio context | "What does 'fluctuate' mean as used?" |
| **main_idea** | Understanding the central message or topic | "What is the lecture mainly about?" |
| **details** | Specific information recall from audio | "How many participants were in the study?" |
| **inference** | Drawing conclusions from what's heard | "What can be inferred about the speaker's opinion?" |
| **speaker_purpose** | Understanding why the speaker said something | "Why does the professor mention dolphins?" |
| **tone** | Recognizing attitude, emotion, or certainty | "What is the speaker's attitude toward...?" |
| **organization** | Understanding how ideas are structured | "How does the speaker organize the information?" |
| **connecting_ideas** | Linking related concepts across the audio | "How does this example relate to the main point?" |

---

## Listening-Specific Features

### 1. Audio Timestamp Tracking

Track which part of the audio each question relates to:

```json
{
  "audio_timestamp_start": 45,
  "audio_timestamp_end": 75
}
```

**Use Cases:**
- Review specific audio segments for incorrect answers
- Analyze which audio sections are most challenging
- Enable targeted practice for weak segments

---

### 2. Audio Replay Count

Track how many times users replay audio during the session:

```json
{
  "audio_replay_count": 2
}
```

**Insights:**
- High replay counts may indicate audio difficulty
- Track if replays correlate with better scores
- Identify users who may need slower-paced audio

---

### 3. Question Type Analysis

Each answer includes `question_type` for granular analysis:

```json
{
  "question_type": "multiple_choice"
}
```

**Benefits:**
- Identify which question formats are most challenging
- Balance question types in content creation
- Tailor practice based on weak question types

---

### 4. Time Per Question Analytics

The system automatically calculates average time spent per skill:

```json
{
  "skill": "inference",
  "avg_time_per_question": 65.3
}
```

**Insights:**
- Inference questions take longer on average
- Vocabulary questions are answered more quickly
- Track speed improvements over time

---

## Usage Examples

### Example 1: Complete Listening Session Flow (Day 3)

**Step 1: Start Session**
```bash
POST /api/v1/listening/sessions

{
  "user_id": "abc-123-def",
  "day_code": "day3",
  "audio_url": "https://cdn.example.com/listening/day3-conversation.mp3",
  "started_at": "2025-10-06T14:00:00Z"
}
```

**Response:**
```json
{
  "session_id": "xyz-789",
  "user_id": "abc-123-def",
  "modality": "listening",
  "day_code": "day3",
  "audio_url": "https://cdn.example.com/listening/day3-conversation.mp3",
  "started_at": "2025-10-06T14:00:00Z"
}
```

---

**Step 2: User Completes Questions, Submit Session**
```bash
POST /api/v1/listening/sessions/xyz-789/submit

{
  "answers": [
    {
      "item_id": "day3_q1",
      "question_type": "multiple_choice",
      "user_answer": "A",
      "correct_answer": "A",
      "is_correct": true,
      "time_spent_sec": 40,
      "skill": "main_idea",
      "audio_timestamp_start": 0,
      "audio_timestamp_end": 60,
      "topic": "campus_conversation"
    },
    {
      "item_id": "day3_q2",
      "question_type": "fill_blank",
      "user_answer": "library",
      "correct_answer": "library",
      "is_correct": true,
      "time_spent_sec": 35,
      "skill": "details",
      "audio_timestamp_start": 20,
      "audio_timestamp_end": 30,
      "topic": "campus_conversation"
    },
    {
      "item_id": "day3_q3",
      "question_type": "true_false",
      "user_answer": "true",
      "correct_answer": "false",
      "is_correct": false,
      "time_spent_sec": 25,
      "skill": "inference",
      "audio_timestamp_start": 45,
      "audio_timestamp_end": 60,
      "topic": "campus_conversation"
    }
  ],
  "completed_at": "2025-10-06T14:12:00Z",
  "duration_sec": 720,
  "score_pct": 67,
  "xp_earned": 75,
  "audio_replay_count": 1
}
```

---

**Step 3: Check Mastery Breakdown**
```bash
GET /api/v1/listening/sessions/xyz-789/mastery
```

**Response:**
```json
{
  "session_id": "xyz-789",
  "modality": "listening",
  "day_code": "day3",
  "overall_score_pct": 67,
  "duration_sec": 720,
  "audio_replay_count": 1,
  "skills": [
    {
      "skill": "main_idea",
      "correct": 1,
      "total": 1,
      "mastery_pct": 100,
      "mastery_level": "advanced"
    },
    {
      "skill": "details",
      "correct": 1,
      "total": 1,
      "mastery_pct": 100,
      "mastery_level": "advanced"
    },
    {
      "skill": "inference",
      "correct": 0,
      "total": 1,
      "mastery_pct": 0,
      "mastery_level": "beginner"
    }
  ],
  "mastery_levels": {
    "beginner": 1,
    "developing": 0,
    "proficient": 0,
    "advanced": 2
  }
}
```

---

### Example 2: Track Progress After 10 Days

**Request:**
```bash
GET /api/v1/listening/users/abc-123-def/progress?from_day=day1&to_day=day10
```

**Response:**
```json
{
  "modality": "listening",
  "date_range": "day1-day10",
  "overall_mastery_pct": 78,
  "total_sessions": 10,
  "total_audio_replay_count": 15,
  "skills": [
    {
      "skill": "vocabulary",
      "sessions_practiced": 10,
      "total_questions": 50,
      "correct_answers": 43,
      "overall_mastery_pct": 86,
      "mastery_level": "proficient",
      "trend": "improving",
      "avg_time_per_question": 38.2
    },
    {
      "skill": "inference",
      "sessions_practiced": 10,
      "total_questions": 40,
      "correct_answers": 28,
      "overall_mastery_pct": 70,
      "mastery_level": "developing",
      "trend": "stable",
      "avg_time_per_question": 62.5
    }
  ]
}
```

---

### Example 3: View Listening Analytics Dashboard

**Request:**
```bash
GET /api/v1/listening/users/abc-123-def/analytics
```

**Response:**
```json
{
  "user_id": "abc-123-def",
  "total_sessions": 30,
  "avg_score_pct": 82.3,
  "total_duration_sec": 27000,
  "total_audio_replays": 42,
  "strongest_skill": "vocabulary",
  "weakest_skill": "speaker_purpose",
  "improvement_rate": 18.7
}
```

**Insights:**
- User has improved 18.7% from first to latest session
- Vocabulary is strongest (likely 90%+ mastery)
- Speaker purpose needs work (likely <65% mastery)
- Average 42 audio replays across 30 sessions = 1.4 replays per session

---

## Best Practices

### Frontend Implementation

#### 1. Audio Player Integration
```javascript
// Track audio replays
let audioReplayCount = 0;

audioPlayer.addEventListener('ended', () => {
  if (userReplaysAudio) {
    audioReplayCount++;
  }
});
```

#### 2. Time Tracking Per Question
```javascript
// Start timer when question is displayed
const questionStartTime = Date.now();

// Calculate time spent when answer submitted
const timeSpent = Math.floor((Date.now() - questionStartTime) / 1000);

answerData.time_spent_sec = timeSpent;
```

#### 3. Audio Timestamp Association
```javascript
// Link question to specific audio segment
const questionData = {
  item_id: "q5",
  audio_timestamp_start: 120,  // 2:00 in audio
  audio_timestamp_end: 150     // 2:30 in audio
};

// Allow user to replay specific segment for review
function replayQuestionAudio(question) {
  audioPlayer.currentTime = question.audio_timestamp_start;
  audioPlayer.play();
}
```

---

### Content Creation Guidelines

#### 1. Question Distribution by Skill
Recommended distribution per session:
- **Vocabulary:** 20-25%
- **Main Idea:** 15-20%
- **Details:** 25-30%
- **Inference:** 15-20%
- **Speaker Purpose:** 10-15%
- **Other Skills:** 5-10%

#### 2. Question Type Variety
Mix question types for engagement:
- Multiple Choice: 40-50%
- Fill in the Blank: 20-25%
- True/False: 15-20%
- Short Answer: 10-15%

#### 3. Audio Length Guidelines
- **Day 1-30:** 2-3 minute audio clips
- **Day 31-60:** 3-5 minute audio clips
- **Day 61-90:** 5-7 minute audio clips

---

### Performance Optimization

1. **Lazy Load Audio:** Only load audio when session starts
2. **Cache Audio Files:** Use CDN with long cache times
3. **Batch Answer Submission:** Submit all answers at once
4. **Async Analytics:** Process skill mastery calculations asynchronously

---

## Error Handling

### Common Errors

**400 Bad Request** - Invalid question type:
```json
{
  "detail": "question_type must be one of: multiple_choice, fill_blank, true_false, short_answer, matching"
}
```

**404 Not Found** - Session doesn't exist:
```json
{
  "detail": "Listening session not found"
}
```

**403 Forbidden** - Unauthorized access:
```json
{
  "detail": "Cannot submit another user's session"
}
```

**422 Validation Error** - Missing skill field:
```json
{
  "detail": [
    {
      "loc": ["body", "answers", 0, "skill"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Integration Checklist

- [ ] Audio player with replay tracking implemented
- [ ] Time tracking per question active
- [ ] Audio timestamp association configured
- [ ] All 8 listening skills mapped to content
- [ ] Question types properly categorized
- [ ] Audio URLs configured and tested
- [ ] Progress dashboard displays listening-specific data
- [ ] Audio replay analytics visible to instructors
- [ ] Review functionality allows segment replay

---

## Database Schema

The listening system uses the same core tables with modality-specific data:

### Listening Sessions
Stored in `lrg_sessions` with `modality = 'listening'`

### Listening Answers
Stored in `lrg_answers` with listening-specific fields:
- `skill`: One of 8 listening skills
- `time_spent_sec`: Duration per question
- `topic`: Audio passage identifier

### Listening Skill Mastery
Stored in `lrg_skill_mastery` with `modality = 'listening'`

---

## Support & Feedback

For API questions or feature requests:
- **API Documentation:** `/docs` (Swagger UI)
- **ReDoc:** `/redoc`
- **Code:** Check `app/services/listening_service.py` and `app/api/v1/listening.py`

---

**Version:** 1.0
**Last Updated:** 2025-10-06
**Maintained By:** LRG Development Team
