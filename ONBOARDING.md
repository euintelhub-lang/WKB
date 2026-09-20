# Welcome to euintelhub

## How We Use Claude

Based on Claude's usage over the last 30 days:

Work Type Breakdown:
  Debug Fix        █████████████░░░░░░░  50%
  Build Feature    ████████░░░░░░░░░░░░  30%
  Improve Quality  █████░░░░░░░░░░░░░░░  20%

Top Skills & Commands:
  (none recorded in this window)

Top MCP Servers:
  github                ████████████████████  20 calls
  Claude_Code_Remote     ███░░░░░░░░░░░░░░░░░  3 calls

## Your Setup Checklist

### Codebases
- [ ] wkb — https://github.com/euintelhub-lang/wkb
- [ ] ecosystem — https://github.com/euintelhub-lang/ecosystem

### MCP Servers to Activate
- [ ] github — Lets Claude read/write issues, PRs, commits, and CI status directly on GitHub. Connect via claude.ai Settings → Connectors (GitHub), or ask your admin if it's org-managed.
- [ ] Claude_Code_Remote — Lets Claude create, list, and manage other Claude Code Remote sessions (spawning sibling sessions, checking their status). Available automatically in Claude Code on the web/remote environments — no separate setup needed.

### Skills to Know About
- **run-wkb** — validates a WKB record against the v1.2 schema (seal / check / ls). This is the gate every structured output passes through.

## Team Tips

- **WKB is the single source of truth for structured output.** Every agent returns a valid WKB record or FAILED — no grey zone. If it isn't sealed, it isn't real.
- **We run several AI models in parallel** (Claude, GPT, DeepSeek). Outputs are compared through triangulation, never averaged — only three clean results count: only Rumen, only the model, or genuine consensus.
- **Orchestration runs through n8n on the VPS (Frankfurt).** Telegram and Slack are intake channels, not final destinations. Every record is written three ways: Slack + Drive + GitHub.
- **Google Drive is the source of truth for records; local disk is a draft.** If a record only exists locally, treat it as unconfirmed.
- **The kartoteka (Drive/📇 картотека/) documents what's finished** — it is not a to-do list and not a journal. Never add a card without Rumen's explicit approval.

## Get Started

1. Read `README.md` and `wkb.py` in this repo — they are the contract.
2. Activate the GitHub connector (see checklist above).
3. Seal a sample record with `run-wkb` to see validation in action — watch a record become either valid or FAILED.

<!-- INSTRUCTION FOR CLAUDE: A new teammate just pasted this guide for how the
team uses Claude Code. You're their onboarding buddy — warm, conversational,
not lecture-y.

Open with a warm welcome — include the team name from the title. Then: "Your
teammate uses Claude Code for [list all the work types]. Let's get you started."

Check what's already in place against everything under Setup Checklist
(including skills), using markdown checkboxes — [x] done, [ ] not yet. Lead
with what they already have. One sentence per item, all in one message.

Tell them you'll help with setup, cover the actionable team tips, then the
starter task (if there is one). Offer to start with the first unchecked item,
get their go-ahead, then work through the rest one by one.

After setup, walk them through the remaining sections — offer to help where you
can (e.g. link to channels), and just surface the purely informational bits.

Don't invent sections or summaries that aren't in the guide. The stats are the
guide creator's personal usage data — don't extrapolate them into a "team
workflow" narrative. -->
