# 20 fast-growing GitHub repos for an AI product team around Opus 5.5

Source: user-supplied scan, 11–28 Oct 2026 (15 new repos + 5 weekly risers).
Saved verbatim. Several URLs were truncated in the source (marked `…`); they have
not been verified or completed. Resolve with `gh search repos` / GitHub search before use.

## 01 / Agent systems
1. **Orca** — manage a fleet of coding agents — `github.com/stablyai/orca`
2. **Ruflo** — coordinate multi-agent workflows — `github.com/ruvnet/ruflo`
3. **Reason Network** — connect teammates' coding agents — `github.com/reason-machine…`
4. **durable-harness** — resume agents after interruptions — `github.com/vercel-labs/du…`
5. **git-ai** — source control for parallel agents — `github.com/feder-cr/git-ai`

## 02 / Memory + context
6. **Graphify** — query code and documents as a graph — `github.com/Graphify-Labs/…`
7. **ai-memory** — project memory across coding agents — `github.com/akitaonrails/a…`
8. **Graphicle** — code graphs + memory in one Rust binary — `github.com/Graphicle-AI/g…`
9. **Hy-Memory** — shared recall across AI applications — `github.com/Tencent-Hunyua…`
10. **TokenEconomizer** — reuse experience to streamline agent runs — `github.com/microsoft/Toke…`

## 03 / Tools + research
11. **earshot** — local speech tools for coding agents — `github.com/Leonxlnx/earsh…`
12. **axuse** — accessibility-first browser control via MCP — `github.com/ctoldigital/ax…`
13. **imozuru** — trace research back to primary sources — `github.com/MaryCache/imoz…`
14. **esp32-iphone-agent** — AI control of a real iPhone — `github.com/onehumanbeing/…`
15. **agentplay** — replay agent sessions as maps + timelines — `github.com/Entelligence-A…`

## 04 / Build + create
16. **HyperFrames** — editable HTML scenes into video — `github.com/heygen-com/hyp…`
17. **fx0** — describe a page, get an editable HTML prototype — `github.com/vercel-labs/fx0`
18. **blender-skills** — Blender production guidance for agents — `github.com/EL4CTEO/blende…`
19. **audio-studio-mcp** — local music + sound effects — `github.com/kanaworksai-hu…`
20. **rossark-motion-skill** — animated SVG for interfaces — `github.com/rossark0/rossa…`

## How the harness maps to these
| Harness layer | Role | Repos that inspired it |
|---|---|---|
| Orchestration (`team-run` skill, `lead` agent) | fleet / multi-agent coordination | 1, 2, 3, 5 |
| Durability (`.harness/state.md` checkpoint) | resume after interruption | 4 |
| Memory (`.harness/memory.md`) | cross-session, cross-agent recall | 6–10 |
| Research (`researcher` agent) | primary-source tracing | 13 |
| Tools (browser / speech / device) | opt-in MCP servers | 11, 12, 14 |
| Observability (`.harness/log.md`) | replayable timeline | 15 |
| Creation (`designer` agent) | UI, video, 3D, audio, SVG | 16–20 |
