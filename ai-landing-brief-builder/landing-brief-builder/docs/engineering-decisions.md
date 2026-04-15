# Engineering decisions

## Why the application stays local-first
The application focuses on the full draft lifecycle: create, preview, update, inspect revisions. JSON persistence keeps that lifecycle visible in the repository and easy to run locally without adding a database layer that would dominate the project.

## Why revisions are first-class
A draft builder becomes more useful once content can be updated safely. Each update requires `expected_revision`, increments the stored revision, and appends a readable history entry so it is possible to review how the page changed over time.

## Why the copy is deterministic
The service composes repeatable page sections from a short brief instead of calling an external content API. That keeps the behavior predictable, testable, and inspectable.

## Why slug generation is stable
Preview links should remain readable and predictable. Slug generation therefore normalizes input, transliterates Cyrillic characters, and adds numeric suffixes when collisions happen.
