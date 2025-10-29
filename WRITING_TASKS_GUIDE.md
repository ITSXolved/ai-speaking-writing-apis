# Writing Tasks Endpoints - Complete Guide

This guide covers the **Daily Writing Tasks** endpoints that allow users to get writing questions/prompts for the day and submit their responses for evaluation.

---

## Table of Contents

1. [Overview](#overview)
2. [Get Daily Writing Tasks](#get-daily-writing-tasks)
3. [Submit Writing Task for Evaluation](#submit-writing-task-for-evaluation)
4. [Complete Workflow Example](#complete-workflow-example)
5. [Testing Guide](#testing-guide)

---

## Overview

The Writing Tasks system provides:
- ✅ **Daily writing prompts** - Get curated writing tasks for any day
- ✅ **Multiple difficulty levels** - Beginner, Intermediate, Advanced
- ✅ **Various writing types** - Essays, emails, stories, reviews, letters
- ✅ **Automatic evaluation** - Submit responses and get AI-powered feedback
- ✅ **Progress tracking** - All evaluations are saved for progress monitoring

### Key Features
- Consistent tasks for each day (same date = same tasks)
- Filterable by difficulty level and writing type
- Word count and time limit guidance
- Detailed evaluation with scores and improvements

---

## Get Daily Writing Tasks

### Endpoint
`GET /writing/tasks/daily`

### Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `date` | string | No | Date in YYYY-MM-DD format (defaults to today) | `2025-10-18` |
| `difficulty_level` | string | No | Filter: `beginner`, `intermediate`, `advanced` | `intermediate` |
| `writing_type` | string | No | Filter: `essay`, `email`, `story`, `review`, `letter` | `essay` |
| `limit` | integer | No | Number of tasks (1-20, default: 5) | `3` |

### Response Schema

```json
{
  "date": "string (YYYY-MM-DD)",
  "tasks": [
    {
      "task_id": "string",
      "title": "string",
      "description": "string",
      "writing_type": "string",
      "difficulty_level": "string",
      "word_count_min": "integer",
      "word_count_max": "integer",
      "time_limit_minutes": "integer",
      "tags": ["string"]
    }
  ],
  "total_count": "integer"
}
```

### Example Request

```bash
# Get today's tasks
curl "http://localhost:8000/writing/tasks/daily"

# Get tasks for a specific date
curl "http://localhost:8000/writing/tasks/daily?date=2025-10-18"

# Get only intermediate level tasks
curl "http://localhost:8000/writing/tasks/daily?difficulty_level=intermediate"

# Get only essay tasks
curl "http://localhost:8000/writing/tasks/daily?writing_type=essay"

# Get 3 advanced essay tasks
curl "http://localhost:8000/writing/tasks/daily?difficulty_level=advanced&writing_type=essay&limit=3"
```

### Example Response

```json
{
  "date": "2025-10-18",
  "tasks": [
    {
      "task_id": "2025-10-18-task-1",
      "title": "Formal Email to a Professor",
      "description": "Write a formal email to your professor requesting an extension for an assignment. Explain your situation professionally and provide valid reasons.",
      "writing_type": "email",
      "difficulty_level": "intermediate",
      "word_count_min": 100,
      "word_count_max": 200,
      "time_limit_minutes": 15,
      "tags": ["formal", "professional", "request"]
    },
    {
      "task_id": "2025-10-18-task-2",
      "title": "Creative Story Opening",
      "description": "Write the opening paragraph of a short story. Create an engaging hook that introduces a character and setting while building intrigue.",
      "writing_type": "story",
      "difficulty_level": "intermediate",
      "word_count_min": 100,
      "word_count_max": 250,
      "time_limit_minutes": 15,
      "tags": ["creative", "narrative", "fiction"]
    },
    {
      "task_id": "2025-10-18-task-3",
      "title": "Complaint Letter to Service Provider",
      "description": "Write a complaint letter to a service provider about a recent negative experience. Be firm but professional in expressing your concerns.",
      "writing_type": "letter",
      "difficulty_level": "intermediate",
      "word_count_min": 150,
      "word_count_max": 300,
      "time_limit_minutes": 20,
      "tags": ["formal", "complaint", "professional"]
    }
  ],
  "total_count": 3
}
```

---

## Submit Writing Task for Evaluation

### Endpoint
`POST /writing/tasks/submit`

### Request Body

```json
{
  "task_id": "string (required)",
  "user_id": "string (required - UUID)",
  "text": "string (required - 10-5000 characters)",
  "language": "string (optional, default: english)",
  "user_level": "string (optional, default: intermediate)",
  "save_evaluation": "boolean (optional, default: true)"
}
```

### Response Schema

```json
{
  "task_id": "string",
  "evaluation_id": "string",
  "overall_score": "integer (0-100)",
  "scores": {
    "grammar": "integer (0-100)",
    "vocabulary": "integer (0-100)",
    "coherence": "integer (0-100)",
    "style": "integer (0-100)",
    "clarity": "integer (0-100)",
    "engagement": "integer (0-100)"
  },
  "improved_version": "string (HTML)",
  "feedback_summary": "string",
  "strengths": ["string"],
  "improvements": ["string"],
  "word_count": "integer",
  "meets_requirements": "boolean"
}
```

### Example Request

```bash
curl -X POST "http://localhost:8000/writing/tasks/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "2025-10-18-task-1",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "text": "Dear Professor Smith,\n\nI am writing to request a brief extension on the research paper due next Friday. Due to an unexpected family emergency that required me to travel home last week, I fell behind on my research timeline. I have completed the majority of the work and would like to request an additional three days to ensure the final product meets the high standards expected in your class. I apologize for any inconvenience this may cause and appreciate your understanding.\n\nBest regards,\nJohn Doe",
    "language": "english",
    "user_level": "intermediate",
    "save_evaluation": true
  }'
```

### Example Response

```json
{
  "task_id": "2025-10-18-task-1",
  "evaluation_id": "abc123-def456-ghi789",
  "overall_score": 87,
  "scores": {
    "grammar": 92,
    "vocabulary": 85,
    "coherence": 90,
    "style": 88,
    "clarity": 89,
    "engagement": 80
  },
  "improved_version": "<p>Dear Professor Smith,</p><p>I am writing to request a brief extension...</p>",
  "feedback_summary": "Excellent formal email structure with professional tone. Your explanation is clear and concise. Minor improvements could be made in transitional phrases.",
  "strengths": [
    "Professional and respectful tone",
    "Clear explanation of circumstances",
    "Appropriate email format and structure"
  ],
  "improvements": [
    "Consider adding specific dates for clarity",
    "Could mention what has been completed in more detail",
    "Strengthen the closing with specific next steps"
  ],
  "word_count": 98,
  "meets_requirements": true
}
```

---

## Complete Workflow Example

### Step 1: Get Today's Writing Tasks

```bash
# Get tasks for today
curl "http://localhost:8000/writing/tasks/daily?limit=5"
```

**Response:**
```json
{
  "date": "2025-10-18",
  "tasks": [
    {
      "task_id": "2025-10-18-task-1",
      "title": "Describe Your Ideal Vacation",
      "description": "Write a descriptive essay...",
      "difficulty_level": "beginner",
      "word_count_min": 150,
      "word_count_max": 300
    },
    // ... more tasks
  ]
}
```

### Step 2: Choose a Task and Write Response

User writes their response to task "2025-10-18-task-1"

### Step 3: Submit for Evaluation

```bash
curl -X POST "http://localhost:8000/writing/tasks/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "2025-10-18-task-1",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "text": "My ideal vacation would be...",
    "user_level": "beginner"
  }'
```

### Step 4: Receive Evaluation

```json
{
  "task_id": "2025-10-18-task-1",
  "evaluation_id": "xyz789",
  "overall_score": 78,
  "scores": {...},
  "feedback_summary": "Good descriptive writing!",
  "strengths": ["Vivid imagery", "Clear structure"],
  "improvements": ["Add more sensory details", "Vary sentence structure"]
}
```

### Step 5: View Progress Over Time

```bash
# See all evaluations
curl "http://localhost:8000/writing/progress?user_id=550e8400-e29b-41d4-a716-446655440000&days=30"
```

---

## Testing Guide

### Quick Test - Complete Flow

#### 1. Get Today's Tasks
```bash
curl "http://localhost:8000/writing/tasks/daily"
```

#### 2. Submit a Response
```bash
curl -X POST "http://localhost:8000/writing/tasks/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "2025-10-18-task-1",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "text": "This is my writing response for the task. It contains several sentences to demonstrate my writing ability. I am practicing my English writing skills through this exercise. I hope to improve my grammar and vocabulary.",
    "language": "english",
    "user_level": "intermediate"
  }'
```

#### 3. Check Progress
```bash
curl "http://localhost:8000/writing/progress?user_id=550e8400-e29b-41d4-a716-446655440000&days=7"
```

### Python Example

```python
import requests

BASE_URL = "http://localhost:8000"
USER_ID = "550e8400-e29b-41d4-a716-446655440000"

# Step 1: Get today's tasks
response = requests.get(f"{BASE_URL}/writing/tasks/daily", params={"limit": 3})
tasks_data = response.json()

print(f"Today's date: {tasks_data['date']}")
print(f"Available tasks: {tasks_data['total_count']}")

# Display tasks
for task in tasks_data['tasks']:
    print(f"\nTask: {task['title']}")
    print(f"  Type: {task['writing_type']}")
    print(f"  Level: {task['difficulty_level']}")
    print(f"  Word count: {task['word_count_min']}-{task['word_count_max']}")
    print(f"  Time limit: {task['time_limit_minutes']} minutes")
    print(f"  Description: {task['description']}")

# Step 2: Submit a task (using first task)
task_id = tasks_data['tasks'][0]['task_id']

submission = {
    "task_id": task_id,
    "user_id": USER_ID,
    "text": """
    My ideal vacation would be to the beautiful island of Bali, Indonesia.
    This tropical paradise offers stunning beaches with crystal clear water,
    ancient temples rich in culture and history, and lush green rice terraces
    that cascade down the hillsides. I would spend my days surfing in the
    morning, exploring local markets in the afternoon, and watching breathtaking
    sunsets from cliff-top restaurants in the evening. The combination of
    natural beauty, rich culture, and warm hospitality makes Bali my dream
    vacation destination.
    """,
    "language": "english",
    "user_level": "beginner"
}

response = requests.post(f"{BASE_URL}/writing/tasks/submit", json=submission)
evaluation = response.json()

print(f"\n=== Evaluation Results ===")
print(f"Overall Score: {evaluation['overall_score']}/100")
print(f"Word Count: {evaluation['word_count']}")
print(f"Meets Requirements: {evaluation['meets_requirements']}")
print(f"\nScores:")
for category, score in evaluation['scores'].items():
    print(f"  {category.capitalize()}: {score}")

print(f"\nStrengths:")
for strength in evaluation['strengths']:
    print(f"  ✓ {strength}")

print(f"\nImprovements:")
for improvement in evaluation['improvements']:
    print(f"  → {improvement}")

print(f"\nFeedback: {evaluation['feedback_summary']}")
```

### JavaScript/TypeScript Example

```typescript
const BASE_URL = 'http://localhost:8000';
const USER_ID = '550e8400-e29b-41d4-a716-446655440000';

// Get today's writing tasks
async function getDailyTasks() {
  const response = await fetch(`${BASE_URL}/writing/tasks/daily?limit=5`);
  const data = await response.json();
  return data;
}

// Submit a writing task
async function submitTask(taskId: string, text: string) {
  const response = await fetch(`${BASE_URL}/writing/tasks/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      task_id: taskId,
      user_id: USER_ID,
      text: text,
      language: 'english',
      user_level: 'intermediate',
      save_evaluation: true
    })
  });
  return await response.json();
}

// Usage
const tasks = await getDailyTasks();
console.log(`Tasks for ${tasks.date}:`, tasks.tasks);

// User completes a task
const selectedTask = tasks.tasks[0];
const userResponse = "My written response here...";

// Submit for evaluation
const evaluation = await submitTask(selectedTask.task_id, userResponse);
console.log('Evaluation:', evaluation);
console.log(`Score: ${evaluation.overall_score}/100`);
```

### React Component Example

```jsx
import React, { useState, useEffect } from 'react';

function WritingTasksApp() {
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [userText, setUserText] = useState('');
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);

  const userId = '550e8400-e29b-41d4-a716-446655440000';

  // Load daily tasks
  useEffect(() => {
    async function loadTasks() {
      const response = await fetch('/writing/tasks/daily?limit=5');
      const data = await response.json();
      setTasks(data.tasks);
    }
    loadTasks();
  }, []);

  // Submit task
  async function handleSubmit() {
    setLoading(true);
    try {
      const response = await fetch('/writing/tasks/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: selectedTask.task_id,
          user_id: userId,
          text: userText,
          language: 'english',
          user_level: 'intermediate'
        })
      });
      const result = await response.json();
      setEvaluation(result);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="writing-tasks-app">
      <h1>Daily Writing Tasks</h1>

      {/* Task List */}
      <div className="tasks-list">
        {tasks.map(task => (
          <div
            key={task.task_id}
            className="task-card"
            onClick={() => setSelectedTask(task)}
          >
            <h3>{task.title}</h3>
            <p>{task.description}</p>
            <div className="task-meta">
              <span className="badge">{task.difficulty_level}</span>
              <span className="badge">{task.writing_type}</span>
              <span>{task.word_count_min}-{task.word_count_max} words</span>
              <span>{task.time_limit_minutes} min</span>
            </div>
          </div>
        ))}
      </div>

      {/* Writing Area */}
      {selectedTask && !evaluation && (
        <div className="writing-area">
          <h2>{selectedTask.title}</h2>
          <p>{selectedTask.description}</p>
          <textarea
            value={userText}
            onChange={(e) => setUserText(e.target.value)}
            placeholder="Write your response here..."
            rows={15}
          />
          <div className="word-count">
            Words: {userText.split(/\s+/).filter(w => w).length}
            / {selectedTask.word_count_min}-{selectedTask.word_count_max}
          </div>
          <button onClick={handleSubmit} disabled={loading}>
            {loading ? 'Evaluating...' : 'Submit for Evaluation'}
          </button>
        </div>
      )}

      {/* Evaluation Results */}
      {evaluation && (
        <div className="evaluation-results">
          <h2>Evaluation Results</h2>

          <div className="overall-score">
            <h3>Overall Score: {evaluation.overall_score}/100</h3>
            <div className="score-bar">
              <div
                className="score-fill"
                style={{width: `${evaluation.overall_score}%`}}
              />
            </div>
          </div>

          <div className="detailed-scores">
            <h4>Detailed Scores</h4>
            {Object.entries(evaluation.scores).map(([category, score]) => (
              <div key={category} className="score-row">
                <span>{category}</span>
                <span>{score}/100</span>
              </div>
            ))}
          </div>

          <div className="feedback">
            <h4>Strengths</h4>
            <ul>
              {evaluation.strengths.map((s, i) => (
                <li key={i} className="strength">✓ {s}</li>
              ))}
            </ul>

            <h4>Areas for Improvement</h4>
            <ul>
              {evaluation.improvements.map((imp, i) => (
                <li key={i} className="improvement">→ {imp}</li>
              ))}
            </ul>

            <h4>Summary</h4>
            <p>{evaluation.feedback_summary}</p>
          </div>

          <button onClick={() => {
            setSelectedTask(null);
            setUserText('');
            setEvaluation(null);
          }}>
            Try Another Task
          </button>
        </div>
      )}
    </div>
  );
}

export default WritingTasksApp;
```

---

## Available Writing Tasks

The system includes 8 different writing task templates across various types and difficulty levels:

### Beginner Level
1. **Describe Your Ideal Vacation** (Essay, 150-300 words)
2. **Product Review** (Review, 150-300 words)

### Intermediate Level
3. **Formal Email to a Professor** (Email, 100-200 words)
4. **Creative Story Opening** (Story, 100-250 words)
5. **Complaint Letter to Service Provider** (Letter, 150-300 words)

### Advanced Level
6. **Climate Change Opinion Essay** (Essay, 300-500 words)
7. **Job Application Cover Letter** (Letter, 250-400 words)
8. **Technology Impact Analysis** (Essay, 300-500 words)

Tasks are randomly selected based on the date, ensuring consistency (same date = same tasks) but variety across different days.

---

## API Summary

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/writing/tasks/daily` | GET | Get daily writing tasks/questions |
| `/writing/tasks/submit` | POST | Submit task response for evaluation |

### Key Features

- ✅ Consistent daily tasks (date-based seed)
- ✅ Filterable by level and type
- ✅ Automatic AI evaluation
- ✅ Detailed feedback with scores
- ✅ Progress tracking (saved to database)
- ✅ Word count validation
- ✅ Requirement checking

---

## Error Handling

### Invalid Date Format
```json
{
  "detail": "Invalid date format. Use YYYY-MM-DD"
}
```
Status: `400 Bad Request`

### Invalid User ID
```json
{
  "detail": "user_id must be a valid UUID string"
}
```
Status: `422 Unprocessable Entity`

### Text Too Short/Long
```json
{
  "detail": [
    {
      "loc": ["body", "text"],
      "msg": "ensure this value has at least 10 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```
Status: `422 Unprocessable Entity`

---

## Best Practices

### For Users
1. **Choose appropriate difficulty level** - Start with beginner, progress to advanced
2. **Follow word count guidelines** - Aim for recommended range
3. **Use time limits as guides** - Practice time management
4. **Review feedback carefully** - Learn from strengths and improvements
5. **Track progress regularly** - Use progress endpoints to monitor improvement

### For Developers
1. **Validate inputs** - Always validate user_id, task_id, and text length
2. **Handle errors gracefully** - Provide clear error messages
3. **Save evaluations** - Enable progress tracking by default
4. **Show word count** - Help users meet requirements
5. **Display feedback clearly** - Make strengths and improvements prominent

---

## Related Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/writing/progress` | View all writing evaluations over time |
| `/writing/competencies` | View daily competency averages |
| `/writing/evaluation/self-save` | Save self-evaluation scores |

---

## Conclusion

The Writing Tasks endpoints provide a complete system for daily writing practice:

1. **Get Tasks** - Fetch curated writing prompts
2. **Complete Tasks** - Write responses
3. **Get Evaluated** - Receive AI-powered feedback
4. **Track Progress** - Monitor improvement over time

Perfect for building a daily writing practice application! 🚀
