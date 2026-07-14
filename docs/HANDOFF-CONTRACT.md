# Cross-Skill Handoff Contract

A handoff is needed only when one skill has completed its postcondition and another workflow must
continue. Do not emit a handoff record for ordinary reasoning inside one skill.

Use a compact observable record when the next step crosses a consequence boundary, depends on
mutable state, or would otherwise repeat material discovery:

```yaml
completed_postcondition: <what is now true>
verified_state: <directly inspected facts>
verified_oids: <exact refs/objects when relevant>
protected_state: <state verified unchanged>
unresolved_unknowns: <material unknowns or none>
partial_effects: <effects already produced or none>
recovery_anchor: <ref/path/limitation or none>
next_skill: <route and reason>
state_reinspection_required: true
```

Authorization, approval, and confirmation are not inherited merely because a previous skill was
activated. Revalidate them when the target, scope, destination, consequence, or recovery model
expands. When the next action is the same exact action and scope already requested, avoid redundant
confirmation; refresh mutable evidence close to execution instead.
