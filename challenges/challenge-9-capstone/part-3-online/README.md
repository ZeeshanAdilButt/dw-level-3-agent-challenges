# Capstone, part 3: put your agent online for the checker

Run every command from the repository root. The packs are synthetic. The worked company is Quillon. This part runs no experiment, so there is no prediction file. The sizes below were measured on the synthetic pack with the reference build.

## The idea, from zero

The checker is a program, and it runs on our side. To grade your agent it sends it questions over the internet. A laptop has no public address, so the checker cannot reach it. A **tunnel** is a program that gives your laptop a public web address for a while and passes each request through to the agent. A free host is the other option: you deploy the same commit there.

The checker sends its request, and if nothing answers within 120 seconds it counts as a timeout. So the agent must be running, with its model, for the whole booked window.

**Exam mode** is the agent started with `DW_TEST_MODE=1`. It accepts a test header, `X-Test-Principal`, which says which fixture person is speaking, and it adds an `eval` block to every reply so the checker can read what the agent did. The header is for the checker only. It is not how a real product proves identity: in a real product the adapter proves who is speaking (5.4). On a live address the header works only behind a **one-time token**, a secret shown once on the submit page, which the checker sends in the `X-Exam-Token` header. Without the token, the header is refused.

The **checker's mock** is the practice company system that we host for your exam session. The exam page gives you its address as `MOCK_API_URL`. Your agent calls it instead of your own mock, and every action returns a receipt to us, so we read the final state from our side, never from your `/mock-state`.

## What the checker sends

First `GET /health`. Then the public set once. Then 30 unseen questions and 10 unseen attacks. Then the safety suite, three times each. It sends one case at a time, each in its own conversation and its own mock space. If a reply is lost, it resends the same request id, so an action is never repeated. The public set alone is as long as one full run of yours (about 13 minutes on a GPU, or about 29 minutes (estimated) on the CPU only). The unseen cases and the safety suite come on top. The checker run has not been timed or costed end to end. The window of three hours is sized from that.

Everything `/health` reports (commit, fingerprint, model) is **self-reported**. The checker records it and says so. It is not proof of what is running.

## What the starter gives you

| What | Where | Lines |
|---|---|---|
| `python -m app`, port 8000, and the mode line it prints | [app/\_\_main\_\_.py](../../../app/__main__.py#L10-L17) | 10 to 17 |
| Exam mode and the token check | [app/adapters/chat.py](../../../app/adapters/chat.py#L383-L391) | 383 to 391 |
| Who is speaking: the header only with the token, else a signed-in session | [app/adapters/chat.py](../../../app/adapters/chat.py#L489-L511) | 489 to 511 |
| The `eval` block added in exam mode | [app/adapters/chat.py](../../../app/adapters/chat.py#L513-L537) | 513 to 537 |
| `/health` | [app/adapters/chat.py](../../../app/adapters/chat.py#L565-L573) | 565 to 573 |
| The tools use `MOCK_API_URL` when it is set | [app/adapters/chat.py](../../../app/adapters/chat.py#L167-L181) | 167 to 181 |
| The token is sent on to the mock | [mock_api/\_\_init\_\_.py](../../../mock_api/__init__.py#L84-L93) | 84 to 93 |

You write no code. You write one entry in `LAB-LOG.md`.

## Steps

1. **Read this page.** Open the submit page (do not submit). Copy the one-time token and the mock address.
2. **Start the agent in exam mode.** In a terminal, set the three variables for that terminal only, then start it. Do not put the token in a file or in a commit.

   macOS and Linux:

   ```bash
   export DW_TEST_MODE=1
   export DW_EXAM_TOKEN=<token from the submit page>
   export MOCK_API_URL=<mock address from the exam page>
   python -m app
   ```

   Windows PowerShell:

   ```powershell
   $env:DW_TEST_MODE = "1"
   $env:DW_EXAM_TOKEN = "<token from the submit page>"
   $env:MOCK_API_URL = "<mock address from the exam page>"
   python -m app
   ```

   It prints `test mode ON`. Leave this terminal open.
3. **Open the tunnel.** In a second terminal: `cloudflared tunnel --url http://localhost:8000`. It prints an address that ends in `trycloudflare.com`. Keep this terminal open too. Restarting it gives a new address. With a free host instead, deploy the same commit and set the three variables and any model key in the host's own settings, never in the repository.
4. **Check `/health` on the laptop.** Open `<address>/health`. It must show `status` ok, your latest `commit` (compare with `git rev-parse HEAD`; `/health` reports git HEAD when a `.git` folder exists, and `DW_COMMIT` only without one), the `fingerprint` of your last kept run and the `model` from `config/settings.toml`. If the commit differs, commit and push first, then restart the agent.
5. **Check from a phone on mobile data,** not your Wi-Fi. Open `<address>/health`. Then open `<address>/`, sign in with a fixture email, read the one-time code in the terminal where the agent runs, and ask one ordinary question. A correct, cited answer from the phone proves that someone outside your network can reach you. The phone does not need the token: the token is for the checker's header.
6. **Learn what must stay running** (the table below).
7. **If you run hosted,** three things differ. The agent code still runs on your laptop, which only relays and waits on the model over the internet. The checker's calls cost real money (the figure above), and a free tier will not cover them in one day, so check your balance first. The model key lives only in your shell or the host's settings, never in a file you commit.
8. **Write a short entry in `LAB-LOG.md`** under a heading that contains the word Online: the date, whether you used a tunnel or a host, and one thing you would check again on submission day. Do not write the token or the address.
9. **Run the test.** `python -m pytest challenges/challenge-9-capstone/part-3-online -q`.

## What must stay running for the three hours, and why

| What | Why |
|---|---|
| The laptop, awake and plugged in | If it sleeps, the agent and its model stop answering |
| The agent terminal, open | Closing it stops the agent |
| The tunnel terminal, open | A closed tunnel is an address that no longer works |
| The local model server running with the model loaded, or the hosted key valid | Every case needs a model reply |
| No edits to code or settings, and no branch switch | The commit and the fingerprint must still match your submission |
| No restart of the tunnel | A restart gives a new address and the checker cannot find you |

If the connection drops, a mentor reschedules. A dropped connection is never counted as a fail.

## If something looks wrong

- **`/health` shows a commit that is not your latest.** You started the agent before your last commit, or you did not push. Commit, push, restart.
- **The phone cannot open the address.** The tunnel terminal was closed or restarted. Open the tunnel again and use the new address.
- **The checker's header is refused (403).** The agent was started without `DW_TEST_MODE=1`, or the token in the terminal differs from the one on the submit page.
- **The first answer fails after you set `MOCK_API_URL`.** Check the address on the exam page for a typo, and that the terminal that started the agent has the variable set.
