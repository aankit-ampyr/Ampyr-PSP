# AI Integration Plan: BESS Sizing Tool

## Overview

Integrate Anthropic Claude API to provide intelligent configuration recommendations across the wizard workflow. The AI layer will analyze user inputs, solar/load profiles, and constraints to suggest optimal configurations at each step.

---

## Architecture

```
src/ai/
├── __init__.py           # Package exports
├── client.py             # Claude API wrapper with retry/caching
├── context.py            # Build context from wizard state
├── prompts.py            # System prompts and templates
├── recommendations.py    # Recommendation logic per step
└── cache.py              # Response caching for cost control
```

---

## Phase 1: Foundation (AI Infrastructure)

### 1.1 Claude API Client (`src/ai/client.py`)

```python
"""
Claude API client with:
- Retry logic with exponential backoff
- Rate limiting (respect API limits)
- Response caching (identical queries)
- Cost tracking (token usage)
- Graceful fallback when API unavailable
"""

Features:
- get_recommendation(context, prompt_type) → structured recommendation
- get_explanation(topic, context) → natural language explanation
- get_analysis(results, context) → results interpretation
- estimate_cost(prompt) → token cost estimate
```

### 1.2 Context Builder (`src/ai/context.py`)

```python
"""
Build structured context from wizard state for AI prompts.
Extracts relevant data without exposing full session state.
"""

def build_step1_context(wizard_state) -> dict:
    """Load profile, solar profile stats, BESS parameters"""

def build_step2_context(wizard_state) -> dict:
    """DG config, timing constraints, current template"""

def build_step3_context(wizard_state) -> dict:
    """Sizing range, duration classes, load/solar summary"""

def build_results_context(results_df, selected_config) -> dict:
    """Metrics, comparisons, trade-offs"""
```

### 1.3 Prompt Templates (`src/ai/prompts.py`)

System prompts that establish Claude as a BESS domain expert:

```python
SYSTEM_PROMPT = """
You are an expert Battery Energy Storage System (BESS) sizing consultant.
You help users configure solar+storage systems for optimal performance.

Domain knowledge:
- Binary delivery constraint: Either deliver full target MW or nothing
- Cycle limits: Typically 1-2 cycles/day to preserve battery life
- SOC bounds: Maintain 5-95% for battery health
- Efficiency: ~87% round-trip, losses on charge and discharge
- Templates T0-T6: Different DG integration strategies

Always provide:
1. Clear recommendation with confidence level
2. Brief rationale (1-2 sentences)
3. Key trade-offs to consider
"""
```

---

## Phase 2: Recommendation Features

### 2.1 Step 1: Setup Recommendations

#### Load Profile Recommender

**Trigger:** User describes their site or use case

**Input Context:**
- User description (free text)
- Available load patterns
- Peak load requirement

**Output:**
```json
{
  "recommended_pattern": "day_only",
  "confidence": "high",
  "parameters": {
    "start_hour": 6,
    "end_hour": 18,
    "load_mw": 25
  },
  "rationale": "Industrial operations typically run during daylight hours, aligning with solar availability.",
  "alternatives": ["constant", "custom_windows"]
}
```

**UI Integration:**
- Text input: "Describe your site (optional)"
- AI suggestion appears below load pattern selector
- "Apply Suggestion" button auto-fills parameters

#### BESS Parameter Advisor

**Trigger:** User adjusts efficiency, SOC limits, or cycle limits

**Input Context:**
- Current parameter values
- Load profile summary
- Solar profile summary

**Output:**
```json
{
  "parameter": "cycle_limit",
  "current_value": 1.0,
  "suggested_value": 1.5,
  "rationale": "Your load profile has evening peaks. Allowing 1.5 cycles/day enables afternoon charging and evening discharge.",
  "impact": "Increases delivery hours by ~200/year, reduces battery life by ~5%"
}
```

**UI Integration:**
- Info icon next to each parameter
- Click reveals AI explanation
- "Optimize for my profile" button suggests all parameters

---

### 2.2 Step 2: Dispatch Rules Recommendations

#### Template Recommender

**Trigger:** User completes DG configuration questions

**Input Context:**
- DG enabled/disabled
- Timing constraints (blackout windows)
- Trigger preferences (reactive, SoC-based, proactive)
- Priority preferences (BESS-first vs DG-first)

**Output:**
```json
{
  "recommended_template": "T3",
  "confidence": "high",
  "rationale": "Your blackout window (22:00-06:00) and reactive DG trigger maps to Template T3: DG available during day, BESS covers night independently.",
  "template_summary": {
    "merit_order": ["Solar", "BESS", "DG", "Unserved"],
    "dg_behavior": "Reactive, day-only",
    "battery_charging": "Solar only"
  },
  "considerations": [
    "Night-only load will rely entirely on BESS stored energy",
    "Consider sizing BESS for 12+ hours of autonomy"
  ]
}
```

**UI Integration:**
- After answering all questions, show recommended template
- Compare user's answers vs. recommended template
- Explain any mismatches

#### Rule Explainer

**Trigger:** User hovers/clicks on a dispatch rule option

**Input Context:**
- Specific rule being explained
- Current configuration

**Output:**
Natural language explanation of what the rule means and its implications.

---

### 2.3 Step 3: Sizing Range Recommendations

#### Smart Range Suggester

**Trigger:** User enters Step 3 or clicks "Suggest Range"

**Input Context:**
- Load profile (8760 hours summarized)
- Solar profile (8760 hours summarized)
- BESS parameters (efficiency, SOC limits, cycles)
- Dispatch template selected

**Analysis Performed:**
1. Calculate minimum BESS to cover largest solar-gap period
2. Estimate maximum useful BESS (diminishing returns threshold)
3. Recommend duration classes based on load pattern

**Output:**
```json
{
  "recommended_range": {
    "min_mwh": 100,
    "max_mwh": 300,
    "step_mwh": 10
  },
  "recommended_durations": [2, 4],
  "rationale": "Your 25 MW constant load with 67 MW peak solar suggests 4-hour storage. Range 100-300 MWh covers 80-95% delivery scenarios.",
  "estimated_simulations": 42,
  "estimated_time": "~30 seconds",
  "insights": [
    "Below 100 MWh: Delivery drops below 80%",
    "Above 300 MWh: <50 hours improvement per 50 MWh added"
  ]
}
```

**UI Integration:**
- "AI Suggest" button next to range inputs
- Shows recommended values with "Apply" option
- Explains why the range was chosen

---

### 2.4 Step 4: Results Interpretation

#### Configuration Interpreter

**Trigger:** Results loaded, top configuration displayed

**Input Context:**
- All simulation results (DataFrame)
- Top recommended configuration
- User's original requirements

**Output:**
```json
{
  "summary": "The 200 MWh / 4-hour system achieves 97.2% delivery with balanced trade-offs.",
  "strengths": [
    "Meets load 8,515 of 8,760 hours (97.2%)",
    "Low cycling stress: 180 equivalent cycles/year",
    "Solar utilization: 89%"
  ],
  "considerations": [
    "245 unserved hours concentrated in winter evenings",
    "Adding 50 MWh recovers 180 hours but costs ~$7.5M"
  ],
  "comparison_to_alternatives": "Next-best option (250 MWh) improves delivery by 2% at 25% higher cost.",
  "recommendation": "This configuration balances cost and reliability. Consider overbuild strategy for Year 10+ performance."
}
```

**UI Integration:**
- AI Analysis card below recommended configuration
- Expandable sections for strengths/considerations
- "Explain Further" for deeper analysis

#### Trade-off Analyzer

**Trigger:** User selects configurations to compare

**Input Context:**
- Selected configurations (2-3)
- Key metrics for each

**Output:**
Natural language comparison highlighting:
- Which is better for reliability
- Which is better for cost
- Which has lower degradation
- Recommended choice with rationale

---

## Phase 3: Interactive Assistant

### 3.1 Chat Interface

**Location:** Collapsible sidebar panel or floating button

**Capabilities:**
- Answer questions about BESS concepts
- Explain current configuration
- Suggest optimizations
- Run what-if scenarios

**Example Interactions:**

```
User: "Why is my delivery rate only 85%?"
AI: "Your 150 MWh battery cannot bridge the 6-hour evening gap
     when solar drops to 5 MW. The load requires 25 MW for 6 hours
     = 150 MWh, but after efficiency losses you only have 130 MWh
     usable. Consider 200 MWh or reducing evening load."

User: "What if I allow DG to charge the battery?"
AI: "Enabling DG→BESS charging would shift ~400 hours from
     DG-direct delivery to green delivery. Daily cycles increase
     by 0.3. Net effect: greener operation with slightly faster
     degradation. Shall I update your dispatch rules?"
```

---

## Implementation Details

### API Configuration

```python
# Environment variables
ANTHROPIC_API_KEY=sk-ant-...
AI_MODEL=claude-3-5-sonnet-20241022  # or claude-3-5-haiku for cost savings
AI_CACHE_TTL=3600  # Cache responses for 1 hour
AI_MAX_TOKENS=1024  # Limit response length
AI_TEMPERATURE=0.3  # Lower for consistent recommendations
```

### Cost Control Strategy

| Feature | Model | Est. Cost/Call | Caching |
|---------|-------|----------------|---------|
| Load profile recommendation | Haiku | $0.001 | Yes |
| Template recommendation | Haiku | $0.001 | Yes |
| Sizing range suggestion | Sonnet | $0.01 | Yes |
| Results interpretation | Sonnet | $0.02 | Yes |
| Chat responses | Sonnet | $0.01 | No |

**Estimated monthly cost:** $10-50 for typical usage (100-500 analyses/month)

### Caching Strategy

```python
def get_cache_key(context: dict, prompt_type: str) -> str:
    """Generate cache key from relevant context fields."""
    # Only include fields that affect the recommendation
    relevant = {
        "load_pattern": context.get("load_pattern"),
        "solar_capacity": context.get("solar_capacity"),
        "bess_efficiency": context.get("bess_efficiency"),
        # ... other relevant fields
    }
    return hashlib.md5(json.dumps(relevant, sort_keys=True).encode()).hexdigest()
```

### Error Handling

```python
def get_recommendation_with_fallback(context, prompt_type):
    try:
        return ai_client.get_recommendation(context, prompt_type)
    except RateLimitError:
        return {"error": "AI service busy. Try again in a moment."}
    except APIError:
        return {"error": "AI service unavailable. Using default recommendations."}
    except Exception as e:
        log_error(e)
        return get_rule_based_fallback(context, prompt_type)
```

---

## UI/UX Design

### AI Suggestion Cards

```
┌─────────────────────────────────────────────────┐
│ 🤖 AI Recommendation                            │
├─────────────────────────────────────────────────┤
│ Based on your 25 MW constant load and solar     │
│ profile, I recommend:                           │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ 📊 Sizing Range: 150-250 MWh               │ │
│ │ ⏱️  Duration: 4-hour                        │ │
│ │ 🔋 Step Size: 10 MWh                        │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ This range covers 90-98% delivery scenarios.    │
│ [Apply Suggestion]  [Explain More]              │
└─────────────────────────────────────────────────┘
```

### Inline Hints

```
Load Pattern: [Day Only ▾]  💡 "Matches your industrial profile"
                              └─ AI-generated contextual hint
```

### Results Insights Panel

```
┌─────────────────────────────────────────────────┐
│ 📊 AI Analysis                                  │
├─────────────────────────────────────────────────┤
│ ✅ This 200 MWh system achieves 97% delivery    │
│                                                 │
│ Key Insights:                                   │
│ • Only 245 unserved hours (winter evenings)     │
│ • Solar utilization: 89% (11% curtailed)        │
│ • Battery stress: Low (180 cycles/year)         │
│                                                 │
│ 💡 Recommendation: Solid choice. Consider       │
│    overbuild strategy for 10+ year operation.   │
│                                                 │
│ [View Detailed Analysis]                        │
└─────────────────────────────────────────────────┘
```

---

## File Structure After Implementation

```
src/
├── ai/
│   ├── __init__.py
│   ├── client.py           # Claude API wrapper
│   ├── context.py          # Context builders
│   ├── prompts.py          # System prompts
│   ├── recommendations.py  # Recommendation logic
│   ├── insights.py         # Results analysis
│   └── cache.py            # Response caching
├── config.py
├── dispatch_engine.py
├── wizard_state.py
└── ...

pages/
├── 8_🚀_Step1_Setup.py     # + AI load profile recommender
├── 9_📋_Step2_Rules.py     # + AI template recommender
├── 10_📐_Step3_Sizing.py   # + AI range suggester
├── 11_📊_Step4_Results.py  # + AI results interpreter
└── ...

components/
└── ai_panel.py             # Reusable AI suggestion component
```

---

## Testing Strategy

### Unit Tests
- Test context builders with various wizard states
- Test prompt formatting
- Test cache key generation
- Test fallback behavior

### Integration Tests
- Mock Claude API responses
- Test full recommendation flow
- Test error handling paths

### Manual Testing
- Verify recommendations make domain sense
- Check UI rendering of AI suggestions
- Test with edge cases (empty profiles, extreme values)

---

## Rollout Plan

### Week 1: Foundation
- [ ] Set up `src/ai/` package structure
- [ ] Implement Claude API client with retry/caching
- [ ] Create context builders for each step
- [ ] Define system prompts

### Week 2: Step 1 & 2 Recommendations
- [ ] Load profile recommender
- [ ] BESS parameter advisor
- [ ] Template recommender
- [ ] Rule explainer

### Week 3: Step 3 & 4 Recommendations
- [ ] Smart sizing range suggester
- [ ] Results interpreter
- [ ] Trade-off analyzer

### Week 4: Polish & Testing
- [ ] UI components for AI suggestions
- [ ] Error handling and fallbacks
- [ ] Cost monitoring
- [ ] Documentation

---

## Future Enhancements

1. **Learning from feedback**: Track which recommendations users accept/reject
2. **Custom prompts**: Let advanced users customize AI behavior
3. **Batch analysis**: Generate reports for multiple configurations
4. **Export AI insights**: Include AI analysis in PDF/Excel exports
5. **Multi-language**: Support prompts in other languages
