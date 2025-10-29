# User ID Handling in Competency Tracking

## Important: Different User ID Types

### The Issue

The `speaking_evaluations` and `writing_evaluations` tables use **different user_id types**:

- **`speaking_evaluations.user_id`** → UUID (references `auth.users.id`)
- **`writing_evaluations.user_id`** → TEXT (legacy format)

This means you need to handle them differently depending on your use case.

---

## Scenarios

### Scenario 1: Same User for Both Speaking and Writing (UUID)

If you want to track the same user across both speaking and writing evaluations:

**Best Practice:** Use UUID format and convert for writing evaluations

```python
import uuid

# User from auth system
user_uuid = "bc46601b-a323-4422-bd2c-92ecd07e1e34"

# Save speaking evaluation (native UUID)
speaking_data = {
    "user_id": user_uuid,  # UUID string
    "session_id": str(uuid.uuid4()),
    "day_code": "day1",
    # ... other fields
}

# Save writing evaluation (convert to text or use as-is)
writing_data = {
    "user_id": user_uuid,  # Works as text too
    "day_code": "day1",
    # ... other fields
}

# Get user competency (works for both)
response = requests.get(f"/api/competency/user/{user_uuid}")
```

### Scenario 2: Separate Users (Writing-Only User)

If you have a user who only does writing evaluations with a text ID:

```python
# Text-based user ID
text_user_id = "student_john_123"

# Save writing evaluation
writing_data = {
    "user_id": text_user_id,  # Text format
    "day_code": "day1",
    # ... other fields
}

# Get user competency (will only show writing progress)
response = requests.get(f"/api/competency/user/{text_user_id}")
# Returns: speaking_completed=false for all days, only writing data shown
```

---

## API Behavior

### GET `/api/competency/user/{user_id}`

The endpoint handles both UUID and text user IDs:

1. **If user_id is valid UUID format:**
   - Queries both `speaking_evaluations` (UUID match)
   - Queries `writing_evaluations` (text match)
   - Returns combined progress

2. **If user_id is text (not UUID):**
   - Skips `speaking_evaluations` (UUID parsing fails gracefully)
   - Queries `writing_evaluations` (text match)
   - Returns only writing progress

**Example Responses:**

#### UUID User with Both Evaluations
```json
{
  "user_id": "bc46601b-a323-4422-bd2c-92ecd07e1e34",
  "progress_by_day": [
    {
      "day_code": "day1",
      "speaking_completed": true,
      "writing_completed": true,
      "speaking_score": 76,
      "writing_score": 72
    }
  ],
  "average_speaking_score": 76.0,
  "average_writing_score": 72.0
}
```

#### Text User (Writing Only)
```json
{
  "user_id": "student_john_123",
  "progress_by_day": [
    {
      "day_code": "day1",
      "speaking_completed": false,
      "writing_completed": true,
      "speaking_score": null,
      "writing_score": 72
    }
  ],
  "average_speaking_score": null,
  "average_writing_score": 72.0
}
```

---

## Recommendations

### Option 1: Standardize on UUID (Recommended)

**Best for:** New implementations, unified user system

1. Always use UUID for user identification
2. Both speaking and writing use the same UUID
3. Clean data model and easy querying

```python
# Always use UUID from auth system
user_uuid = str(user.id)  # From auth.users

# Use for both evaluations
save_speaking_evaluation(user_id=user_uuid, ...)
save_writing_evaluation(user_id=user_uuid, ...)
```

### Option 2: Keep Separate (Current State)

**Best for:** Legacy compatibility, existing data

1. Use UUID for speaking evaluations (from `auth.users`)
2. Use text for writing evaluations (custom format)
3. Link them externally if needed (e.g., via user profile table)

```python
# Speaking uses auth UUID
speaking_user_id = auth_user.id  # UUID

# Writing uses custom text
writing_user_id = f"user_{auth_user.email.split('@')[0]}"  # Text

# Query separately
speaking_progress = get_user_competency(speaking_user_id)
writing_progress = get_user_competency(writing_user_id)
```

### Option 3: Migrate Writing Table (Future)

**Best for:** Long-term consistency

Migrate `writing_evaluations.user_id` from text to UUID:

```sql
-- Backup first!
CREATE TABLE writing_evaluations_backup AS
SELECT * FROM writing_evaluations;

-- Add new UUID column
ALTER TABLE writing_evaluations
ADD COLUMN user_uuid UUID;

-- Migrate data (if possible - depends on your text format)
UPDATE writing_evaluations
SET user_uuid = user_id::uuid
WHERE user_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- Drop old column and rename
ALTER TABLE writing_evaluations DROP COLUMN user_id;
ALTER TABLE writing_evaluations RENAME COLUMN user_uuid TO user_id;

-- Add foreign key
ALTER TABLE writing_evaluations
ADD CONSTRAINT writing_evaluations_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth.users(id);
```

---

## Testing

### Test with UUID User
```bash
# UUID format
curl http://localhost:8000/api/competency/user/bc46601b-a323-4422-bd2c-92ecd07e1e34
```

### Test with Text User
```bash
# Text format
curl http://localhost:8000/api/competency/user/student_john_123
```

Both should work without errors!

---

## Troubleshooting

### Error: "invalid input syntax for type uuid"

**Cause:** Trying to query `speaking_evaluations` with a text user_id

**Solution:** This is now handled gracefully. The service catches the error and continues with only writing evaluations.

### No Data Returned

**Check:**
1. Is the user_id saved exactly as you're querying?
2. For speaking: Must be valid UUID format
3. For writing: Can be any text
4. Case sensitivity matters!

---

## Summary

| Scenario | Speaking user_id | Writing user_id | Recommendation |
|----------|-----------------|----------------|----------------|
| **New app** | UUID | UUID | ✅ Use same UUID for both |
| **Legacy data** | UUID | Text | ⚠️ Keep separate, handle both |
| **Writing only** | N/A | Text | ✅ Use text, no speaking data |
| **Speaking only** | UUID | N/A | ✅ Use UUID, no writing data |

---

## Code Examples

### React/Next.js Example

```typescript
// Get current user from auth
const { user } = useAuth();  // Returns auth.users object
const userId = user.id;  // UUID string

// Save speaking evaluation
await fetch('/api/competency/speaking/save', {
  method: 'POST',
  body: JSON.stringify({
    user_id: userId,  // UUID
    day_code: 'day1',
    // ... other fields
  })
});

// Save writing evaluation
await fetch('/api/competency/writing/save', {
  method: 'POST',
  body: JSON.stringify({
    user_id: userId,  // Same UUID works!
    day_code: 'day1',
    // ... other fields
  })
});

// Get progress (shows both)
const response = await fetch(`/api/competency/user/${userId}`);
const progress = await response.json();

// progress will have both speaking and writing data
console.log(progress.average_speaking_score);
console.log(progress.average_writing_score);
```

### Python Example

```python
import requests
from uuid import uuid4

# Auth user UUID
user_id = "bc46601b-a323-4422-bd2c-92ecd07e1e34"

# Save both evaluations with same user_id
requests.post('/api/competency/speaking/save', json={
    'user_id': user_id,
    'session_id': str(uuid4()),
    'day_code': 'day1',
    # ...
})

requests.post('/api/competency/writing/save', json={
    'user_id': user_id,  # Same ID
    'day_code': 'day1',
    # ...
})

# Get combined progress
response = requests.get(f'/api/competency/user/{user_id}')
progress = response.json()

# Check completion
day1 = next(d for d in progress['progress_by_day'] if d['day_code'] == 'day1')
if day1['speaking_completed'] and day1['writing_completed']:
    print("Day 1 fully completed!")
```

---

**Last Updated:** 2025-10-29
**Status:** Working as intended with graceful fallback
