# Prompt Patch 002 — Contract byte-determinism must be tested by same-basename re-render, not -a/-b copies

## Failure that (nearly) slipped through
Sprint 002's contract §7(a)/(c) asserts `manifest.json` **byte-identical** across runs, but the
command copies each fixture to two **differently-named** folders (`/tmp/$f-a`, `/tmp/$f-b`) and
diffs the manifests. The manifest carries `slug`, derived from the folder basename
(`slug = folder.name` — frozen v1 behavior; the spec's own §5.3 manifest shows `slug` = folder
name). So the literal command ALWAYS produces a slug-only diff → a spurious `AssertionError`, even
though the renderer is correctly deterministic (same asset folder re-rendered → `cmp`-identical
manifest + PNG, which the Generator's own `test_written_outputs_byte_identical_across_runs` proves
by using **same-basename** temp dirs).

A naive evaluator running the contract verbatim would FAIL correct code on this false signal.

## Which rubric/prompt allowed it
The Contract mode has no rule that byte-determinism tests must hold **every input constant** —
including the folder basename that feeds `slug`. §7c changed an input (the folder name) while
asserting output-byte-equality.

## Exact instruction to add (Contract-authoring guidance; applies to Sprints 004 & 006, which also assert PDF/manifest byte-equality)
> When asserting byte-equality of any manifest/PDF/PNG across runs, hold ALL inputs constant,
> including the asset folder **basename** (the renderer derives `slug` from it). Test determinism
> by re-rendering the SAME folder twice (or two temp copies that share the SAME basename under
> different parents), never by copying to distinct basenames like `-a`/`-b`. If distinct basenames
> are unavoidable, exclude `slug` from the byte comparison and state so explicitly.

## Example of future unacceptable output (a contract command that would wrongly FAIL correct code)
```bash
cp -R inputs/foo /tmp/foo-a && cp -R inputs/foo /tmp/foo-b
render /tmp/foo-a && render /tmp/foo-b
diff /tmp/foo-a/render/manifest.json /tmp/foo-b/render/manifest.json   # WRONG: slug differs by design
```
Acceptable instead:
```bash
cp -R inputs/foo /tmp/A/foo && cp -R inputs/foo /tmp/B/foo   # same basename 'foo'
render /tmp/A/foo && render /tmp/B/foo
cmp /tmp/A/foo/render/manifest.json /tmp/B/foo/render/manifest.json   # slug identical -> true byte test
```

## Evaluator guidance (until the contract prompt is patched)
If a byte-determinism command fails only on `slug` (or another basename-derived field), disposition
it as a **contract-test artifact, not a code defect**: verify same-basename re-render is
`cmp`-identical before failing the sprint. Do NOT FAIL correct deterministic renderers on a
basename-induced slug diff.
