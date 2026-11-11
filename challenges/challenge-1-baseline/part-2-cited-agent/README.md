# Challenge 1, part 2: a cited agent

You write the core loop of the agent: one message in, one reply out, with the document ids the answer used. Then you ask it your company's first question in the chat page. Run every command from the repository root. The company data is synthetic.

## The idea, from zero

The **corpus** is the company's documents. A **document** is one of them. A **chunk** is a piece of a document, stored and searched on its own, because a model cannot read 150 documents for every question. The core's `top_k` chunks are the best-ranked chunks for the question (5 by default, [`config/settings.toml`](../../../config/settings.toml#L18)).

The core does five things in order:

1. **Retrieve.** Ask the keyword search for the chunks that best match the question. BM25 ranks chunks by the rare words they share with the question; chapter 3.2 explains it. It is shipped: [`BM25.search`](../../../app/retrieval/bm25.py#L12-L20).
2. **Build the prompt.** The system text says: answer only from the documents, and cite each document id in square brackets ([`system.txt`](../../../app/prompts/system.txt)). The user text holds each chunk as `[doc-id] title`, then the chunk, then the question ([`format_documents`](../../../app/prompts/__init__.py#L51-L61), [`build_messages`](../../../app/agents/base.py#L83-L97)).
3. **Call the model.** [`ModelClient.chat`](../../../app/model.py#L67-L77) returns a `ChatResult` with the text and the token counts.
4. **Read the citations.** The model writes `[doc-pricing-table]` after a sentence. The core keeps an id only if that document was in the evidence it delivered to the model ([`parse_citations`](../../../app/core.py#L100-L107)). A model can invent an id or cite a document it never saw. Dropping that id keeps every citation checkable. In lab 1 the delivered evidence is the retrieved chunks.
5. **Reply.** Return `text`, `citations`, `actions`, `pending`, `handoff`, `usage`, `cost_usd`, `latency_ms` and `trace_id`. When `DW_TEST_MODE=1` the reply also carries an `eval` block (`raw_reply`, ranked hit ids, delivered evidence ids, delivered tokens, usage) that the harness grades ([`_reply`](../../../app/core.py#L250-L271), [`EvalBlock`](../../../app/types.py#L59-L74)).

Two more jobs belong to the core and not to the page. **History** is kept by principal and conversation, so a person who learns another person's conversation id still starts with no history ([`_history` and `HISTORY_TURNS`](../../../app/core.py#L38)). The **request id** is a label the adapter puts on each message ([the adapter builds it](../../../app/adapters/chat.py#L528)). If a message arrives twice (an email delivered twice, a reconnecting call), the core returns the stored reply and does not act twice. The store key is the principal id, the conversation id and the request id, plus a hash of the text ([`request_hash`](../../../app/idempotency.py#L14-L15)). The same request id from another principal finds nothing. The starter store keeps only the key; Lab 5 replaces it with a store that also checks the hash, so the same request id with different text is refused there. That store is also an atomic reservation, so a duplicate that arrives while the first is still running gets an "in progress" answer.

## Step 1: read before you write (15 min)

Run the starter and ask the first question in the chat page. It answers "I don't know yet". Then read three shipped files and say in one sentence what each returns: [`app/adapters/chat.py`](../../../app/adapters/chat.py#L512-L541) (where the core's input is built), [`app/retrieval/bm25.py`](../../../app/retrieval/bm25.py), [`app/model.py`](../../../app/model.py#L59-L70).

## Step 2: write the loop (30 min)

Your gap is the block in [`app/core.py`](../../../app/core.py#L241-L247) that starts at the line `YOUR TURN: lab 1 part 2` (the line numbers here are the finished reference, so search your own file for that text). The finished reference splits the work into small functions you can read when you are stuck, but write yours in the shape you like:

- **Retrieve and prompt (10 min).** [`retrieve_turn`](../../../app/core.py#L119-L125) gets the chunks, and [`build_messages`](../../../app/agents/base.py#L83-L97) builds the messages, history first.
- **The call and the citations (10 min).** [`chat`](../../../app/core.py#L128-L135) calls the model and records the usage. Then [`parse_citations`](../../../app/core.py#L100-L107) keeps only delivered ids.
- **History and the reply store (10 min).** [`handle`](../../../app/core.py#L241-L243) and [`_process`](../../../app/core.py#L248): look the key up, return the stored reply on a repeat, otherwise build the reply and store it.

Where each number in the reply comes from: `usage` is the token counts the model returned for each call; `cost_usd` is those tokens times the prices in [`config/prices.toml`](../../../config/prices.toml) (zero on the local path); `latency_ms` is the end of the root span minus its start.

## Step 3: test and ask (15 min)

```bash
python -m pytest challenges/challenge-1-baseline/part-2-cited-agent -q
```

The tests give the core a **scripted model**, a stand-in that cites the first document it was given plus one id it was never given. No network and no Ollama are used.

- Acceptance, failing on the starter with `AssertionError: expected a citation, the starter core answered "I don't know yet"`: `test_cited_answer` (the reply cites the delivered document and drops the invented one), `test_repeat_request_id` (the second call returns the stored reply with no second model call, and the same request id from another principal gets no stored reply), `test_history_is_per_principal` (the second principal in the same conversation starts with no history; the first keeps theirs).
- Invariant, passing on the starter: `test_core_has_no_channel_code` (a static check that `app/core.py` imports nothing from `app/adapters/`) and `test_health`.

Then start the app:

```bash
python -m app
```

Open `http://localhost:8000/`. Sign in with a fixture email of your pack and read the one-time code that the server prints in its own terminal (the page never shows it): Quillon `maya.okafor@harlanmoss.example`, Juniper Lane `imelda.frost@mailbox.example`, Saltmarsh `eleanor.whitcombe@mail.example`. Ask the first question of `eval/questions.md` and read the cited answer. Open the cited document in `packs/<your-pack>/corpus/` while the model works.

One answer took 2.5 seconds on the reference GPU and 5.5 seconds on the CPU only.

| Company | First question | Cited answer (reference) | Cited ids |
|---|---|---|---|
| Quillon | How much is Pro per seat if we pay every month? | The Pro plan costs $38 per seat per month when billed monthly. [doc-pricing-table] | doc-pricing-table |
| Juniper Lane | What does service code BF-15 cost? | Service code BF-15 costs EUR 48 for self-pay patients. [doc-svc-blood-tests] | doc-svc-blood-tests |
| Saltmarsh | How much is the excess for flood damage on Home Plus? | The excess for flood damage on Home Plus is £500. [doc-faq-home] | doc-faq-home |

Commit when the tests pass.

## If something looks wrong

- **The answer has no `[doc-...]` marker.** Look at the model's raw text first (the `eval` block of a test-mode reply). If the model wrote no marker, the prompt did not reach it; print the messages you send.
- **A citation is dropped that you expected.** The id must match a delivered chunk's document exactly, `doc-pricing-table` and not `pricing-table`.
- **The second call with the same request id calls the model again.** Your key is probably missing the principal or the request id, or you store after returning.
