# Writing Evaluation - Simplified Response with Error Highlighting

## Overview

The writing evaluation service now returns a simplified response focused on the essential fields needed for frontend display:

### What You Get:
✅ **overall_score** - Overall writing quality (0-100)
✅ **scores** - Detailed category scores (grammar, vocabulary, etc.)
✅ **improved_version** - The corrected text
✅ **error_highlights** - List of errors with corrections for red/green highlighting

### What's Removed:
❌ strengths
❌ improvements
❌ suggestions
❌ feedback_summary
❌ original_text

---

## API Response Format

### Request
```json
POST /writing/evaluate

{
  "text": "I am learning English for two years now.",
  "language": "english",
  "writing_type": "general",
  "user_level": "intermediate",
  "save_evaluation": false
}
```

### Response
```json
{
  "evaluation_id": "550e8400-e29b-41d4-a716-446655440000",
  "overall_score": 75,
  "scores": {
    "grammar": 70,
    "vocabulary": 80,
    "coherence": 75,
    "style": 75,
    "clarity": 80,
    "engagement": 75
  },
  "improved_version": "I have been learning English for two years now.",
  "error_highlights": [
    {
      "error_text": "am learning",
      "correction": "have been learning",
      "error_type": "grammar",
      "position": 2
    },
    {
      "error_text": "for two years now",
      "correction": "for two years",
      "error_type": "word choice",
      "position": 30
    }
  ],
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

## Error Highlighting Format

Each error highlight contains:

| Field | Description | Frontend Display |
|-------|-------------|------------------|
| `error_text` | Text with the error | **Red background** or red underline |
| `correction` | Corrected text | **Green text** when shown |
| `error_type` | Type of error | Badge/label (grammar, spelling, etc.) |
| `position` | Character position in original text | For precise highlighting |

### Error Types:
- `grammar` - Grammatical errors
- `spelling` - Spelling mistakes
- `punctuation` - Punctuation errors
- `word choice` - Better word alternatives

---

## Frontend Implementation

### HTML/CSS Example

```html
<div class="evaluation-container">
  <!-- Overall Score -->
  <div class="score-badge">
    <h3>Overall Score: <span class="score">{{ overall_score }}/100</span></h3>
  </div>

  <!-- Category Scores -->
  <div class="detailed-scores">
    <div class="score-item" *ngFor="let score of scores | keyvalue">
      <span class="category">{{ score.key | titlecase }}</span>
      <div class="score-bar">
        <div class="score-fill" [style.width.%]="score.value"></div>
      </div>
      <span class="score-value">{{ score.value }}/100</span>
    </div>
  </div>

  <!-- Original Text with Error Highlights -->
  <div class="original-text-section">
    <h4>Your Text (with corrections):</h4>
    <div class="highlighted-text">
      <span *ngFor="let segment of highlightedSegments"
            [ngClass]="{
              'error': segment.isError,
              'correct': !segment.isError
            }"
            [title]="segment.isError ? 'Correction: ' + segment.correction : ''">
        {{ segment.text }}
      </span>
    </div>
  </div>

  <!-- Improved Version -->
  <div class="improved-version-section">
    <h4>Improved Version:</h4>
    <p class="improved-text">{{ improved_version }}</p>
  </div>

  <!-- Error Details List -->
  <div class="error-details">
    <h4>Corrections:</h4>
    <div class="error-item" *ngFor="let error of error_highlights">
      <span class="error-label">{{ error.error_type }}</span>
      <span class="error-original">{{ error.error_text }}</span>
      <span class="arrow">→</span>
      <span class="error-correction">{{ error.correction }}</span>
    </div>
  </div>
</div>
```

### CSS Styling

```css
/* Score Display */
.score-badge {
  background: #4CAF50;
  color: white;
  padding: 20px;
  border-radius: 10px;
  text-align: center;
}

.score {
  font-size: 2em;
  font-weight: bold;
}

/* Detailed Scores */
.detailed-scores {
  margin: 20px 0;
}

.score-item {
  display: flex;
  align-items: center;
  margin: 10px 0;
}

.category {
  width: 120px;
  font-weight: 500;
}

.score-bar {
  flex: 1;
  height: 20px;
  background: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
  margin: 0 10px;
}

.score-fill {
  height: 100%;
  background: linear-gradient(90deg, #FF6B6B 0%, #FFA500 50%, #4CAF50 100%);
  transition: width 0.3s ease;
}

/* Error Highlighting */
.highlighted-text {
  font-size: 16px;
  line-height: 1.8;
  padding: 15px;
  background: #f5f5f5;
  border-radius: 5px;
}

.error {
  background-color: #ffebee;
  color: #c62828;
  padding: 2px 4px;
  border-radius: 3px;
  border-bottom: 2px solid #ef5350;
  cursor: help;
  position: relative;
}

.error:hover::after {
  content: attr(title);
  position: absolute;
  bottom: 100%;
  left: 0;
  background: #333;
  color: white;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 10;
}

/* Improved Version */
.improved-text {
  font-size: 16px;
  line-height: 1.8;
  padding: 15px;
  background: #e8f5e9;
  border-left: 4px solid #4CAF50;
  border-radius: 5px;
}

/* Error Details */
.error-item {
  display: flex;
  align-items: center;
  padding: 10px;
  margin: 5px 0;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 5px;
}

.error-label {
  background: #ff9800;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  margin-right: 10px;
}

.error-original {
  color: #c62828;
  text-decoration: line-through;
  margin-right: 10px;
}

.arrow {
  color: #757575;
  margin: 0 5px;
}

.error-correction {
  color: #2e7d32;
  font-weight: 500;
}
```

### JavaScript/TypeScript Processing

```typescript
interface ErrorHighlight {
  error_text: string;
  correction: string;
  error_type: string;
  position: number;
}

interface EvaluationResponse {
  evaluation_id: string;
  overall_score: number;
  scores: Record<string, number>;
  improved_version: string;
  error_highlights: ErrorHighlight[];
  created_at: string;
}

function processTextWithHighlights(
  originalText: string,
  errorHighlights: ErrorHighlight[]
): Array<{text: string; isError: boolean; correction?: string}> {

  // Sort errors by position
  const sortedErrors = [...errorHighlights].sort((a, b) => a.position - b.position);

  const segments = [];
  let lastPosition = 0;

  for (const error of sortedErrors) {
    // Add text before error
    if (error.position > lastPosition) {
      segments.push({
        text: originalText.substring(lastPosition, error.position),
        isError: false
      });
    }

    // Add error text
    segments.push({
      text: error.error_text,
      isError: true,
      correction: error.correction
    });

    lastPosition = error.position + error.error_text.length;
  }

  // Add remaining text
  if (lastPosition < originalText.length) {
    segments.push({
      text: originalText.substring(lastPosition),
      isError: false
    });
  }

  return segments;
}

// Usage in component
async evaluateText(text: string) {
  const response = await fetch('/writing/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      language: 'english',
      writing_type: 'general',
      user_level: 'intermediate',
      save_evaluation: false
    })
  });

  const evaluation: EvaluationResponse = await response.json();

  // Process for display
  this.overallScore = evaluation.overall_score;
  this.scores = evaluation.scores;
  this.improvedVersion = evaluation.improved_version;
  this.highlightedSegments = processTextWithHighlights(
    text,  // original text
    evaluation.error_highlights
  );
}
```

### React Example

```jsx
import React, { useState } from 'react';

function WritingEvaluator() {
  const [text, setText] = useState('');
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleEvaluate = async () => {
    setLoading(true);
    try {
      const response = await fetch('/writing/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          language: 'english',
          writing_type: 'general',
          user_level: 'intermediate',
          save_evaluation: false
        })
      });
      const data = await response.json();
      setEvaluation(data);
    } catch (error) {
      console.error('Evaluation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderHighlightedText = () => {
    if (!evaluation) return null;

    const segments = processTextWithHighlights(text, evaluation.error_highlights);

    return (
      <div className="highlighted-text">
        {segments.map((segment, index) => (
          segment.isError ? (
            <span
              key={index}
              className="error"
              title={`Correction: ${segment.correction}`}
            >
              {segment.text}
            </span>
          ) : (
            <span key={index}>{segment.text}</span>
          )
        ))}
      </div>
    );
  };

  return (
    <div className="evaluator-container">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Enter your text here..."
        rows={10}
        className="text-input"
      />

      <button onClick={handleEvaluate} disabled={loading || !text}>
        {loading ? 'Evaluating...' : 'Evaluate'}
      </button>

      {evaluation && (
        <div className="results">
          {/* Overall Score */}
          <div className="score-badge">
            <h2>Score: {evaluation.overall_score}/100</h2>
          </div>

          {/* Category Scores */}
          <div className="scores-grid">
            {Object.entries(evaluation.scores).map(([category, score]) => (
              <div key={category} className="score-item">
                <span className="category">{category}</span>
                <div className="score-bar">
                  <div
                    className="score-fill"
                    style={{ width: `${score}%` }}
                  />
                </div>
                <span className="score-value">{score}</span>
              </div>
            ))}
          </div>

          {/* Original Text with Highlights */}
          <div className="section">
            <h3>Your Text:</h3>
            {renderHighlightedText()}
          </div>

          {/* Improved Version */}
          <div className="section">
            <h3>Improved Version:</h3>
            <p className="improved-text">{evaluation.improved_version}</p>
          </div>

          {/* Error Details */}
          <div className="section">
            <h3>Corrections ({evaluation.error_highlights.length}):</h3>
            {evaluation.error_highlights.map((error, index) => (
              <div key={index} className="error-item">
                <span className="error-label">{error.error_type}</span>
                <span className="error-original">{error.error_text}</span>
                <span className="arrow">→</span>
                <span className="error-correction">{error.correction}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## Testing the New Response

### cURL Example

```bash
curl -X POST "http://localhost:8000/writing/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I am learning English for two years now. Yesterday I go to the market.",
    "language": "english",
    "writing_type": "general",
    "user_level": "intermediate",
    "save_evaluation": false
  }' | jq
```

### Expected Response

```json
{
  "evaluation_id": "abc-123-def-456",
  "overall_score": 72,
  "scores": {
    "grammar": 65,
    "vocabulary": 75,
    "coherence": 75,
    "style": 70,
    "clarity": 75,
    "engagement": 72
  },
  "improved_version": "I have been learning English for two years. Yesterday I went to the market.",
  "error_highlights": [
    {
      "error_text": "am learning",
      "correction": "have been learning",
      "error_type": "grammar",
      "position": 2
    },
    {
      "error_text": "go",
      "correction": "went",
      "error_type": "grammar",
      "position": 50
    }
  ],
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

## Visual Display Examples

### Desktop View
```
┌────────────────────────────────────────────────┐
│           Overall Score: 75/100                │
└────────────────────────────────────────────────┘

Category Scores:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Grammar    ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░ 70/100
Vocabulary ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░ 80/100
Coherence  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░ 75/100
...

Your Text:
I [am learning]ᴿᴱᴰ English for two years now.
     ↓ have been learning

Improved Version:
I have been learning English for two years.

Corrections:
🔸 grammar | am learning → have been learning
🔸 word choice | for two years now → for two years
```

### Mobile View
```
┌──────────────────────┐
│   Score: 75/100      │
└──────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━
Grammar:    70 ▓▓▓▓░░
Vocabulary: 80 ▓▓▓▓▓░
...

Your Text:
I [am learning]ᴿᴱᴰ for
two years.
→ have been learning

✓ Improved:
I have been learning
for two years.
```

---

## Benefits of Simplified Response

1. **Smaller Payload** - Reduced API response size
2. **Faster Rendering** - Less data to process on frontend
3. **Visual Focus** - Emphasizes error corrections with red/green highlighting
4. **Better UX** - Users see exactly what's wrong and how to fix it
5. **Mobile Friendly** - Compact format works better on small screens
6. **Actionable** - Corrections are immediately visible and understandable

---

## Backward Compatibility

The legacy full response with all fields is still available in the `EvaluationResponseFull` model if needed. To use it, create a separate endpoint or add a query parameter.

---

## Summary

The new simplified writing evaluation response provides:
- ✅ Overall and detailed scores
- ✅ Improved/corrected text
- ✅ Error highlights with red/green display data
- ❌ Removed verbose fields (strengths, improvements, suggestions)

Perfect for frontend applications that need clean, visual error highlighting!
