# Enhanced Multilingual Voice Learning Server

A production-ready language learning platform with real-time voice interaction, automatic scoring, and comprehensive session management.

## 🚀 Features

- **REST API** for teaching metadata, session management, and conversation tracking
- **WebSocket Integration** for real-time voice interaction
- **Automatic Language Scoring** with configurable rubrics per teaching mode
- **Session Persistence** with Redis and Supabase
- **Learning Summary Generation** with structured JSON output
- **Multi-language Support** with 40+ supported languages
- **8 Specialized Teaching Modes** (conversation, grammar, pronunciation, vocabulary, test prep, concept learning, reading, assessment)
- **Real-time Conversation Logging** with turn-by-turn scoring
- **Microservices Architecture** with dependency injection

## 🛠 Tech Stack

- **Backend**: FastAPI + WebSocket server
- **Database**: Supabase (PostgreSQL)
- **Cache/Session Store**: Redis
- **AI Integration**: Google Gemini 2.0 Flash Live
- **Audio Processing**: Real-time PCM audio streaming
- **Container**: Docker with Docker Compose

## 📋 Prerequisites

- Docker and Docker Compose
- Supabase account and project
- Google AI API key (Gemini)
- Redis (provided via Docker Compose)

## ⚙️ Environment Setup

Create a `.env` file in the project root:

```bash
# Required API Keys
GEMINI_API_KEY=your_gemini_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8765
HEALTH_PORT=8766
API_PORT=8000

# Audio Configuration
SEND_SAMPLE_RATE=16000
RECEIVE_SAMPLE_RATE=24000

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Optional Configuration
LOG_LEVEL=INFO
DEBUG=false
CORS_ORIGINS=*
SESSION_TIMEOUT_SECONDS=3600
MAX_TURNS_PER_SESSION=1000
```

## 🗃 Database Schema

Run this SQL in your Supabase SQL editor to set up the database:

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id TEXT UNIQUE NOT NULL,
  display_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Teaching modes table
CREATE TABLE IF NOT EXISTS teaching_modes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  rubric JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Supported languages table
CREATE TABLE IF NOT EXISTS supported_languages (
  code TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  level_cefr TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Default scenarios table
CREATE TABLE IF NOT EXISTS default_scenarios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mode_code TEXT REFERENCES teaching_modes(code) ON DELETE CASCADE,
  title TEXT NOT NULL,
  prompt TEXT NOT NULL,
  language_code TEXT REFERENCES supported_languages(code),
  metadata JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(mode_code, title, language_code)
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  mode_code TEXT REFERENCES teaching_modes(code),
  language_code TEXT REFERENCES supported_languages(code),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  closed_at TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}'::JSONB,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed', 'expired'))
);

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
  id BIGSERIAL PRIMARY KEY,
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  turn_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evaluations table
CREATE TABLE IF NOT EXISTS evaluations (
  id BIGSERIAL PRIMARY KEY,
  conversation_id BIGINT REFERENCES conversations(id) ON DELETE CASCADE,
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  mode_code TEXT,
  metrics JSONB NOT NULL,
  total_score NUMERIC,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Session summaries table
CREATE TABLE IF NOT EXISTS session_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  summary_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_session_turn ON conversations(session_id, turn_index);
CREATE INDEX IF NOT EXISTS idx_evaluations_session ON evaluations(session_id);
CREATE INDEX IF NOT EXISTS idx_summaries_user ON session_summaries(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON sessions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at DESC);

-- Insert default teaching modes
INSERT INTO teaching_modes (code, name, description, rubric) VALUES
('conversation', 'Conversation Practice', 'Natural conversation practice with gentle corrections', '{"weights":{"fluency":0.3,"vocabulary":0.25,"grammar":0.25,"pronunciation":0.2},"scales":{"min":0,"max":5},"guidelines":{"fluency":"Natural flow and rhythm","vocabulary":"Appropriate word choice","grammar":"Correct sentence structure","pronunciation":"Clear articulation"}}'),
('grammar', 'Grammar Practice', 'Focus on grammar rules, patterns, and correct usage', '{"weights":{"fluency":0.15,"vocabulary":0.2,"grammar":0.45,"pronunciation":0.2},"scales":{"min":0,"max":5},"guidelines":{"grammar":"Focus on grammatical accuracy and rule application"}}'),
('pronunciation', 'Pronunciation Practice', 'Improve pronunciation, stress, and intonation', '{"weights":{"fluency":0.2,"vocabulary":0.15,"grammar":0.2,"pronunciation":0.45},"scales":{"min":0,"max":5},"guidelines":{"pronunciation":"Focus on phoneme clarity and intonation"}}'),
('vocabulary', 'Vocabulary Building', 'Learn new words and expand vocabulary', '{"weights":{"fluency":0.2,"vocabulary":0.45,"grammar":0.2,"pronunciation":0.15},"scales":{"min":0,"max":5},"guidelines":{"vocabulary":"Focus on word variety and appropriate usage"}}'),
('test_prep', 'Test Preparation', 'Practice for English language tests and exams', '{"weights":{"fluency":0.25,"vocabulary":0.25,"grammar":0.3,"pronunciation":0.2},"scales":{"min":0,"max":5},"guidelines":{"grammar":"Test-specific grammar patterns","vocabulary":"Academic vocabulary usage"}}'),
('concept_learning', 'Concept Learning', 'Deep understanding of English language concepts', '{"weights":{"fluency":0.2,"vocabulary":0.3,"grammar":0.3,"pronunciation":0.2},"scales":{"min":0,"max":5},"guidelines":{"vocabulary":"Conceptual understanding","grammar":"Rule comprehension"}}'),
('reading', 'Reading Comprehension', 'Improve reading skills and understanding', '{"weights":{"fluency":0.15,"vocabulary":0.4,"grammar":0.25,"pronunciation":0.2},"scales":{"min":0,"max":5},"guidelines":{"vocabulary":"Reading vocabulary","grammar":"Text comprehension"}}'),
('assessment', 'Level Assessment', 'Assess current English proficiency level', '{"weights":{"fluency":0.25,"vocabulary":0.25,"grammar":0.25,"pronunciation":0.25},"scales":{"min":0,"max":5},"guidelines":{"overall":"Comprehensive skill assessment"}}')
ON CONFLICT (code) DO NOTHING;

-- Insert default supported languages
INSERT INTO supported_languages (code, label, level_cefr) VALUES
('en', 'English', 'C2'),
('es', 'Spanish', 'B2'),
('fr', 'French', 'B2'),
('de', 'German', 'B1'),
('it', 'Italian', 'B1'),
('pt', 'Portuguese', 'B1'),
('zh', 'Chinese (Mandarin)', 'A2'),
('ja', 'Japanese', 'A2'),
('ko', 'Korean', 'A1'),
('ar', 'Arabic', 'A2'),
('ru', 'Russian', 'B1'),
('hi', 'Hindi', 'A2')
ON CONFLICT (code) DO NOTHING;

-- Insert default scenarios
INSERT INTO default_scenarios (mode_code, title, prompt, language_code, metadata) VALUES
('conversation', 'Restaurant Conversation', 'You are at a restaurant. Practice ordering food, asking about menu items, and interacting with the waiter.', 'en', '{"level":"beginner","topics":["food","ordering","polite_conversation"]}'),
('conversation', 'Job Interview', 'You are in a job interview. Practice answering questions about your experience, skills, and career goals.', 'en', '{"level":"advanced","topics":["professional","career","communication"]}'),
('grammar', 'Verb Tenses Practice', 'Practice using different verb tenses in context through guided exercises and conversation.', 'en', '{"level":"intermediate","focus":["present_perfect","past_continuous","future_tenses"]}'),
('pronunciation', 'Difficult Sounds', 'Practice pronunciation of commonly difficult English sounds and word stress patterns.', 'en', '{"level":"intermediate","sounds":["th","r","l","word_stress"]}'),
('vocabulary', 'Academic Vocabulary', 'Learn and practice academic vocabulary through contextual usage and examples.', 'en', '{"level":"advanced","domains":["academic","formal","technical"]}}')
ON CONFLICT (mode_code, title, language_code) DO NOTHING;
```

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone and setup**:
```bash
git clone <repository-url>
cd voice-learning-server
cp .env.example .env
# Edit .env with your API keys
```

2. **Start services**:
```bash
docker-compose up -d
```

3. **Check health**:
```bash
curl http://localhost:8766/health
```

4. **Access services**:
- REST API: http://localhost:8000
- WebSocket: ws://localhost:8765
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8766/health

### Local Development

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Start Redis** (if not using Docker):
```bash
redis-server
```

3. **Run the server**:
```bash
python -m app.main
```

## 📖 API Documentation

### Base URL
- REST API: `http://localhost:8000/api/v1`
- WebSocket: `ws://localhost:8765`

### Authentication
Currently no authentication required. In production, implement JWT or API key authentication.

### Core Endpoints

#### Teaching Metadata Management

**Create Teaching Mode**
```bash
curl -X POST http://localhost:8000/api/v1/teaching-modes \
  -H "Content-Type: application/json" \
  -d '{
    "code": "BEGINNER_GUIDED",
    "name": "Beginner (Guided)",
    "description": "Structured practice with hints",
    "rubric": {
      "weights": {"fluency": 0.25, "vocabulary": 0.25, "grammar": 0.25, "pronunciation": 0.25},
      "scales": {"min": 0, "max": 5}
    }
  }'
```

**Get Teaching Modes**
```bash
curl http://localhost:8000/api/v1/teaching-modes
```

**Create Scenario**
```bash
curl -X POST http://localhost:8000/api/v1/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "mode_code": "conversation",
    "title": "Airport Check-in",
    "prompt": "You are at an airport checking in for your flight. Practice the conversation.",
    "language_code": "en",
    "metadata": {"level": "intermediate"}
  }'
```

**Create Language**
```bash
curl -X POST http://localhost:8000/api/v1/languages \
  -H "Content-Type: application/json" \
  -d '{
    "code": "fr-FR",
    "label": "French (France)",
    "level_cefr": "B2"
  }'
```

#### Session Management

**Open Session**
```bash
curl -X POST http://localhost:8000/api/v1/sessions/open \
  -H "Content-Type: application/json" \
  -d '{
    "user_external_id": "user_123",
    "mode_code": "conversation",
    "language_code": "en",
    "metadata": {"user_level": "intermediate"}
  }'
```

**Get Session**
```bash
curl http://localhost:8000/api/v1/sessions/{session_id}
```

**Close Session**
```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/close
```

#### Conversation Management

**Add Turn**
```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/turns \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "text": "Hello, I would like to practice my English conversation skills."
  }'
```

**Get Conversation History**
```bash
curl "http://localhost:8000/api/v1/sessions/{session_id}/turns?page=1&page_size=20"
```

**Search Conversations**
```bash
curl "http://localhost:8000/api/v1/conversations/search?user_external_id=user_123&text_search=practice"
```

#### Summary Management

**Get Summaries**
```bash
curl "http://localhost:8000/api/v1/summaries?user_external_id=user_123&page=1&page_size=20"
```

**Get Session Summary**
```bash
curl http://localhost:8000/api/v1/sessions/{session_id}/summary
```

### WebSocket API

**Connect to WebSocket**
```javascript
const ws = new WebSocket('ws://localhost:8765');

// Send welcome message
ws.onopen = () => {
  console.log('Connected to voice learning server');
};

// Start session
ws.send(JSON.stringify({
  type: 'start_session',
  user_external_id: 'user_123',
  mother_language: 'spanish',
  target_language: 'english',
  user_level: 'intermediate',
  teaching_mode: 'conversation',
  scenario_id: 'restaurant'
}));

// Send audio data
ws.send(JSON.stringify({
  type: 'audio',
  data: base64AudioData
}));

// End session
ws.send(JSON.stringify({
  type: 'end_session'
}));
```

**WebSocket Message Types**

**Incoming Messages**:
- `welcome` - Connection established
- `session_started` - Session ready
- `audio` - AI response audio
- `transcription` - Speech transcription
- `feedback` - Language scoring feedback
- `turn_complete` - Turn finished
- `session_ended` - Session closed with summary

**Outgoing Messages**:
- `start_session` - Initialize learning session
- `audio` - Send audio data (base64 PCM)
- `end_session` - Close session
- `get_teaching_modes` - Request available modes
- `get_languages` - Request supported languages
- `get_scenarios` - Request available scenarios

## 🔧 Configuration

### Teaching Mode Configuration

Teaching modes define the focus and scoring rubric for learning sessions:

```json
{
  "code": "grammar_intensive",
  "name": "Grammar Intensive",
  "description": "Focus heavily on grammatical accuracy",
  "rubric": {
    "weights": {
      "fluency": 0.15,
      "vocabulary": 0.20,
      "grammar": 0.50,
      "pronunciation": 0.15
    },
    "scales": {
      "min": 0,
      "max": 5
    },
    "guidelines": {
      "grammar": "Strict focus on grammatical correctness",
      "vocabulary": "Appropriate word choice for context",
      "fluency": "Natural speech flow",
      "pronunciation": "Clear articulation"
    }
  }
}
```

### Scoring System

Each user turn is automatically scored based on:

- **Fluency** (0-5): Speech flow, hesitations, natural rhythm
- **Vocabulary** (0-5): Word variety, appropriateness, range
- **Grammar** (0-5): Sentence structure, rule compliance
- **Pronunciation** (0-5): Clarity, stress patterns, intonation

**Total Score**: Weighted average normalized to 0-100 scale

### Summary Schema

Learning summaries follow this exact structure:

```json
{
  "title": "Session abc123 Study Notes — English (Conversation)",
  "subtitle": {
    "0": {
      "heading": "Key Phrases Practiced",
      "points": {
        "0": "Hello, how are you?",
        "1": "I'm fine, thank you",
        "2": "What's your name?"
      }
    },
    "1": {
      "heading": "Grammar & Corrections",
      "points": {
        "0": "Use 'I am' instead of 'I'm' in formal settings",
        "1": "Remember subject-verb agreement",
        "2": "Practice question formation"
      }
    },
    "2": {
      "heading": "Pronunciation / Fluency Tips",
      "points": {
        "0": "Work on 'th' sound pronunciation",
        "1": "Practice word stress patterns",
        "2": "Reduce speech hesitations"
      }
    },
    "3": {
      "heading": "Next Steps",
      "points": {
        "0": "Practice daily conversations",
        "1": "Focus on question formation",
        "2": "Continue pronunciation work"
      }
    }
  }
}
```

## 🐳 Docker Configuration

### Services

- **voice-server**: Main application (API + WebSocket)
- **redis**: Session storage and caching

### Ports

- `8765`: WebSocket server
- `8766`: Health check endpoint
- `8000`: REST API server
- `6379`: Redis (internal only)

### Health Checks

- Database connectivity
- Redis connectivity
- WebSocket server status
- Service dependency health

## 📊 Monitoring & Logging

### Structured Logging

All services use structured logging with:
- Request/response logging
- Performance metrics
- Error tracking
- User activity monitoring

### Health Endpoints

**Application Health**
```bash
curl http://localhost:8766/health
```

**Service Status**
```bash
curl http://localhost:8000/status
```

### Metrics Available

- Active session count
- Total conversations logged
- Average scoring metrics
- Session duration statistics
- Error rates by endpoint

## 🚀 Production Deployment

### Environment Considerations

1. **Database**: Use managed Supabase in production
2. **Redis**: Use managed Redis service (AWS ElastiCache, etc.)
3. **Secrets**: Use proper secret management
4. **Scaling**: Consider horizontal scaling for API servers
5. **Load Balancing**: Implement proper load balancing for WebSocket connections

### Security Checklist

- [ ] Implement authentication (JWT/API keys)
- [ ] Add rate limiting
- [ ] Enable HTTPS/WSS
- [ ] Validate all inputs
- [ ] Implement CORS properly
- [ ] Use environment-specific secrets
- [ ] Enable audit logging

### Performance Optimization

- Use connection pooling for database
- Implement caching strategies
- Optimize audio buffer sizes
- Monitor memory usage for voice sessions
- Use CDN for static assets

## 🧪 Testing

### Unit Tests
```bash
pytest tests/unit/
```

### Integration Tests
```bash
pytest tests/integration/
```

### Load Testing
```bash
# Use your preferred load testing tool
# Test WebSocket connections, API endpoints, and concurrent sessions
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## 📄 License

[Add your license here]

## 🆘 Troubleshooting

### Common Issues

**Connection Refused**
- Check if Redis is running
- Verify Supabase credentials
- Confirm network connectivity

**Audio Issues**
- Verify audio format (PCM, 16kHz)
- Check WebSocket connection
- Confirm Gemini API key

**Database Errors**
- Run schema migration
- Check Supabase service status
- Verify service role key permissions

**Performance Issues**
- Monitor Redis memory usage
- Check database connection pool
- Review active session counts

### Debug Mode

Enable debug logging:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

### Support

For issues and questions:
1. Check the logs for error details
2. Verify environment configuration
3. Test individual service components
4. Review API documentation

---

**Built with ❤️ for language learners worldwide**