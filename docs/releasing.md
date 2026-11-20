# Releasing

A release is a git tag. Repositories pin it in three places: `unslop.toml`, the marketplace `ref` in `.claude/settings.json`, and the action in `.github/workflows/unslop.yml`.

## Cut a release

1. In a pull request, set the new version in `src/unslop/__init__.py` and `plugin/.claude-plugin/plugin.json`, and update the `@v…` examples in the README and `docs/adopting.md`. The contract check fails if the two version files disagree.
2. After it merges, tag the merge commit and push the tag:

   ```bash
   git tag v0.4.0 origin/main
   git push origin v0.4.0
   ```

3. The `release` workflow checks that the tag matches both version files, builds the wheel and source archive, and attaches them to a GitHub release.

`unslop init` and `unslop upgrade` resolve the tag to a commit SHA for the generated workflow, so tag before anyone runs them with the new version; `upgrade` refuses an untagged version.

## Publish to PyPI

The name `unslop` is taken on PyPI by an unrelated project, so the distribution is called `unslop-cli`. It installs two identical commands, `unslop` and `unslop-cli`, so `uvx unslop-cli init` works once it is published.

Publishing is off until you turn it on:

1. Create an account on [pypi.org](https://pypi.org) and add a pending trusted publisher for the project `unslop-cli`: owner `kimkun0504`, repository `unslop`, workflow `release.yml`, environment `release`.
2. In this repository's settings on GitHub, create an environment named `release`, and set the repository variable `PUBLISH_TO_PYPI` to `true`.
3. Push the next tag. The workflow publishes with a short-lived token from GitHub, so no PyPI password is stored anywhere.

After the first publish, switch the default source in `plugin/bin/unslop` from the git tag to `unslop-cli==$version`, and change the commands in the README and `docs/adopting.md` to `uvx unslop-cli init` and `uvx unslop-cli new`.
