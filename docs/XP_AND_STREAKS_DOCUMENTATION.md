# XP & Streaks Management Documentation

## Overview

The **XP (Experience Points) and Streaks** system gamifies learning with daily goals, level progression, and streak tracking. This document covers XP calculation, streak management, daily goals, and level progression.

---

## Table of Contents

1. [XP System](#xp-system)
2. [Streak System](#streak-system)
3. [Level System](#level-system)
4. [Daily Goals & Progress](#daily-goals--progress)
5. [API Endpoints](#api-endpoints)
6. [XP Calculation Examples](#xp-calculation-examples)
7. [Best Practices](#best-practices)

---

## XP System

### XP Configuration

| Component | Value | Description |
|-----------|-------|-------------|
| **Base Session XP** | 20 XP | Awarded for completing any session |
| **Accuracy Bonus** | 10 XP | Awarded for ≥80% accuracy |
| **Perfect Score Bonus** | 25 XP | Awarded for 100% accuracy |
| **First Session Bonus** | 15 XP | First session of the day |
| **Speed Bonus** | Up to 10 XP | Completing faster than expected |
| **Streak Bonus** | 2 XP/day (max 30) | Based on current streak |
| **Perfect Day Bonus** | 50 XP | All 3 modalities completed |
| **Badge Bonus** | 50 XP | Awarded with each badge |

### XP Calculation Formula

```
Total XP = Base (20)
         + Accuracy Bonus (10 if ≥80%)
         + Perfect Score (25 if 100%)
         + Speed Bonus (0-10)
         + Streak Bonus (current_streak * 2, max 30)
         + First Session (15 if first today)
         + Perfect Day (50 if R+L+G done)
```

### XP Sources

XP can be earned from:
- **Sessions** - Completing listening, reading, or grammar sessions
- **Badges** - Earning achievement badges
- **Streaks** - Maintaining daily learning streaks
- **Bonuses** - Speed, accuracy, and perfect day bonuses

---

## Streak System

### How Streaks Work

1. **Streak Starts**: Complete any session on a day
2. **Streak Continues**: Complete at least one session the next day
3. **Streak Breaks**: Skip a day (no sessions completed)
4. **Streak Resets**: Starts at 1 after breaking

### Streak Status

| Status | Description | Condition |
|--------|-------------|-----------|
| **Active** | Learned today | Last active = today |
| **At Risk** | Haven't learned today | Last active = yesterday |
| **Broken** | Missed a day | Last active > 1 day ago |

### Streak Tracking

```json
{
  "current_streak": 15,
  "longest_streak": 30,
  "last_active_date": "2025-10-06",
  "is_active_today": true,
  "streak_status": "active"
}
```

---

## Level System

### Level Calculation

Levels are calculated using **exponential XP growth**:

```
XP Required for Level N = 100 * (1.5 ^ (N - 1))
```

### Level Progression Table

| Level | XP Required (Total) | XP for This Level | Level Name |
|-------|---------------------|-------------------|------------|
| 1 | 0 | 0 | Beginner |
| 2 | 100 | 100 | Beginner |
| 3 | 250 | 150 | Beginner |
| 4 | 475 | 225 | Beginner |
| 5 | 813 | 338 | Beginner |
| 6 | 1,320 | 507 | Intermediate |
| 7 | 2,080 | 760 | Intermediate |
| 8 | 3,220 | 1,140 | Intermediate |
| 9 | 4,930 | 1,710 | Intermediate |
| 10 | 7,495 | 2,565 | Intermediate |
| 15 | 38,443 | - | Advanced |
| 20 | 254,803 | - | Expert |
| 25 | 1,693,508 | - | Expert |
| 30+ | - | - | Master |

### Level Names

| Level Range | Name |
|-------------|------|
| 1-5 | **Beginner** |
| 6-10 | **Intermediate** |
| 11-20 | **Advanced** |
| 21-35 | **Expert** |
| 36+ | **Master** |

---

## Daily Goals & Progress

### Default Daily Goals

1. **XP Goal**: 100 XP
2. **Session Goal**: 3 sessions (1 per modality)
3. **Perfect Day**: Complete Listening + Reading + Grammar

### Daily Progress Tracking

```json
{
  "date": "2025-10-06",
  "xp_earned": 85,
  "xp_goal": 100,
  "sessions_completed": 2,
  "session_goal": 3,
  "time_spent_minutes": 45,
  "modalities_completed": ["listening", "reading"],
  "goals": [
    {
      "goal_type": "xp",
      "target": 100,
      "current": 85,
      "is_completed": false
    },
    {
      "goal_type": "sessions",
      "target": 3,
      "current": 2,
      "is_completed": false
    },
    {
      "goal_type": "perfect_day",
      "target": 1,
      "current": 0,
      "is_completed": false
    }
  ],
  "is_perfect_day": false
}
```

---

## API Endpoints

### 1. Get User XP Summary

**Endpoint:** `GET /api/v1/users/{user_id}/xp`

**Description:** Get total XP, today's XP, and level information.

**Response:**
```json
{
  "user_id": "uuid",
  "total_xp": 1250,
  "today_xp": 75,
  "current_level": 6,
  "xp_to_next_level": 70,
  "level_progress_pct": 85
}
```

---

### 2. Get Daily XP Breakdown

**Endpoint:** `GET /api/v1/users/{user_id}/xp/daily`

**Description:** Detailed XP breakdown for today with sources.

**Response:**
```json
{
  "user_id": "uuid",
  "date": "2025-10-06",
  "xp_earned_today": 120,
  "xp_goal": 100,
  "goal_completion_pct": 120,
  "sessions_today": 3,
  "breakdown": [
    {
      "user_id": "uuid",
      "amount": 20,
      "source": "session",
      "occurred_at": "2025-10-06T10:00:00Z"
    },
    {
      "user_id": "uuid",
      "amount": 50,
      "source": "perfect_day_bonus",
      "occurred_at": "2025-10-06T14:00:00Z"
    },
    {
      "user_id": "uuid",
      "amount": 50,
      "source": "badge_streak_7",
      "occurred_at": "2025-10-06T14:00:00Z"
    }
  ]
}
```

---

### 3. Get User Level Info

**Endpoint:** `GET /api/v1/users/{user_id}/level`

**Description:** Detailed level progression information.

**Response:**
```json
{
  "current_level": 8,
  "level_name": "Intermediate",
  "total_xp": 3500,
  "xp_for_current_level": 3220,
  "xp_for_next_level": 4930,
  "xp_to_next_level": 1430,
  "progress_pct": 16
}
```

---

### 4. Get User Streak

**Endpoint:** `GET /api/v1/users/{user_id}/streak`

**Description:** Current streak status and history.

**Response:**
```json
{
  "user_id": "uuid",
  "current_streak": 15,
  "longest_streak": 30,
  "last_active_date": "2025-10-06",
  "is_active_today": true,
  "streak_status": "active"
}
```

---

### 5. Get Daily Progress

**Endpoint:** `GET /api/v1/users/{user_id}/daily-progress`

**Description:** Complete daily progress with all goals.

**Response:**
```json
{
  "user_id": "uuid",
  "date": "2025-10-06",
  "xp_earned": 120,
  "xp_goal": 100,
  "sessions_completed": 3,
  "session_goal": 3,
  "time_spent_minutes": 55,
  "modalities_completed": ["listening", "reading", "grammar"],
  "goals": [
    {
      "goal_type": "xp",
      "target": 100,
      "current": 120,
      "is_completed": true
    },
    {
      "goal_type": "sessions",
      "target": 3,
      "current": 3,
      "is_completed": true
    },
    {
      "goal_type": "perfect_day",
      "target": 1,
      "current": 1,
      "is_completed": true
    }
  ],
  "is_perfect_day": true
}
```

---

### 6. Get Streak Calendar

**Endpoint:** `GET /api/v1/users/{user_id}/streak-calendar?month=2025-10`

**Description:** Calendar view of activity for a month.

**Response:**
```json
{
  "user_id": "uuid",
  "current_month": "2025-10",
  "days": [
    {
      "date": "2025-10-01",
      "sessions_completed": 3,
      "modalities_completed": ["listening", "reading", "grammar"],
      "total_xp_earned": 150,
      "streak_day": 15
    },
    {
      "date": "2025-10-02",
      "sessions_completed": 2,
      "modalities_completed": ["listening", "reading"],
      "total_xp_earned": 85,
      "streak_day": 16
    }
  ],
  "current_streak": 16,
  "perfect_days": 12
}
```

---

## XP Calculation Examples

### Example 1: Basic Session (Low Performance)

**Scenario:**
- Accuracy: 65%
- Duration: 900 seconds (expected: 720 seconds - slower)
- Streak: 0 (new user)
- First session: No

**XP Breakdown:**
```
Base XP:             20
Accuracy Bonus:       0  (< 80%)
Perfect Score:        0  (< 100%)
Speed Bonus:          0  (slower than expected)
Streak Bonus:         0  (no streak)
First Session:        0  (not first today)
Perfect Day:          0  (not all modalities)
-------------------------
Total XP:            20
```

---

### Example 2: Great Session (High Performance)

**Scenario:**
- Accuracy: 95%
- Duration: 540 seconds (expected: 720 seconds - 25% faster)
- Streak: 10 days
- First session: Yes

**XP Breakdown:**
```
Base XP:             20
Accuracy Bonus:      10  (≥ 80%)
Perfect Score:        0  (< 100%)
Speed Bonus:          2  (25% faster = 2.5 XP, rounded)
Streak Bonus:        20  (10 days * 2 XP)
First Session:       15  (first of the day)
Perfect Day:          0  (not all modalities yet)
-------------------------
Total XP:            67
```

---

### Example 3: Perfect Day Achievement

**Scenario:**
- User completes all 3 modalities
- Listening: 85% accuracy, 10-day streak
- Reading: 90% accuracy
- Grammar: 100% accuracy (perfect score)

**XP Breakdown:**

**Listening Session:**
```
Base: 20 + Accuracy: 10 + Streak: 20 + First: 15 = 65 XP
```

**Reading Session:**
```
Base: 20 + Accuracy: 10 + Streak: 20 = 50 XP
```

**Grammar Session:**
```
Base: 20 + Accuracy: 10 + Perfect: 25 + Streak: 20 + Perfect Day: 50 = 125 XP
```

**Total XP Today:** 240 XP 🎉

---

### Example 4: Streak Bonus Growth

| Streak Days | Streak Bonus | Total XP (80% accuracy) |
|-------------|--------------|-------------------------|
| 0 | 0 XP | 30 XP |
| 1 | 2 XP | 32 XP |
| 5 | 10 XP | 40 XP |
| 10 | 20 XP | 50 XP |
| 15 | 30 XP (max) | 60 XP |
| 20+ | 30 XP (max) | 60 XP |

---

## Best Practices

### For Learners

1. **Maintain Streaks**: Log in daily to keep streak bonuses
2. **Aim for Perfect Days**: Complete all 3 modalities for 50 XP bonus
3. **Focus on Accuracy**: ≥80% unlocks 10 XP bonus
4. **Speed Matters**: Complete sessions efficiently for speed bonus
5. **Track Progress**: Check daily goals to stay motivated

### For Frontend Implementation

#### 1. Display XP Gains After Session
```javascript
// Show XP breakdown after session completion
{
  "base_xp": 20,
  "accuracy_bonus": 10,
  "streak_bonus": 20,
  "total_xp": 50,
  "message": "Great job! +50 XP earned"
}
```

#### 2. Show Streak Status
```javascript
// Daily reminder for streak maintenance
if (streak_status === "at_risk") {
  showNotification("Complete a session today to maintain your 15-day streak!");
}
```

#### 3. Progress Bars
```javascript
// Show visual progress
<ProgressBar
  current={xp_to_next_level}
  total={xp_for_next_level}
  label="Level 8 → Level 9"
/>
```

#### 4. Daily Goal Tracking
```javascript
// Display goal completion
goals.forEach(goal => {
  if (goal.is_completed) {
    showCheckmark(goal.goal_type);
  }
});
```

---

### Gamification Tips

1. **Level Up Celebrations**: Show animation when user levels up
2. **Streak Milestones**: Celebrate 7, 30, 100 day streaks
3. **Daily Challenges**: Encourage "Perfect Day" achievement
4. **Leaderboards**: Show top XP earners (coming soon)
5. **Badge Integration**: Award badges for XP milestones

---

## Database Schema

### XP Ledger Table

```sql
CREATE TABLE xp_ledger (
  xp_id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  amount INTEGER NOT NULL,
  source TEXT NOT NULL,  -- 'session', 'badge', 'streak_bonus', etc.
  occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Streaks Table

```sql
CREATE TABLE streaks (
  streak_id UUID PRIMARY KEY,
  user_id UUID NOT NULL UNIQUE,
  current_streak INTEGER DEFAULT 0,
  longest_streak INTEGER DEFAULT 0,
  last_active_date DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Integration with Sessions

When a session is submitted, XP and streaks are automatically updated:

```python
# After session completion
1. Calculate accuracy and duration
2. Get current streak
3. Check if first session today
4. Check if perfect day (after this session)
5. Calculate XP with all bonuses
6. Award XP to xp_ledger
7. Update streak
8. Check and award badges
```

---

## Frequently Asked Questions

**Q: What happens if I miss a day?**
A: Your streak resets to 1 when you next complete a session.

**Q: Can I earn XP without completing sessions?**
A: Yes, earning badges awards 50 XP each.

**Q: Is there a maximum XP cap?**
A: No, you can earn unlimited XP.

**Q: How is "today" defined?**
A: Based on UTC timezone (can be configured to user's timezone).

**Q: Do all sessions earn the same base XP?**
A: Yes, all modalities (listening, reading, grammar) earn 20 base XP.

**Q: What's the fastest way to level up?**
A: Maintain a streak, complete all 3 modalities daily, and aim for high accuracy.

---

## Summary

The XP and Streaks system provides:
- ✅ **Motivating Rewards** - XP bonuses for achievements
- ✅ **Daily Engagement** - Streak tracking encourages consistency
- ✅ **Level Progression** - Clear advancement path
- ✅ **Goal Tracking** - Daily targets keep users focused
- ✅ **Gamification** - Makes learning fun and competitive

---

**Version:** 1.0
**Last Updated:** 2025-10-06
**Maintained By:** LRG Development Team
