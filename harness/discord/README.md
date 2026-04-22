# Discord Interface

This directory owns Discord-only transport and UI behavior.

What belongs here:
- Discord event handlers, application slash commands, and message rendering
- Channel/session mapping for Discord-specific scratch threads
- Thin glue that turns Discord input into shared harness calls

What does not belong here:
- Core loop rules
- Tool discovery or tool execution policy
- Prompt ownership
- Shared skill logic

Those shared concerns live under `harness/utils/`.

## Normal Chat Flow

Normal Discord chat uses the same shared loop as the web client:

1. Discord receives a DM or an `@mention`.
2. `bot.py` loads the channel's scratch thread through `ConversationManager`.
3. The message is appended to the in-memory thread state.
4. The shared `harness.utils.llm.loop(...)` entrypoint runs with `client_type="discord"`.
5. Policy construction filters the visible tool set for Discord before the model sees it.
6. The updated thread is persisted back through the shared context/persistence layer.

The important boundary is that Discord is a client of the shared orchestrator, not a second assistant implementation.

## Tool Access Rule

Discord is default-deny for tool exposure.

That means:
- normal Discord chat does not automatically inherit every MCP tool
- orchestration pseudo-tools such as delegation are also hidden by default
- the only tools exposed to Discord are the ones you explicitly allow in `.env`

Current knob:
- `HARNESS_DISCORD_TOOL_ALLOWLIST=tool_a,tool_b`

If that value is blank, Discord sees no tools.

## Adding Slash Commands

Use real Discord application commands in `bot.py` via `bot.tree.command(...)`.

Guidelines:
- keep command handlers thin
- route command behavior into shared helpers in `harness/utils/`
- avoid re-implementing orchestration or model calling logic in Discord code

Good pattern:
- parse Discord-specific inputs
- call a shared skill or shared session helper
- send the result back through Discord rendering

Bad pattern:
- add a second model loop just for Discord
- bypass shared policy and expose tools directly from Discord code

## Skills From Discord

Discord slash commands are the explicit client-trigger surface for skills.

Current shape:
- `/skill` triggers a named shared skill
- the command builds a payload from the current channel thread
- shared skill execution happens in `harness/utils/orchestration/skills.py`

Skills are not the same thing as tools:
- a skill is a higher-level intent entrypoint
- a skill may use specialized prompting or a controlled execution path
- a skill does not imply that raw tools are exposed to the Discord model

## Session Commands

Discord may expose session/thread slash commands when a client-local action is needed.

The current `thread_new` command is intentionally local:
- it resets the Discord channel onto a fresh `client_scratch` thread
- it does not change shared web/global thread behavior

If you add more session commands, keep them focused on Discord UX and thread selection, not on core orchestration logic.
