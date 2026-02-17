import asyncio
import re, os
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List
from uuid import uuid4
from openai import OpenAI
from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

# ASI1 API Configuration
ASI1_API_KEY = os.getenv("ASI1_API_KEY")
client = OpenAI(
    api_key=ASI1_API_KEY,
    base_url="https://api.asi1.ai/v1"
)

# Initialize the chat protocol with the standard chat spec
chat_proto = Protocol(spec=chat_protocol_spec)


# ============== Session Storage Functions ==============

def get_session_key(sender: str, session_id: str) -> str:
    return f"session:{sender}:{session_id}"


def get_session_data(ctx: Context, sender: str, session_id: str) -> Dict[str, Any]:
    key = get_session_key(sender, session_id)
    if ctx.storage.has(key):
        data = ctx.storage.get(key)
        if isinstance(data, dict):
            ctx.logger.info(f"Loaded session: {session_id}, {len(data.get('history', []))} messages")
            return data

    ctx.logger.info(f"Creating new session: {session_id}")
    return {
        "history": [],
        "state": {
            "greeted": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "current_phase": "intake",
            "fitness_profile": {},
            "goals": [],
            "workout_plan": {},
            "meal_plan": {},
            "progress_log": []
        }
    }


def save_session_data(ctx: Context, sender: str, session_id: str, session_data: Dict[str, Any]) -> None:
    key = get_session_key(sender, session_id)
    session_data["state"]["updated_at"] = datetime.now(timezone.utc).isoformat()
    ctx.storage.set(key, session_data)
    ctx.logger.info(f"Saved session: {session_id}, {len(session_data.get('history', []))} messages")


def add_to_history(history: List[Dict], role: str, content: str) -> List[Dict]:
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return history


def build_context_summary(history: List[Dict], max_messages: int = 20) -> str:
    if not history:
        return ""
    recent = history[-max_messages:] if len(history) > max_messages else history
    lines = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg['content'][:500] + "..." if len(msg['content']) > 500 else msg['content']
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def extract_text(msg: ChatMessage) -> str:
    for item in msg.content:
        if isinstance(item, TextContent):
            return item.text
    return ""


def create_text_chat(text: str, end_session: bool = False) -> ChatMessage:
    content: list = [TextContent(type="text", text=text)]
    if end_session:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=content,
    )


# ============== System Prompt (Planner Mode) ==============

SYSTEM_PROMPT = """You are a certified Fitness Goal Planner powered by AI planning capabilities. You guide users through a structured, multi-phase fitness journey using ONLY your planning and reasoning abilities — no web search.

## YOUR 5-PHASE PLANNING PIPELINE:

### Phase 1: FITNESS ASSESSMENT
Gather and assess the user's current fitness level:
- Age, gender, height, weight, BMI estimate
- Current activity level (sedentary / lightly active / moderately active / very active)
- Exercise history and experience
- Any injuries, medical conditions, or limitations
- Available equipment (gym, home, bodyweight only)
- Time available per day/week for workouts

### Phase 2: SMART GOAL SETTING
Help the user define goals that are:
- **S**pecific: "Lose 5kg of body fat" not "lose weight"
- **M**easurable: Trackable metrics (weight, reps, distance, body measurements)
- **A**chievable: Realistic based on their assessment
- **R**elevant: Aligned with their lifestyle and motivation
- **T**ime-bound: Clear deadlines (4-week, 8-week, 12-week milestones)

### Phase 3: WEEKLY WORKOUT SPLIT
Design a personalized weekly training program:
- Push/Pull/Legs, Upper/Lower, Full Body, or Bro Split based on experience
- Exercise selection with sets × reps × rest periods
- Progressive overload strategy
- Warm-up and cool-down routines
- Cardio integration (LISS, HIIT, or hybrid)
- Rest day scheduling and active recovery

### Phase 4: MEAL PLANNING
Create a nutrition framework:
- Calculate TDEE (Total Daily Energy Expenditure) estimate
- Macro split (protein/carbs/fats) based on goal (cut/bulk/recomp)
- Sample meal templates for each day type (training vs rest)
- Pre-workout and post-workout nutrition timing
- Hydration guidelines
- Supplement suggestions (if appropriate)

### Phase 5: PROGRESS TRACKING
Set up a monitoring system:
- Weekly check-in metrics (weight, measurements, photos)
- Workout log format (track progressive overload)
- When to adjust the plan (plateaus, overtraining signs)
- Milestone celebrations and plan adjustments
- Deload week scheduling

## INTERACTION RULES:
1. Start by asking which phase the user wants to begin with, or start from Phase 1
2. Ask focused questions — don't overwhelm with everything at once
3. After each phase, summarize what was planned and ask to proceed to the next
4. Adapt recommendations based on ALL previously gathered information
5. Use evidence-based fitness principles (no fads or dangerous advice)
6. Be encouraging but realistic — set expectations properly
7. If the user asks about a specific phase, jump directly to it while noting dependencies
8. For follow-up sessions, reference their existing profile and plans

## OUTPUT FORMAT:
- Use clear headers and bullet points
- For workout plans, use table-like formatting:
  **Day 1 — Push (Chest/Shoulders/Triceps)**
  | Exercise | Sets | Reps | Rest |
  |----------|------|------|------|
  | Bench Press | 4 | 8-10 | 90s |
- For meal plans, include approximate macros
- Always end responses with a clear next step or question

## IMPORTANT:
- Never recommend extreme caloric deficits (below BMR)
- Always suggest consulting a doctor for medical conditions
- Adjust intensity for beginners — safety first
- Provide alternatives for exercises when equipment is limited
- All advice is based on general fitness principles, not medical advice"""


# ============== Query Classification ==============

def classify_query(query: str, history: List[Dict]) -> Dict[str, Any]:
    query_lower = query.lower().strip()
    query_clean = re.sub(r'@agent1q\w+', '', query_lower).strip()

    classification = {
        "type": "general",
        "phase": None,
        "is_followup": len(history) > 0,
        "needs_planning": True
    }

    # Phase detection patterns
    phase_patterns = {
        "assessment": [
            "assess", "fitness level", "current fitness", "starting point",
            "how fit am i", "my stats", "bmi", "body composition",
            "evaluate", "baseline", "fitness test"
        ],
        "goals": [
            "goal", "smart goal", "target", "objective", "aim",
            "want to lose", "want to gain", "want to build",
            "lose weight", "gain muscle", "get stronger", "get lean",
            "bulk", "cut", "recomp", "body recomposition"
        ],
        "workout": [
            "workout", "exercise", "training", "split", "routine",
            "push pull", "upper lower", "full body", "gym plan",
            "program", "schedule", "sets", "reps", "cardio",
            "hiit", "strength training", "resistance"
        ],
        "meal": [
            "meal", "diet", "nutrition", "food", "eat", "calories",
            "macro", "protein", "carb", "fat", "tdee", "meal prep",
            "supplement", "pre workout", "post workout", "hydration"
        ],
        "progress": [
            "progress", "track", "measure", "check-in", "plateau",
            "adjust", "deload", "overtraining", "milestone",
            "not seeing results", "stuck", "update my plan"
        ]
    }

    for phase, patterns in phase_patterns.items():
        for pattern in patterns:
            if pattern in query_clean:
                classification["phase"] = phase
                classification["type"] = f"phase_{phase}"
                return classification

    # Context analysis patterns (use conversation history, no new planning needed)
    context_patterns = [
        "summarize", "summary", "explain", "why", "how does",
        "what did you", "repeat", "show again", "recap",
        "from before", "you said", "earlier"
    ]
    for pattern in context_patterns:
        if pattern in query_clean:
            classification["type"] = "context_analysis"
            classification["needs_planning"] = False
            return classification

    return classification


# ============== Context Analysis (No Planning Needed) ==============

CONTEXT_ANALYSIS_PROMPT = """You are a helpful fitness planning assistant reviewing conversation history.

Answer the user's question based ONLY on information already discussed in the conversation.
Do NOT create new plans or recommendations — just reference what was already provided.
Be specific and reference actual details from previous messages."""


async def analyze_context(query: str, history: List[Dict]) -> str:
    messages = [{"role": "system", "content": CONTEXT_ANALYSIS_PROMPT}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    clean_query = re.sub(r'@agent1q\w+\s*', '', query).strip()
    messages.append({
        "role": "user",
        "content": f"Based on our conversation so far, please answer: {clean_query}"
    })

    try:
        response = client.chat.completions.create(
            model="asi1",
            messages=messages,
            temperature=0.3,
            top_p=0.9,
            max_tokens=3000,
            stream=False,
            extra_body={"planner_mode": True}
        )
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content
        return "I couldn't find the information in our conversation. Could you rephrase?"
    except Exception:
        return "An error occurred while reviewing our conversation. Please try again."


# ============== Fitness Planning Function (Planner Mode) ==============

async def plan_fitness_response(query: str, history: List[Dict], state: Dict[str, Any]) -> str:
    classification = classify_query(query, history)

    # If it's a context query, just analyze history
    if classification["type"] == "context_analysis":
        return await analyze_context(query, history)

    # Build messages with system prompt and history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history for continuity
    for msg in history[-16:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"][:1500]
        })

    # Clean query
    clean_query = re.sub(r'@agent1q\w+\s*', '', query).strip()

    # Build phase-aware query
    phase = classification.get("phase")
    if phase:
        phase_context = build_phase_query(clean_query, phase, state)
    else:
        phase_context = build_general_query(clean_query, state)

    messages.append({"role": "user", "content": phase_context})

    try:
        response = client.chat.completions.create(
            model="asi1",
            messages=messages,
            temperature=0.4,
            top_p=0.9,
            max_tokens=2000,
            presence_penalty=0.1,
            frequency_penalty=0.1,
            stream=False,
            extra_body={"planner_mode": True, "web_search": False}
        )
        if response.choices and len(response.choices) > 0:
            result = response.choices[0].message.content

            # Update state phase tracking
            if phase:
                state["current_phase"] = phase

            return result
        return "I couldn't generate a fitness plan for that. Please try rephrasing your request."
    except asyncio.TimeoutError:
        return "Planning is taking longer than expected. Try a more specific question."
    except Exception:
        return "An unexpected error occurred. Please try again."


def build_phase_query(query: str, phase: str, state: Dict[str, Any]) -> str:
    current_phase = state.get("current_phase", "intake")
    profile = state.get("fitness_profile", {})

    profile_summary = ""
    if profile:
        profile_summary = f"\n**Known User Profile:** {profile}"

    phase_instructions = {
        "assessment": f"""The user wants to work on their FITNESS ASSESSMENT (Phase 1).
{profile_summary}
Ask targeted questions to build their fitness profile. Gather: age, gender, height, weight, activity level, exercise history, injuries/limitations, available equipment, and time availability.
If some info is already known, skip those questions.""",

        "goals": f"""The user wants to SET FITNESS GOALS (Phase 2).
{profile_summary}
Help them define SMART goals. Use their assessment data to make goals realistic. Suggest specific, measurable targets with timeframes.""",

        "workout": f"""The user wants a WORKOUT PLAN (Phase 3).
{profile_summary}
Design a weekly training split appropriate for their level and goals. Include exercises, sets, reps, rest periods, and progressive overload strategy.""",

        "meal": f"""The user wants a MEAL PLAN (Phase 4).
{profile_summary}
Create a nutrition framework. Estimate TDEE, suggest macro splits, provide sample meal templates, and cover pre/post workout nutrition.""",

        "progress": f"""The user wants PROGRESS TRACKING guidance (Phase 5).
{profile_summary}
Set up their monitoring system: weekly metrics, workout logging, plateau identification, and plan adjustment criteria."""
    }

    instruction = phase_instructions.get(phase, "Respond helpfully to the user's fitness question.")

    return f"""**User Request:** {query}

**Phase:** {phase.upper()}
**Current Session Phase:** {current_phase}

{instruction}

Remember: Use planning and reasoning only — no web search. Provide evidence-based, safe fitness advice."""


def build_general_query(query: str, state: Dict[str, Any]) -> str:
    current_phase = state.get("current_phase", "intake")
    profile = state.get("fitness_profile", {})

    return f"""**User Request:** {query}

**Current Phase:** {current_phase}
**Known Profile:** {profile if profile else "Not yet collected"}

Respond helpfully. If this is a new user, guide them through Phase 1 (Assessment) first.
If they have an existing profile, continue from where they left off.
Use planning and reasoning only — no web search."""


# ============== Chat Handlers ==============

@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    try:
        ctx.logger.info(f"Received message from {sender}")

        await ctx.send(
            sender,
            ChatAcknowledgement(
                timestamp=datetime.now(timezone.utc),
                acknowledged_msg_id=msg.msg_id,
            ),
        )

        session_id = str(ctx.session) if hasattr(ctx, "session") and ctx.session else f"{sender}_{int(datetime.now(timezone.utc).timestamp())}"
        ctx.logger.info(f"Session ID: {session_id}")

        session_data = get_session_data(ctx, sender, session_id)
        history = session_data["history"]
        state = session_data["state"]

        text = extract_text(msg)

        if not text:
            for item in msg.content:
                if isinstance(item, StartSessionContent):
                    ctx.logger.info(f"Session started with {sender}")
                    state["greeted"] = True
                    session_data["state"] = state
                    save_session_data(ctx, sender, session_id, session_data)

                    welcome_message = """Welcome to the Fitness Goal Planner Agent!

I'll guide you through a complete fitness planning journey using a structured 5-phase approach:

**Phase 1** — Fitness Assessment (your starting point)
**Phase 2** — SMART Goal Setting (where you want to go)
**Phase 3** — Weekly Workout Split (your training plan)
**Phase 4** — Meal Planning (your nutrition framework)
**Phase 5** — Progress Tracking (staying on track)

You can:
- Start from Phase 1 for a complete plan
- Jump to any phase directly (e.g., "create a workout plan")
- Ask follow-up questions anytime
- Request adjustments to any part of your plan

Let's begin! Tell me about yourself — what's your current fitness level, and what are you hoping to achieve?"""

                    await ctx.send(sender, create_text_chat(welcome_message))
                    return

                elif isinstance(item, EndSessionContent):
                    ctx.logger.info(f"Session ended with {sender}")
                    save_session_data(ctx, sender, session_id, session_data)
                    await ctx.send(
                        sender,
                        create_text_chat(
                            "Great session! Your fitness plan has been saved.\n"
                            "Come back anytime to adjust your plan or track progress.\n"
                            "Stay consistent and trust the process!",
                            end_session=True
                        )
                    )
                    return
            return

        ctx.logger.info(f"Query: {text[:100]}")

        history = add_to_history(history, "user", text)

        classification = classify_query(text, history[:-1])
        ctx.logger.info(f"Query classification: {classification['type']}, phase: {classification.get('phase')}")

        result = await plan_fitness_response(text, history[:-1], state)

        ctx.logger.info(f"Result: {result[:200]}")

        history = add_to_history(history, "assistant", result)

        session_data["history"] = history
        session_data["state"] = state
        save_session_data(ctx, sender, session_id, session_data)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                await ctx.send(sender, create_text_chat(result))
                ctx.logger.info(f"Sent response to {sender}")
                break
            except Exception as send_err:
                ctx.logger.warning(f"Send attempt {attempt + 1}/{max_retries} failed: {send_err}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    ctx.logger.error(f"All {max_retries} send attempts failed for {sender}")
                    raise

    except Exception as e:
        ctx.logger.error(f"Error in handle_message: {e}")
        ctx.logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            await ctx.send(
                sender,
                create_text_chat("Sorry, I encountered a technical issue. Please try again.")
            )
        except Exception as send_error:
            ctx.logger.error(f"Failed to send error message: {send_error}")


@chat_proto.on_message(ChatAcknowledgement)
async def handle_acknowledgement(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(
        f"Received acknowledgement from {sender} for message {msg.acknowledged_msg_id}"
    )
