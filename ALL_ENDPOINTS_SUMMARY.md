# Complete API Endpoints Summary

Quick reference for all Writing and Speaking evaluation endpoints.

---

## Endpoints Overview

| Category | Endpoint | Method | Purpose |
|----------|----------|--------|---------|
| **Writing** | `/writing/evaluate` | POST | AI-powered writing evaluation |
| | `/writing/evaluation/save` | POST | Save full evaluation (AI-generated) |
| | `/writing/evaluation/self-save` | POST | Save self-evaluation |
| | `/writing/progress` | GET | Get individual evaluations + trend |
| | `/writing/competencies` | GET | Get daily competency averages |
| | `/writing/improve` | POST | Get improved version of text |
| | `/writing/tips` | GET | Get writing tips |
| **Speaking** | `/speaking/evaluate` | POST | AI-powered speaking evaluation |
| | `/speaking/evaluation/save` | POST | Save full evaluation (AI-generated) |
| | `/speaking/evaluation/self-save` | POST | Save self-evaluation |
| | `/speaking/progress` | GET | Get individual evaluations + trend |
| | `/speaking/competencies` | GET | Get daily competency averages |
| | `/speaking/tips` | GET | Get speaking tips |
| | `/speaking/evaluation/{session_id}` | GET | Get specific evaluation |
| | `/speaking/evaluations/user/{user_id}` | GET | Get all user evaluations |
| | `/speaking/evaluation/{evaluation_id}` | DELETE | Delete an evaluation |

---

## Quick Command Reference

### Writing Endpoints

#### 1. Self-Evaluation (Create Data)
```bash
curl -X POST "http://localhost:8000/writing/evaluation/self-save" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "scores": {
      "grammar": 85, "vocabulary": 80, "coherence": 90,
      "style": 75, "clarity": 88, "engagement": 82
    },
    "user_level": "intermediate"
  }'
```

#### 2. Progress (Individual Evaluations)
```bash
curl "http://localhost:8000/writing/progress?user_id=550e8400-e29b-41d4-a716-446655440000&days=30"
```

**Returns:**
```json
{
  "evaluations": [
    {"date": "2025-10-15", "overall_score": 83, "scores": {...}},
    {"date": "2025-10-16", "overall_score": 87, "scores": {...}}
  ],
  "trend": {
    "start_score": 64,
    "end_score": 89,
    "change": 25,
    "direction": "improving"
  }
}
```

#### 3. Competencies (Daily Averages)
```bash
curl "http://localhost:8000/writing/competencies?user_id=550e8400-e29b-41d4-a716-446655440000&days=30"
```

**Returns:**
```json
{
  "daily_competencies": [
    {
      "date": "2025-10-15",
      "overall_score": 85,
      "grammar": 87,
      "vocabulary": 84,
      "coherence": 88,
      "style": 82,
      "clarity": 86,
      "engagement": 83,
      "evaluation_count": 2
    }
  ],
  "average_scores": {
    "overall_score": 83.0,
    "grammar": 85.0,
    "vocabulary": 80.0,
    ...
  }
}
```

---

### Speaking Endpoints

#### 1. Self-Evaluation (Create Data)
```bash
curl -X POST "http://localhost:8000/speaking/evaluation/self-save" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "660e8400-e29b-41d4-a716-446655440001",
    "scores": {
      "fluency": 78, "pronunciation": 82, "vocabulary": 75,
      "grammar": 80, "focus": 85, "understanding": 88
    },
    "user_level": "intermediate"
  }'
```

#### 2. Progress (Individual Evaluations)
```bash
curl "http://localhost:8000/speaking/progress?user_id=550e8400-e29b-41d4-a716-446655440000&days=30"
```

**Returns:**
```json
{
  "evaluations": [
    {
      "date": "2025-10-15",
      "overall_score": 81,
      "scores": {...},
      "total_turns": 12
    }
  ],
  "trend": {
    "start_score": 61,
    "end_score": 91,
    "change": 30,
    "direction": "improving"
  }
}
```

#### 3. Competencies (Daily Averages)
```bash
curl "http://localhost:8000/speaking/competencies?user_id=550e8400-e29b-41d4-a716-446655440000&days=30"
```

**Returns:**
```json
{
  "daily_competencies": [
    {
      "date": "2025-10-15",
      "overall_score": 82,
      "fluency": 80,
      "pronunciation": 83,
      "vocabulary": 79,
      "grammar": 81,
      "focus": 84,
      "understanding": 86,
      "evaluation_count": 3
    }
  ],
  "average_scores": {
    "overall_score": 81.0,
    "fluency": 78.0,
    ...
  }
}
```

---

## Comparison: Progress vs Competencies

### When to Use Progress Endpoints

**Use `/writing/progress` or `/speaking/progress` when you need:**
- ✅ Individual evaluation history
- ✅ Trend analysis (improving/declining/stable)
- ✅ Timeline/chronological view
- ✅ See all evaluations separately
- ✅ Track exact scores over time

**Example Use Cases:**
- Progress timeline widget
- "Your Journey" section
- Detailed history view
- Trend indicators
- Achievement tracking

### When to Use Competencies Endpoints

**Use `/writing/competencies` or `/speaking/competencies` when you need:**
- ✅ Daily summary/averages
- ✅ Competency-focused analysis
- ✅ Identify weak areas
- ✅ High-level overview
- ✅ Chart/graph data

**Example Use Cases:**
- Competency radar charts
- Daily performance summaries
- Strength/weakness analysis
- Progress charts
- Weekly/monthly reports

---

## Response Structure Comparison

### Progress Endpoint Response

```json
{
  "user_id": "uuid",
  "days": 30,
  "start_date": "2025-09-18",
  "end_date": "2025-10-18",
  "evaluations": [
    // Individual evaluations (no averaging)
    {
      "date": "2025-10-15",
      "overall_score": 80,
      "scores": {/* all competencies */}
    },
    {
      "date": "2025-10-15",  // Same day, different evaluation
      "overall_score": 90,
      "scores": {/* all competencies */}
    }
  ],
  "trend": {
    "start_score": 64,
    "end_score": 89,
    "change": 25,
    "direction": "improving"
  }
}
```

### Competencies Endpoint Response

```json
{
  "user_id": "uuid",
  "days": 30,
  "start_date": "2025-09-18",
  "end_date": "2025-10-18",
  "daily_competencies": [
    // Daily averages
    {
      "date": "2025-10-15",
      "overall_score": 85,  // Average of 80 and 90
      "grammar": 87,
      "vocabulary": 84,
      ...
      "evaluation_count": 2  // Shows how many evaluations were averaged
    }
  ],
  "average_scores": {
    // Overall averages across all days
    "overall_score": 83.0,
    "grammar": 85.0,
    "vocabulary": 80.0,
    ...
  }
}
```

---

## Complete Workflow Example

### Step 1: Create Self-Evaluations

```bash
# Day 1
curl -X POST "http://localhost:8000/writing/evaluation/self-save" \
  -d '{"user_id": "USER_ID", "scores": {...}}'

# Day 2
curl -X POST "http://localhost:8000/writing/evaluation/self-save" \
  -d '{"user_id": "USER_ID", "scores": {...}}'

# Day 3
curl -X POST "http://localhost:8000/writing/evaluation/self-save" \
  -d '{"user_id": "USER_ID", "scores": {...}}'
```

### Step 2: View Progress (Individual Evaluations)

```bash
curl "http://localhost:8000/writing/progress?user_id=USER_ID&days=7"
```

**Use this to:**
- See all 3 evaluations separately
- Track improvement trend
- Display timeline

### Step 3: View Competencies (Daily Averages)

```bash
curl "http://localhost:8000/writing/competencies?user_id=USER_ID&days=7"
```

**Use this to:**
- See daily summaries
- Identify weak competencies
- Create competency charts

---

## Frontend Integration Examples

### Dashboard with Both Endpoints

```jsx
import React, { useEffect, useState } from 'react';

function UserDashboard({ userId }) {
  const [progress, setProgress] = useState(null);
  const [competencies, setCompetencies] = useState(null);

  useEffect(() => {
    // Fetch both in parallel
    Promise.all([
      fetch(`/writing/progress?user_id=${userId}&days=30`).then(r => r.json()),
      fetch(`/writing/competencies?user_id=${userId}&days=30`).then(r => r.json())
    ]).then(([prog, comp]) => {
      setProgress(prog);
      setCompetencies(comp);
    });
  }, [userId]);

  if (!progress || !competencies) return <div>Loading...</div>;

  return (
    <div className="dashboard">
      {/* Trend Card - from Progress */}
      <div className="trend-card">
        <h3>Your Progress</h3>
        <div className={`trend ${progress.trend.direction}`}>
          <span className="icon">
            {progress.trend.direction === 'improving' ? '📈' :
             progress.trend.direction === 'declining' ? '📉' : '➡️'}
          </span>
          <span className="direction">{progress.trend.direction}</span>
          <span className="change">
            {progress.trend.change > 0 ? '+' : ''}{progress.trend.change} points
          </span>
        </div>
        <div className="scores">
          <span>{progress.trend.start_score}</span>
          <span>→</span>
          <span>{progress.trend.end_score}</span>
        </div>
      </div>

      {/* Competency Strengths/Weaknesses - from Competencies */}
      <div className="competencies-card">
        <h3>Your Strengths & Weaknesses</h3>
        {Object.entries(competencies.average_scores)
          .filter(([key]) => key !== 'overall_score')
          .sort(([, a], [, b]) => b - a)
          .map(([competency, score]) => (
            <div key={competency} className="competency-bar">
              <span>{competency}</span>
              <div className="bar">
                <div
                  className="fill"
                  style={{ width: `${score}%` }}
                />
              </div>
              <span>{score.toFixed(1)}</span>
            </div>
          ))}
      </div>

      {/* Timeline - from Progress */}
      <div className="timeline-card">
        <h3>Recent Activity</h3>
        <div className="timeline">
          {progress.evaluations.map((eval, idx) => (
            <div key={idx} className="timeline-item">
              <span className="date">{eval.date}</span>
              <span className="score">{eval.overall_score}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Charts - from Competencies */}
      <div className="charts-card">
        <h3>Daily Performance</h3>
        <LineChart data={competencies.daily_competencies}>
          {/* Chart implementation */}
        </LineChart>
      </div>
    </div>
  );
}
```

---

## Testing Checklist

### Writing Endpoints
- [ ] Create writing self-evaluation
- [ ] Fetch writing progress (individual evaluations)
- [ ] Fetch writing competencies (daily averages)
- [ ] Verify trend calculation
- [ ] Verify average scores calculation

### Speaking Endpoints
- [ ] Create speaking self-evaluation
- [ ] Fetch speaking progress (individual evaluations)
- [ ] Fetch speaking competencies (daily averages)
- [ ] Verify trend calculation
- [ ] Verify average scores calculation

### Edge Cases
- [ ] Empty user (no evaluations)
- [ ] Single evaluation
- [ ] Multiple evaluations same day
- [ ] Large date ranges (365 days)
- [ ] Invalid user_id
- [ ] Invalid days parameter

---

## Documentation Reference

| Document | Description |
|----------|-------------|
| [SELF_EVALUATION_ENDPOINTS.md](SELF_EVALUATION_ENDPOINTS.md) | Self-evaluation endpoints (create data) |
| [PROGRESS_ENDPOINTS_GUIDE.md](PROGRESS_ENDPOINTS_GUIDE.md) | Progress endpoints (individual evaluations) |
| [COMPETENCIES_TESTING_GUIDE.md](COMPETENCIES_TESTING_GUIDE.md) | Competencies endpoints (daily averages) |
| [COMPETENCIES_QUICK_REFERENCE.md](COMPETENCIES_QUICK_REFERENCE.md) | Quick reference for competencies |
| [COMPETENCIES_EXAMPLE_USAGE.md](COMPETENCIES_EXAMPLE_USAGE.md) | Real-world examples |
| [OVERALL_SCORE_UPDATE.md](OVERALL_SCORE_UPDATE.md) | Overall score field addition |
| [ALL_ENDPOINTS_SUMMARY.md](ALL_ENDPOINTS_SUMMARY.md) | This file |

---

## Quick Start

### 1. Create Test Data
```bash
# Writing
curl -X POST "http://localhost:8000/writing/evaluation/self-save" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "550e8400-e29b-41d4-a716-446655440000", "scores": {"grammar": 85, "vocabulary": 80, "coherence": 90, "style": 75, "clarity": 88, "engagement": 82}, "user_level": "intermediate"}'

# Speaking
curl -X POST "http://localhost:8000/speaking/evaluation/self-save" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "550e8400-e29b-41d4-a716-446655440000", "session_id": "660e8400-e29b-41d4-a716-446655440001", "scores": {"fluency": 78, "pronunciation": 82, "vocabulary": 75, "grammar": 80, "focus": 85, "understanding": 88}, "user_level": "intermediate"}'
```

### 2. View Progress
```bash
# Writing
curl "http://localhost:8000/writing/progress?user_id=550e8400-e29b-41d4-a716-446655440000&days=7"

# Speaking
curl "http://localhost:8000/speaking/progress?user_id=550e8400-e29b-41d4-a716-446655440000&days=7"
```

### 3. View Competencies
```bash
# Writing
curl "http://localhost:8000/writing/competencies?user_id=550e8400-e29b-41d4-a716-446655440000&days=7"

# Speaking
curl "http://localhost:8000/speaking/competencies?user_id=550e8400-e29b-41d4-a716-446655440000&days=7"
```

---

## Summary

You now have **3 main endpoint types** for tracking user progress:

1. **Self-Evaluation** (`POST /evaluation/self-save`)
   - Create new evaluations with user-provided scores

2. **Progress** (`GET /progress`)
   - View individual evaluations over time
   - Includes trend analysis
   - Best for timelines and detailed history

3. **Competencies** (`GET /competencies`)
   - View daily competency averages
   - Includes overall averages
   - Best for charts and competency analysis

Use them together for a comprehensive user progress tracking system! 🚀
