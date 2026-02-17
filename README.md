## Fitness Goal Planner Agent

![tag:innovationlab](https://img.shields.io/badge/innovationlab-2E7DB5) ![tag:uagents](https://img.shields.io/badge/uagents-3776AB) ![tag:asi1](https://img.shields.io/badge/asi1-6366F1) ![tag:fetch--ai](https://img.shields.io/badge/fetch--ai-0EA5E9) ![tag:agentverse](https://img.shields.io/badge/agentverse-8B5CF6) ![tag:python](https://img.shields.io/badge/python-FFD43B) ![tag:fitness--goal--planner](https://img.shields.io/badge/fitness--goal--planner-22C55E) ![tag:llm](https://img.shields.io/badge/llm-F97316)

An AI-powered fitness planning agent built using the **uAgents** framework and **[ASI1 LLM](https://asi1.ai/)** in **planner mode** (no web search). This agent helps users build a realistic, personalized fitness plan through a structured 5-phase process: assessment → SMART goals → weekly workouts → meal planning → progress tracking.

### Features

- **5-Phase Fitness Planning Pipeline**: Guides users from baseline assessment to measurable goals and an actionable plan
- **Planner-Mode Reasoning (No Web Search)**: Uses ASI1 planning to generate consistent, evidence-based recommendations
- **Personalized Training Plan**: Builds a weekly workout split with sets × reps × rest and progressive overload guidance
- **Nutrition Framework**: Suggests calories/macros targets and meal templates aligned to the user’s goal (cut/bulk/recomp)
- **Session Memory**: Stores per-session history so follow-ups can refine plans instead of starting over
- **Chat Protocol Compatible**: Uses the standard uAgents chat protocol for Agentverse compatibility

### Project Structure

```
fitness-goal-planner-agent/
├── agent.py         # Agent setup, wallet funding, startup event, and entry point
├── protocol.py      # ASI1 client, planning logic, session storage, and chat protocol handlers
├── requirements.txt
└── README.md
```

- **`agent.py`** — Creates the uAgent, funds the wallet, logs agent details on startup, includes the chat protocol, and runs the agent.
- **`protocol.py`** — Defines the ASI1 client, the planner-mode system prompt, session memory helpers, and chat protocol message/acknowledgement handlers.

### How to Get Started

1. **Clone the repository**

```bash
git clone https://github.com/devcode8/asi1-fitness-goal-planner-agent
cd asi1-fitness-goal-planner-agent
```

2. **Install the required dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure API Key**

- Get your ASI1 API key from [ASI1](https://asi1.ai)
- Create a `.env` file in the project directory and add your key:

```
ASI1_API_KEY=your_asi1_api_key_here
```

4. **Run the agent**

```bash
python agent.py
```

5. **Open the Agent Inspector**

After running the agent, you should see something similar in your terminal output:

```
INFO:     [fitness_goal_planner_agent]: Starting agent with address: agent1...
INFO:     [fitness_goal_planner_agent]: Agent inspector available at https://Agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8011&address=agent1...
INFO:     [fitness_goal_planner_agent]: Starting server on http://0.0.0.0:8011 (Press CTRL+C to quit)
INFO:     [fitness_goal_planner_agent]: Starting mailbox client for https://Agentverse.ai
...
```

Click the **Agent Inspector URL** from the terminal output to open the Inspector UI in your browser.

6. **Publish your agent on Agentverse (Optional)**

To publish the agent details (and link the README) on Agentverse, set a `readme_path` while defining the agent:

```python
agent = Agent(
    name="fitness_goal_planner_agent",
    port=8011,
    mailbox=True,
    publish_agent_details=True,
    readme_path="README.md",
)
```

> **Warning: Local Network Access Permission (Chrome Update)**
>
> Recent Chrome (v142+) and Brave updates introduced a Local Network Access permission prompt. If this permission is not granted, the browser cannot detect locally running agents.
>
> **Solution:** When prompted with "Allow this site to access devices on your local network", click **Allow**. If you missed the prompt, you can manually enable it in: Chrome Settings → Privacy and Security → Site Settings → Additional permissions → Local network access.
>
> **If you see "Could not find this Agent on your local host."** (Brave or any other browser): disable your browser’s shield (e.g. Brave Shields) or any site blocker / ad blocker for this site, then reload and try again.
>
> Reference: [Chrome For Developers Blog – Local Network Access Update](https://developer.chrome.com/blog/local-network-access-update)

7. **Create a Mailbox in Agentverse**

Now that your local Agent is running, you can connect it to Agentverse via a Mailbox:

1. Make sure your Agent is running
2. Click on the **Local Agent Inspector URL** provided in your terminal output — you will be redirected to the Inspector UI where you can see details about this local Agent
3. Click the **Connect** button

![Mailbox Connect](https://innovationlab.fetch.ai/resources/assets/images/mailbox-connect-1de25d2539f6f386fe2b17fb777ee8cb.png)

4. You will be presented with 3 choices: **Mailbox**, **Proxy**, and **Custom** — select **Mailbox**

![Mailbox Options](https://innovationlab.fetch.ai/resources/img/uagents/mailbox-options.png)

![Mailbox Done](https://innovationlab.fetch.ai/resources/img/uagents/mailbox-done.png)

5. You will see some code details for the Agent — you do not need to do anything, just click **Finish**

### View your Agent on Agentverse

Once you connect your Agent via Mailbox, click on **Agent Profile** and navigate to the **Overview** section of the Agent. Your Agent will appear under local agents on Agentverse.

![Agent Profile](https://innovationlab.fetch.ai/resources/assets/images/agent-profile-ad2d027033e8cf9d7f1e75c0728f480f.png)

### Chat with your Agent on ASI1 UI

Click the **Chat with Agent** button to start chatting with your agent on the ASI1 UI.

![Chat with Agent](https://res.cloudinary.com/doesqlfyi/image/upload/v1771323333/Screenshot_2026-02-17_at_3.45.25_PM_gvxiuq.png)

![ASI1 UI](https://res.cloudinary.com/doesqlfyi/image/upload/v1771323453/Screenshot_2026-02-17_at_3.47.21_PM_pvwbwx.png)

### Usage

Once the agent is running, it registers on the uAgents network and can be interacted with via the chat protocol. You can connect to it through Agentverse (Inspector) or any compatible uAgents client.

Send a message like:

```
I’m 29, 178cm, 86kg. I can train 4 days/week at a gym. My goal is to lose fat while maintaining muscle over 12 weeks.
```

The agent will guide you through:

```
Phase 1: Fitness Assessment
Phase 2: SMART Goal Setting
Phase 3: Weekly Workout Split
Phase 4: Meal Planning
Phase 5: Progress Tracking
```

**Example prompts:**
- "Start with Phase 1 — here are my stats and injuries…"
- "Help me set a SMART goal for a 12-week fat loss plan."
- "Build me a 3-day full-body workout split with progressive overload."
- "Estimate my calories/macros and give a simple meal template."
- "Create a weekly check-in plan and how to adjust if I plateau."

### Sample Chat


![Sample Chat](https://res.cloudinary.com/doesqlfyi/image/upload/v1771323585/Screenshot_2026-02-17_at_3.49.17_PM_afjkxb.png)
![Sample Chat](https://res.cloudinary.com/doesqlfyi/image/upload/v1771323588/Screenshot_2026-02-17_at_3.49.36_PM_nxdipq.png)

**Sample chat:** [Sample Chat Session](https://asi1.ai/shared-chat/0d5963e8-bc48-4929-b49e-b56c98454d06)




