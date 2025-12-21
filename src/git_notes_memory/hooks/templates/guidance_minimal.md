<session_behavior_protocol level="minimal">
<mandatory_rules><![CDATA[
**REQUIRED:** Use block markers for captures with three-level structure:

```
:::decision Summary line here
## Context
Why this decision was needed.

## Rationale
- Key reasoning points

## Related Files
- path/file.py:10-25
:::
```

**Block types:** `:::decision`, `:::learned`, `:::blocker`, `:::progress`, `:::pattern`

**Quick markers (brief notes only):** `[decision]`, `[learned]`, `[blocker]`, `[progress]`

**REQUIRED:** Memories in `<memory_context>` are summaries. Use `/memory:recall <id>` to expand when relevant.

Valid namespaces: decisions, learnings, blockers, progress, patterns, research, reviews, retrospective
]]></mandatory_rules>
</session_behavior_protocol>
