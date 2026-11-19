---
name: migration
description: Write a safe, versioned Postgres migration in an unslop project. Use whenever a schema change is needed.
---

# Safe Postgres migration

1. Never edit a migration that already exists. Add a new file with the next version number in `db/migrations/`.
2. Start every migration with `SET lock_timeout = '5s';` and `SET statement_timeout = '15min';`.
3. Use expand and contract. Add new nullable columns or tables first, backfill in a separate migration in batches, switch the code, and drop old columns only in a later release.
4. Create indexes with `CREATE INDEX CONCURRENTLY` in their own migration. Add foreign keys and checks with `NOT VALID`, then `VALIDATE CONSTRAINT` in a later migration.
5. Use `bigint GENERATED ALWAYS AS IDENTITY` or `uuid DEFAULT uuidv7()` keys, `timestamptz`, `text` with check constraints, and constraints in the database rather than only in code.
6. Run `scripts/fast-check`; it runs Squawk on new migrations. Fix every finding instead of excluding the rule.
7. Never run migrations against a shared or production database. CI and the deploy pipeline apply them.
