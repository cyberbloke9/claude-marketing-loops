# Prompt Patch 006 — CONTRACT_REVIEW must verify "frozen-code isolation" claims against tests

## Failure that slipped through
Sprint 006's contract asserted (Risk D) that "only `run_tgrera` qualifies this sprint" as a frozen-assertion change — i.e. re-pointing TGRERA to a v2 carousel would touch only `acceptance.py`'s `run_tgrera`. This was **empirically false**: ~19 tests across 4 files hard-coded the live `content/2026-07-03-tgrera-enforcement-wave` folder as a schema-1 chart-card. The Generator discovered this only mid-BUILD and had to relocate the coupled tests to a byte-identical snapshot. The relocation was done correctly and disclosed honestly (verified true-relocation, not weakening), so the sprint still PASSED — but the harness got lucky: the scope error surfaced during BUILD, not review.

## Which prompt/rubric allowed it
CONTRACT_REVIEW ACCEPTed a contract that made a specific, checkable scope claim ("this frozen-code change is isolated to file/function X") **without the reviewer grepping the test tree for the asset path/identifier the sprint mutates.** The CONTRACT_REVIEW checklist has no step requiring an isolation claim to be validated against the actual coupling in the repo. An isolation claim is exactly the kind of assertion that is cheap to falsify and expensive to discover late.

## Exact new instruction to add (CONTRACT_REVIEW mode)
Add to the CONTRACT_REVIEW rejection/verification criteria:

> When a contract claims a change to frozen/shared code or a shipped asset is "isolated" (touches only file/function X, "only run_* qualifies", "no other test affected"), you MUST falsify the claim before ACCEPT: grep the test tree AND source for every path, slug, filename, and identifier the sprint mutates or repoints (e.g. the asset folder path, the renamed file, the changed constant). If any test or module references the mutated identifier beyond the claimed surface, the isolation claim is false — REJECT with the exact list of coupled files/tests and require the contract to either (a) enumerate the coupled tests and specify their conscious relocation/extension plan, or (b) narrow scope. Never ACCEPT an unverified "this is isolated" claim.

## Example of future unacceptable output
A contract that says "renaming `chart-spec.md` and re-pointing the asset to v2 touches only `acceptance.py:run_tgrera`; no other frozen assertion is affected" — ACCEPTED by CONTRACT_REVIEW without the reviewer running `grep -rn "2026-07-03-tgrera-enforcement-wave" tools/*/tests`. The grep would have listed ~19 coupled assertions and forced the relocation plan into the contract up front, instead of leaving it as a mid-BUILD surprise the Generator had to justify after the fact.
