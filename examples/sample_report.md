# Codex Session Health

## Summary

- Visible state: `TOOL_RUNNING`
- Confidence: `MEDIUM`
- Session: `20260701-143812-demo`
- Project: `codex-doctor`

## Visible Evidence

- Latest event age: `8s`
- Tool: `exec_command`
- Open tool calls without completion output: `2`
- Network probe: `reachable, HTTP=401, total=0.44s`

## Conservative Interpretation

Visible events show Codex entered local tool execution. Two tool calls have not
yet shown completion output in the local log.

This is local evidence only. It does not reveal what the model is thinking.

## Next Check

Check whether the corresponding terminal commands are still running. If the
commands already finished, the local session log may be incomplete or delayed.
