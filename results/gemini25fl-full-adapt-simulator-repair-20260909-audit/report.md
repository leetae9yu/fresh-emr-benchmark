# AdaptQA simulator repair: complete

Completed 2026-09-09T02:43:40.872Z. All 160 requested slots now have valid outcomes.
The original 156 results and all 40 files in the original result root are
unchanged by SHA-256. All 410 historical attempts remain available.

## Results

| Environment | Successes / valid | Rate |
|---|---:|---:|
| MIMIC Original | 7/40 | 17.5% |
| MIMIC Star | 9/40 | 22.5% |
| eICU Original | 7/40 | 17.5% |
| eICU Star | 8/40 | 20.0% |
| **Total** | **31/160** | **19.375%** |

The four additions are eICU Original task0=1, task5=0, task11=0, task30=0.
No missing outcome was filled with a synthetic score. The native
EnvRunResult parser accepted the combined artifact, with exactly one
result per environment/task/trial slot.

## What failed and what changed

1. Null or blank simulator content entered string checks. Null produced a
   NoneType error before corrective feedback; blank content could pass.
   Invalid content is now rejected explicitly and receives bounded feedback.
2. Rejected drafts and repair instructions were appended to the canonical
   simulator history. Retries now use a separate list; accepted responses
   alone are committed to that history.
3. Reflection JSON and new_response were insufficiently checked. The existing
   structured schema now parses reflection output, and revised text must pass
   the same user-response format checks before it can be accepted.
4. Nonempty malformed drafts, including explanation plus END, bypassed the
   existing reflection mechanism. They now enter that mechanism using the
   canonical history. The initial repair consumes one of the same three
   reflection calls; it does not add an extra reflection budget.
5. Context/exhaustion paths no longer fabricate END. Plain provider timeouts
   retain bounded retries and become unscored runtime errors on exhaustion.
   Actual inherited agent-deadline handling is unchanged.

Models, temperatures, task instructions, tool exposure and any-hit scoring
were not changed. The original 156, first three additions and final task5
use separately recorded source versions; this is not presented as a single
unchanged-code run.

## Runtime evidence and limitations

The repair produced 10 new attempts: four valid outcomes, four user_error
rejections, one runtime_error and one validator_error. There are now 420
distinct attempts in total. None of the failed records was deleted.

Ten per-sample diagnostic files contain 537 events and
164 raw simulator responses. They record generation, verifier and reflection
requests/responses, response IDs, finish reasons, available usage, parse or
format failures and retry decisions. Credentials and headers are excluded.
Final validator verdicts/reasons and tracebacks remain in checkpoints and logs.

The accepted task0/11/30 trajectories recovered 2/4/1 null simulator
responses respectively. These null responses reported zero tokens; two
OpenRouter generation metadata lookups returned404. The provider's deeper
reason for returning null is therefore unknown, not inferred.

Task5 previously repeated the same mixed-END response through all three
generation attempts. Its final accepted trajectory did not hit this
format-error branch; regression tests establish the new routing behavior.
Do not claim that the routing change alone caused the final acceptance.

The existing validator shortcut for an empty DB-agent response accepted
task0/11/30; task5 was accepted by the unchanged LLM validator. The shortcut
was preserved rather than silently changing benchmark semantics.

Historical rejected simulator raw payloads were not saved by the old code
and cannot be reconstructed retroactively. Existing historical reasons,
agent-visible conversations and logs remain intact.

## Cost

| Item | USD |
|---|---:|
| Previously paid pilot | 0.565066700 |
| Previously paid full continuation | 2.763604530 |
| **This repair, including failed attempts** | **0.31303736** |
| **Combined experiment total** | **3.64170859** |

OpenRouter selected-key usage:81.842985711 -> 82.156023071.
The previous Tavily discrepancy settled at222credits before repair, matching
2 preflight credits plus110 advanced searches. This repair added9 searches,
expected18advanced credits; the final usage counter stillreports222, so the
new increment is pending reconciliation. No extra searches were made to
check billing. All run/completion/budget watches are stopped.

## Verification

- Initial boundary/diagnostic regression:66 red failures, then228 related tests passed.
- Provider-timeout scoring regression:14 red failures, then136 related tests passed.
- Final routing regression:4 red failures, then154 related tests passed together.
- Python compilation and actual config-driven execution succeeded.
- Combined artifact:160 unique valid slots,31successes; native schema validated.
- Original40file hashes,156payload hashes and410historical attempts verified unchanged.
- Full suite did not complete because unrelated SQL-conversion tests timed out.
  Legacy source lint/type findings remain; no full-suite or clean-static claim is made.

## Files

- combined-results.jsonl:160 original-format result rows, copied verbatim from source checkpoints.
- attempt-index.json:all420attempts, original locations, verdicts and diagnostic links.
- final-analysis.json:machine-readable results, costs, provenance and diagnostic hashes.
- preservation.json:original file and156result hashes.
- provenance.json and format-routing-provenance.json:old/new source identities and scope.
- simulator-repair.patch and final-code-snapshot.json:repair code and tests.
- format-failure-evidence.json and null-generation-lookup.json:concrete failure evidence.
- repair-journal.md:investigation record.

Original, first-repair and final-repair result directories are indexed in
final-analysis.json. Original files are not overwritten by the combined view.
