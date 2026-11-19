# Project

Ruby 4.0 with Bundler. `lib/app/domain` holds pure logic: a RuboCop guard forbids it from touching `App::Cli`, files, the clock, randomness or the process. `lib/app/cli` is the adapter; `bin/app` only wires `$stdout` and `$stderr`.

- `scripts/setup` checks Ruby, then installs the locked gems into `vendor/bundle`.
- `scripts/fast-check` must pass before you stop: no comments, suppressions, RuboCop with every cop enabled, Steep strict, RSpec.
- `scripts/verify` is what CI runs: fast-check plus 100% line and branch coverage and `bundle-audit`.
- `scripts/mutation` runs mutant and must leave no mutation alive.

Every class in `lib` has an RBS signature in `sig/` with the same path; Steep checks them in strict mode, so add or update the signature with the code. Value objects freeze themselves in `initialize` and validate their input, as `Money` does. Write output through the injected streams, never `puts` or `$stdout`.

You cannot edit the Gemfile, the lockfile, `.rubocop.yml`, `Steepfile`, `.mutant.yml`, `spec/spec_helper.rb` or anything in `tools/guard`. If you need a gem, say which one and why in your final message.
