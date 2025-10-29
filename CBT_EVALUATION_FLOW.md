# CBT Evaluation Endpoint - Flow Diagram

## Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Application                        │
│  (Frontend, Mobile App, Testing Tool, etc.)                      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ HTTP POST Request
                                │ /api/cbt-evaluation/evaluate
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                        │
│                      (app/api/main.py)                           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ Route to endpoint
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CBT Evaluation Router                          │
│              (app/api/routes/cbt_evaluation.py)                  │
│                                                                   │
│  • Validate request (CBTEvaluationRequest schema)                │
│  • Extract: question, answer, skill_type, options               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ Call service
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 CBT Evaluation Service                           │
│          (app/services/cbt_evaluation_service.py)                │
│                                                                   │
│  1. Build evaluation prompt                                      │
│  2. Include CBT guidelines                                       │
│  3. Format question, answer, skill type                          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ API Call
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Google Gemini AI                            │
│           (gemini-2.5-flash-native-audio-preview)                │
│                                                                   │
│  • Evaluate answer quality                                       │
│  • Generate constructive feedback                                │
│  • Create CBT-based suggestion                                   │
│  • Calculate confidence score                                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ AI Response
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 CBT Evaluation Service                           │
│          (Parse and structure response)                          │
│                                                                   │
│  • Extract EVALUATION text                                       │
│  • Extract CBT_SUGGESTION text                                   │
│  • Extract CONFIDENCE score                                      │
│  • Format as CBTEvaluationResponse                               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ Return result
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CBT Evaluation Router                          │
│              (Return CBTEvaluationResponse)                      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ JSON Response
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Client Application                        │
│                                                                   │
│  Response received:                                              │
│  {                                                               │
│    "skill_type": "speaking",                                     │
│    "evaluation": "Constructive feedback...",                     │
│    "cbt_suggestion": "Therapeutic advice...",                    │
│    "confidence_score": 0.85,                                     │
│    "timestamp": "2025-10-27T10:30:00"                           │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Example

### Input (Request)
```json
{
  "question": "Tell me about your hobbies",
  "answer": "I like play guitar and reading book.",
  "skill_type": "speaking",
  "user_id": "student123"
}
```

### Processing Steps

1. **Validation**
   - ✓ Question is not empty
   - ✓ Answer is not empty
   - ✓ Skill type is valid (speaking, writing, listening, reading, grammar)

2. **Prompt Construction**
   ```
   You are a compassionate language learning evaluator...

   Task: Evaluate the following speaking exercise...
   Question: Tell me about your hobbies
   Student's Answer: I like play guitar and reading book.

   Provide response in format:
   EVALUATION: [feedback]
   CBT_SUGGESTION: [therapeutic advice]
   CONFIDENCE: [0-1]
   ```

3. **AI Processing**
   - Gemini analyzes the answer
   - Identifies grammar issues
   - Recognizes effort and progress
   - Generates encouraging feedback

4. **Response Parsing**
   - Extract evaluation: "You've communicated your interests..."
   - Extract CBT suggestion: "Great job expressing yourself..."
   - Extract confidence: 0.92

### Output (Response)
```json
{
  "skill_type": "speaking",
  "evaluation": "You've communicated your interests clearly! Minor grammar improvements: 'I like playing guitar and reading books'...",
  "cbt_suggestion": "Great job expressing yourself! Making small grammar mistakes is completely normal...",
  "confidence_score": 0.92,
  "timestamp": "2025-10-27T10:35:00.000Z"
}
```

## Component Interaction

```
┌──────────────────────┐
│   Pydantic Schemas   │
│                      │
│  • Request Model     │────────┐
│  • Response Model    │        │
│  • Validation Rules  │        │ Type Safety
└──────────────────────┘        │ & Validation
                                │
                                ▼
┌──────────────────────┐    ┌──────────────────────┐
│    FastAPI Router    │◄───│   Service Layer      │
│                      │    │                      │
│  • Endpoint def      │    │  • Business logic    │
│  • Error handling    │    │  • AI integration    │
│  • HTTP responses    │    │  • Response parsing  │
└──────────────────────┘    └──────────┬───────────┘
                                       │
                                       │ API Key
                                       │ from config
                                       ▼
                            ┌──────────────────────┐
                            │   Configuration      │
                            │                      │
                            │  • GEMINI_API_KEY    │
                            │  • MODEL selection   │
                            └──────────────────────┘
```

## Error Handling Flow

```
Request
  │
  ├──► Validation Error (422)
  │    • Invalid skill_type
  │    • Missing required fields
  │    • Invalid data types
  │
  ├──► Service Error (500)
  │    • AI API connection failed
  │    • Parsing error
  │    • Timeout
  │
  └──► Success (200)
       • Valid evaluation returned
```

## Skill Types Supported

```
┌─────────────────────────────────────────────┐
│         CBT Evaluation Endpoint             │
└─────────────────┬───────────────────────────┘
                  │
                  ├──► 🗣️  Speaking
                  │     • Fluency
                  │     • Grammar in speech
                  │     • Vocabulary usage
                  │
                  ├──► ✍️  Writing
                  │     • Structure
                  │     • Grammar & spelling
                  │     • Coherence
                  │
                  ├──► 👂 Listening
                  │     • Comprehension
                  │     • Detail retention
                  │     • Inference
                  │
                  ├──► 📖 Reading
                  │     • Understanding
                  │     • Summary ability
                  │     • Analysis
                  │
                  └──► 📝 Grammar
                        • Accuracy
                        • Rule application
                        • Error correction
```

## Integration Points

```
Frontend Application
        │
        ├──► Direct HTTP calls
        ├──► Axios/Fetch
        └──► API client libraries
                │
                ▼
        CBT Evaluation API
                │
                ├──► Logging system
                ├──► Monitoring tools
                └──► Analytics (optional)
```

## Deployment Flow

```
Development
    │
    ├──► Local testing (localhost:8000)
    ├──► Unit tests
    └──► Integration tests
            │
            ▼
        Staging
            │
            ├──► E2E tests
            └──► Performance tests
                    │
                    ▼
                Production
                    │
                    ├──► Load balancing
                    ├──► Rate limiting
                    └──► Monitoring & alerts
```
