\# Meeting Arena Brain — Product Brief



\## Purpose



Meeting Arena Brain is the local reasoning layer for the Meeting Arena communication-training product.



Its job is to improve the realism and usefulness of workplace roleplay while reducing unnecessary LLM reasoning and token spend.



It sits between SillyTavern and a remote language model.



The core principle is:



> Python decides the conversational strategy.  

> The LLM mainly turns that strategy into natural human language.



This is not a chatbot application and does not replace SillyTavern.



For the authoritative, current description of how behaviour is composed (persona vs. stance vs. temporary condition vs. deterministic move vs. rendering), see \`SEMANTIC\_ARCHITECTURE.md\` at the repository root. Where anything below conflicts with it, \`SEMANTIC\_ARCHITECTURE.md\` wins.



\---



\## Product Context



The wider Meeting Arena product uses:



\- SillyTavern for UI, chat history, group conversations, microphone input and voices

\- Meeting Arena Brain for deterministic social / political reasoning

\- a remote LLM for natural-language rendering

\- Coach as an on-demand training mode (not yet implemented; its first deterministic building block — the Managing Up coaching repertoire, activated when relationship=BOSS — exists, see \`SEMANTIC\_ARCHITECTURE.md\`)



The user participates as themselves.



AI participants should feel like believable colleagues in a real meeting, not roleplay characters or exaggerated personalities.



\---



\## Problem



Prompt-only character cards tend to exaggerate behavioural descriptions.



For example, describing a Service Owner as:



\- senior

\- time-poor

\- outcome-focused

\- under leadership pressure



can cause an LLM to produce caricatured dialogue such as:



> "Let's not spend an hour on this. Can we start Monday or not?"



A believable colleague might express the same pressure more indirectly:



> "Are any of those issues actually stopping us starting, or are they things we can manage through SIT?"



The product therefore separates:



1\. \*\*what conversational move should happen\*\*

2\. \*\*how that move should naturally be expressed\*\*



The first should increasingly be deterministic and testable.



The second is where the LLM adds value.



\---



\## Core Behaviour



For each actor turn:



1\. receive the existing SillyTavern conversation (which already carries that actor's persona via the SillyTavern character card)

2\. identify the current actor, for routing only — not to look up a persona description

3\. read any explicit power-difficulty/relationship/stance/temporary-condition markers (never inferred); power difficulty is room-wide, relationship is actor-to-user, and both are control metadata only in this iteration — logged, not yet acted on — see \`SEMANTIC\_ARCHITECTURE.md\`

4\. inspect the latest user utterance

5\. select an appropriate conversational move deterministically

6\. check whether this actor is repeating their immediately preceding move, from the resent conversation history only, to vary wording

7\. add a compact behavioural instruction covering stance, temporary condition, the selected move, and its guidance — never a persona description

8\. forward the request to the remote LLM

9\. return the normal OpenAI-compatible response to SillyTavern



The remote LLM should not need to rediscover the workplace strategy from scratch. See \`SEMANTIC\_ARCHITECTURE.md\` for full ownership boundaries.



\---



\## Initial Actors



These bios are the design reference that seeded each actor's SillyTavern character card, and \`arena\_brain/actors.py\` still keeps them as a routing table (which actor IDs the brain recognises). They are historical/reference material, not something the brain injects into the prompt at runtime — the actor's persona is expressed through the SillyTavern character card itself, not through this list. See \`SEMANTIC\_ARCHITECTURE.md\` for current ownership boundaries.



\### Priya — Service Owner



\- authority: high

\- pace: fast

\- detail appetite: medium

\- warmth: medium

\- challenge style: indirect

\- action bias: high



She tends to test whether an issue is a genuine blocker or something that can be managed while progress continues.



Pressure should usually be implicit rather than announced.



\### Marcus — Test Lead



\- authority: medium

\- pace: medium

\- detail appetite: high

\- warmth: medium

\- challenge style: direct

\- action bias: medium



He wants evidence and is comfortable probing weak assumptions.



\### Dana — Integration SME



\- authority: medium

\- pace: medium

\- detail appetite: high

\- warmth: medium

\- challenge style: low

\- action bias: medium



She tends to provide useful technical context and can drift into detail.



\---



\## Initial Conversational Moves



The MVP supports only five moves.



\### CLARIFY\_BLOCKER



Purpose:



Determine whether a concern genuinely prevents progress or can be managed during the work.



Example behavioural instruction:



> Clarify whether the concern genuinely prevents progress or can be managed during the work. Do not dismiss the concern.



\---



\### ACKNOWLEDGE\_THEN\_REFRAME



Purpose:



Preserve relationship/status while moving the conversation toward another interpretation or objective.



Example behavioural instruction:



> Briefly acknowledge the other person's point, then reframe toward the actor's objective without sounding submissive.



\---



\### SURFACE\_TRADEOFF



Purpose:



Make the consequence of a choice visible without turning it into confrontation.



Example behavioural instruction:



> Make the priority consequence explicit and ask for alignment on the trade-off.



\---



\### PROTECT\_ACCOUNTABILITY



Purpose:



Clarify ownership, prior agreement or responsibility without sounding defensive or accusatory.



Example behavioural instruction:



> Clarify ownership or prior agreement factually. Avoid blame language.



\---



\### ASK\_FOR\_SPECIFICS



Purpose:



Reduce ambiguity when no stronger move applies.



Example behavioural instruction:



> Ask one practical question that reduces ambiguity.



\---



\## MVP Selection Logic



The first version is intentionally simple.



Examples:



\- blocker / ready / readiness / risk / stop us

&#x20; → favour `CLARIFY\_BLOCKER`



\- priority / instead / delay / defer / trade-off

&#x20; → favour `SURFACE\_TRADEOFF`



\- owner / ownership / responsible / agreed / sign-off

&#x20; → favour `PROTECT\_ACCOUNTABILITY`



\- disagree / don't agree / however / concern

&#x20; → favour `ACKNOWLEDGE\_THEN\_REFRAME`



\- otherwise

&#x20; → `ASK\_FOR\_SPECIFICS`



This logic is a proof of architecture, not the final intelligence layer.



Keep move selection isolated so it can later become a weighted recommender.



\---



\## Language Rendering Rules



The brain's own added instruction should normally contain only:



\- stance overlay, if any (explicit, closed vocabulary)

\- temporary-condition overlay, if any (explicit, closed vocabulary)

\- selected move

\- concise move guidance

\- a note to vary wording if this move repeats the actor's immediately preceding one



It should \*\*not\*\* contain an actor identity/behavioural-profile description — that persona is already present in the conversation via the SillyTavern character card, and duplicating it here is exactly the "second persona engine" this architecture avoids. See \`SEMANTIC\_ARCHITECTURE.md\`.



Generated dialogue should:



\- sound like normal workplace speech

\- avoid theatrical roleplay

\- avoid caricature

\- avoid announcing personality traits

\- keep pressure implicit where appropriate

\- avoid unnecessary corporate jargon

\- normally stay within 1–2 short paragraphs

\- react to what was actually said

\- preserve the latest user's wording verbatim in the source conversation



\---



\## Architecture



This diagram is a quick-reference summary only. \`SEMANTIC\_ARCHITECTURE.md\` at the repository root is the authoritative, current description — read it before changing persona, stance, condition, move selection, or prompt composition.



```text

SillyTavern (owns the actor's persona: voice, cadence, dialogue examples)

&#x20;   |

&#x20;   | OpenAI-compatible request, carrying [ARENA_ACTOR=...], optional [ARENA_POWER=...] / [ARENA_RELATIONSHIP=...] / [ARENA_STANCE=...] / [ARENA_CONDITION=...]

&#x20;   v

Meeting Arena Brain

&#x20;   |

&#x20;   | identify actor (routing only, no persona lookup)

&#x20;   | read power-difficulty marker, room-wide (control metadata only in this iteration — logged, not acted on)

&#x20;   | read relationship marker, actor-to-user (control metadata only in this iteration — logged, not acted on)

&#x20;   | read stance / temporary-condition markers (explicit, never inferred)

&#x20;   | inspect latest user turn

&#x20;   | deterministic move selection (unaffected by stance/condition)

&#x20;   | check for a repeated move from resent history (wording variation only)

&#x20;   | inject compact instruction: stance + condition + move + guidance — no persona text

&#x20;   v

OpenAI / remote LLM

&#x20;   |

&#x20;   | natural-language rendering (one call)

&#x20;   v

Meeting Arena Brain

&#x20;   |

&#x20;   | OpenAI-compatible response

&#x20;   v

SillyTavern

```

