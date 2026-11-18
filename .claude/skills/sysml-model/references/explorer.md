# Republishing the explorer

The explorer is one self-contained page (`generated/explorer.html`): the views in `VIEW_ORDER`, the model tree and
an inspector. The lead opens it on a phone at `EXPLORER_URL` in `tools/explorer.py` (currently
<https://claude.ai/artifact/K7ttKxrqZxzVPoWiXZknix>, also linked in the README "Explorer" row).
`tools/explorer.sha256` holds `<fingerprint>  published at <url>` for the fragment last published, and
`explorer.py --check` fails with "the published explorer is out of date" when the model, layout or explorer assets
changed and the page was not rebuilt and republished.

## Steps

1. From `assurance/models/sysml`:
   ```bash
   python3 tools/explorer.py --fragment <scratchpad>/sysml-explorer.html
   ```
   This writes `generated/explorer.html`, the fragment (the page without its document wrapper, which the Artifact
   tool adds) and **already** the new fingerprint in `tools/explorer.sha256`.
2. If this conversation has not read or published the page yet, read it first with the Artifact tool
   (`action: "read"`, `url` = `EXPLORER_URL`).
3. Publish with the Artifact tool: `file_path` = the fragment, `url` = `EXPLORER_URL`. Omit `icon` and
   `capabilities` so the page keeps its own. Do not publish without `url`: that makes a second page.
4. Confirm the result names the same URL. Then `python3 tools/explorer.py --check` passes; commit
   `generated/explorer.html` and `tools/explorer.sha256` with the model change.
5. To see the page, open the published URL (Artifact `action: "open"`), or open `generated/explorer.html` locally.

## When the publish fails

The publish can be refused (the page belongs to the lead and this session cannot write to it, a conflict, no
network, no approval). Then:

- **Never say or write that it was published.** Restore the fingerprint so the check stays honest:
  `git checkout -- tools/explorer.sha256`. `explorer.py --check` (and so CI) will keep failing until someone
  republishes, which is the true state.
- Tell the user plainly: the live explorer is behind the model, why the publish failed, and the fragment path so
  they or the lead can publish it.
- Publish a **new** page only with the lead's go-ahead (ask in chat, multiple choice, recommendation first; or
  through the `decision-inbox` skill if it is not urgent). With it: publish without `url` (give it an `icon` such as
  `diagram`), then in one commit set `EXPLORER_URL` in `tools/explorer.py`, the link in the README "Explorer" row,
  rerun `explorer.py --fragment` so `explorer.sha256` names the new URL, and check that
  `grep -rn <old-id> --exclude-dir=.git .` finds nothing else.
- Never delete the old page on your own initiative.
