# Decision register

Questions that wait on the project lead live in [`register.yaml`](register.yaml), one entry per
question. The decision inbox page is generated from it by [`build_inbox.py`](build_inbox.py), and
[`check_decisions.py`](check_decisions.py) checks it in CI.

The register is where a question is asked and answered. It is not the decision record: once a
decision is applied, it is recorded where the project already keeps that kind of decision
(WP-M-07 §5 for strategic decisions, otherwise the work product that owns the item), and the
register entry points there.

## Lifecycle

| Status | Meaning | Who moves it |
|---|---|---|
| `open` | Asked; no answer yet | Claude, when asking |
| `answered` | The project lead picked an option (on the inbox page or in chat) | Claude, when copying the answer in |
| `assumed` | No answer by `proceed_after`; Claude went ahead with the recommended option. Allowed only for `reversibility: easy`. The lead can still change it | Claude |
| `applied` | The change is made; `applied.ref` names the commit or PR, `applied.record` where the decision is recorded | Claude |
| `withdrawn` | The question no longer applies; `note` says why | Claude |

A `hard` question is never assumed and never applied without an answer from the lead. A `revisit`
question waits for an answer too, but can be reopened at the gate named in `gate`.

## The inbox page

The page shows open questions first (hard, then revisit, then easy), then answers waiting to be
applied, then what is done, with a link to each commit or PR.

Answers and requests for more explanation are saved in the page's own store, in the collections
`answers` and `explain`, keyed by register `id`. At the start of a session Claude reads both,
copies answers into this file (`via: inbox`), writes any requested explanation into `explanation`,
applies what can be applied, rebuilds the page and republishes it.

```sh
python3 assurance/01-management/decisions/check_decisions.py
python3 assurance/01-management/decisions/build_inbox.py --out <scratch>/inbox.html
```

## How Claude asks

- **Blocking now, a quick choice:** asked in chat, then recorded here with `via: chat`.
- **Needs a picture or context, or can wait:** a register entry and a card on the inbox page, with
  one line and the link in chat.
- **Easy to undo:** an entry with `proceed_after`; Claude goes ahead with the recommendation after
  that date and says so.
