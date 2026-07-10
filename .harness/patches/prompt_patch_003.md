# Prompt Patch 003 — contract arithmetic self-consistency

## What slipped through
Sprint 003 contract §4.2 (echoed §8.7, §15.5) enumerated a 5-stage single-image
degrade sequence (`limit → create container → poll → publish → permalink`) with an
explicit "NO separate parent step", but labelled it "(6 steps)". The enumerated
count, the "no parent" instruction, and the parenthetical integer were mutually
inconsistent. The Generator had to guess which was authoritative (it chose
correctly: 5), but a less careful build could have invented a phantom 6th call to
satisfy the integer — exactly the "no invented endpoints" failure the spec forbids.

## Which rule allowed it
The CONTRACT_REVIEW rubric checks for missing pass/fail conditions but does not
require step-count parentheticals to be arithmetically consistent with their own
adjacent enumeration and with the derived formula (here `N+5` carousel / `N+4`
degrade). An inconsistent "(6 steps)" passed contract review unchallenged.

## New instruction to add (CONTRACT_REVIEW mode)
When a contract states an explicit item/step COUNT next to an enumeration or a
derivable formula, REJECT unless (a) the parenthetical integer equals the number of
enumerated items, AND (b) it equals the formula's result for the stated input.
Any count that can only be reached by adding an unenumerated step is a REJECT with
the exact corrected integer supplied.

## Example of future unacceptable output
> "Sequence: A → B → C → D → E (6 steps)."  ← 5 enumerated, labelled 6. REJECT;
> required fix: change to "(5 steps)" or add the missing sixth enumerated step by
> name (never leave the reader to invent it).

## Disposition this sprint
Non-blocking. The Generator's 5-step build is the faithful reading and PASSES.
Recommend the contract text be corrected to "(5 steps)" in §4.2/§8.7/§15.5.
