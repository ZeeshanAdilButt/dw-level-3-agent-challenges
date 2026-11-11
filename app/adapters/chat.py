"""The chat adapter: a thin FastAPI layer that connects the web channel to the agent core.

It proves who is speaking (a session cookie from a fixture sign-in, or the test header in test mode),
builds a `types.Message`, calls `Agent.handle`, and returns the `Reply`. It decides nothing about the
answer. It also serves the chat UI, the dashboard and the read-only runs API.

Identity simulation (decision C2): the user signs in with a fixture email, the server prints a one-time
code to its own log (never to the browser), and a session cookie carries the principal from then on.
`X-Test-Principal` is accepted only when DW_TEST_MODE=1 and the X-Exam-Token header equals DW_EXAM_TOKEN.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import threading
import time
import tomllib
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.types import Message, Principal, principal_from_dict, principal_id

ROOT = Path(__file__).resolve().parents[2]
SESSION_COOKIE = "dw_session"
SESSION_SECONDS = 8 * 3600
CODE_SECONDS = 600
MAX_CODE_ATTEMPTS = 5
ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
MAX_TEXT = 4000


class CoreUnavailable(RuntimeError):
    """The agent core, or something it needs, could not be loaded."""


# ----------------------------------------------------------------------------------------------
# Settings and fixtures
# ----------------------------------------------------------------------------------------------

def load_flat_settings(root: Path) -> dict:
    """Use the app core's loader when it exists, else read config/settings.toml directly."""
    try:
        from app.settings import load_settings  # written by the app core builder
    except ImportError:
        pass
    else:
        return load_settings(path=Path(root) / "config" / "settings.toml")
    with open(root / "config" / "settings.toml", "rb") as fh:
        raw = tomllib.load(fh)
    flat: dict = {}
    for value in raw.values():
        if isinstance(value, dict):
            flat.update(value)
    return flat


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", ".", text.lower()).strip(".")


def load_principals(root: Path, pack: str) -> tuple[dict[str, Principal], dict[str, str]]:
    """Fixture principals by id, and fixture emails to principal ids, for one pack.

    The fixture holds accounts (Quillon), patients and the accounts that own them (Juniper), and
    policyholders (Saltmarsh). A fixture without an email gets a derived first.last@mail.example one.
    """
    path = root / "packs" / pack / "tools" / "fixture.json"
    principals: dict[str, Principal] = {}
    emails: dict[str, str] = {}
    if not path.exists():
        return principals, emails
    fx = json.loads(path.read_text(encoding="utf-8"))

    def add(pid: str, role: str, verified: bool, account: Optional[str], email: Optional[str], *aliases: str):
        p = Principal(id=pid, role=role, verified=verified, account_id=account)
        principals[pid] = p
        for alias in aliases:
            principals.setdefault(alias, p)
        if email:
            emails[email.lower()] = pid

    for acc in fx.get("accounts", []):
        if "primary_contact" in acc:  # Quillon
            add(f"{acc['account_id']}-owner", "customer", True, acc["account_id"],
                acc["primary_contact"].get("email"), acc["account_id"])
    for acc in fx.get("accounts", []):
        if "owns_patient_ids" in acc:  # Juniper Lane
            pid = f"{acc['account_id']}-owner"
            add(pid, "patient", True, acc["account_id"], None, acc["account_id"])
            for pt in fx.get("patients", []):
                if pt.get("owner_account_id") == acc["account_id"] and pt.get("email"):
                    emails[pt["email"].lower()] = pid
    for ph in fx.get("policyholders", []):  # Saltmarsh
        email = ph.get("email") or f"{_slug(ph['name'])}@mail.example"
        add(f"{ph['account_id']}-owner", "policyholder", True, ph["account_id"], email, ph["account_id"])
    for i, pr in enumerate(fx.get("prospects", []), start=1):
        pid = pr.get("prospect_id", f"prospect-{i:02d}")
        number = re.sub(r"\D", "", pid) or f"{i:02d}"
        add(pid, "prospect", False, None, pr.get("email"), f"prospect-{number}")
    add("anonymous", "prospect", False, None, None)
    return principals, emails


def pack_documents(root: Path, pack: str) -> Path:
    return root / "packs" / pack / "corpus"


def split_front_matter(text: str) -> tuple[dict, str]:
    meta: dict = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if ":" in line and not line.startswith(" "):
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip("'\"")
            return meta, text[end + 4:].lstrip("\n")
    return meta, text


# ----------------------------------------------------------------------------------------------
# The agent, built lazily so the server starts even while the core is unfinished
# ----------------------------------------------------------------------------------------------

class AgentHolder:
    def __init__(self, root: Path, factory: Optional[Callable[[], Any]] = None):
        self.root = root
        self.factory = factory
        self._agent = None
        self._lock = threading.Lock()
        self.error: Optional[str] = None

    def get(self):
        with self._lock:
            if self._agent is None:
                try:
                    self._agent = self.factory() if self.factory else self._default_factory()
                    self.error = None
                except CoreUnavailable:
                    raise
                except Exception as exc:  # any failure to build is reported the same plain way
                    self.error = f"{type(exc).__name__}: {exc}"
                    raise CoreUnavailable(self.error) from exc
            return self._agent

    def _default_factory(self):
        try:
            from app.core import Agent
        except Exception as exc:
            raise CoreUnavailable(f"app/core.py could not be imported ({type(exc).__name__}: {exc}). "
                                  "The agent core is not finished or has an error.") from exc
        settings = load_flat_settings(self.root)
        pack_dir = self.root / "packs" / settings.get("pack", "quillon")
        mock = self._make_mock(pack_dir)
        return Agent(settings, pack_dir, mock)

    @staticmethod
    def _make_mock(pack_dir: Path):
        url = os.environ.get("MOCK_API_URL")
        namespace = os.environ.get("DW_MOCK_NAMESPACE", "live")
        try:
            if url:
                from mock_api import HttpMockClient
                return HttpMockClient(url, namespace)
            try:
                from mock_api import MockClient
            except ImportError:
                from mock_api.client import MockClient
            return MockClient(pack_dir, namespace)
        except Exception as exc:
            raise CoreUnavailable(f"the mock API could not be loaded ({type(exc).__name__}: {exc})") from exc

    def mock_state(self) -> dict:
        agent = self.get()
        mock = getattr(agent, "mock", None)
        if mock is None:
            raise CoreUnavailable("the agent has no mock client to read state from")
        return mock.state()


# ----------------------------------------------------------------------------------------------
# Runs on disk
# ----------------------------------------------------------------------------------------------

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


class RunStore:
    """Read-only view of runs/ (and, when asked, of reference-runs/). Never writes."""

    def __init__(self, runs_dir: Path, reference_dir: Path):
        self.runs_dir = runs_dir
        self.reference_dir = reference_dir

    def _dirs(self, source: str) -> list[tuple[str, Path]]:
        found: list[tuple[str, Path]] = []
        if source == "reference":
            if self.reference_dir.is_dir():
                for lab in sorted(self.reference_dir.iterdir()):
                    if not lab.is_dir():
                        continue
                    if (lab / "run.json").exists():
                        found.append((f"ref.{lab.name}", lab))
                    for sub in sorted(lab.iterdir()):
                        if sub.is_dir() and (sub / "run.json").exists():
                            found.append((f"ref.{lab.name}.{sub.name}", sub))
        elif self.runs_dir.is_dir():
            for d in sorted(self.runs_dir.iterdir()):
                if d.is_dir() and (d / "run.json").exists():
                    found.append((d.name, d))
        return found

    def resolve(self, run_id: str) -> Optional[Path]:
        if not SAFE_NAME.match(run_id):
            return None
        if run_id.startswith("ref."):
            parts = run_id.split(".", 2)
            base = self.reference_dir / parts[1] if len(parts) > 1 else None
            if base is None:
                return None
            d = base if len(parts) == 2 else base / parts[2]
            root = self.reference_dir.resolve()
        else:
            d = self.runs_dir / run_id
            root = self.runs_dir.resolve()
        try:
            d = d.resolve()
            d.relative_to(root)
        except (ValueError, OSError):
            return None
        return d if d.is_dir() and (d / "run.json").exists() else None

    def listing(self, source: str = "runs") -> dict:
        runs = []
        for run_id, d in self._dirs(source):
            try:
                data = read_json(d / "run.json")
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            data.setdefault("run_id", run_id)
            data["id"] = run_id
            data["mtime"] = (d / "run.json").stat().st_mtime
            runs.append(data)
        runs.sort(key=lambda r: (r.get("mtime", 0), r["id"]))
        confirmations = []
        if source == "runs" and self.runs_dir.is_dir():
            confirmations = sorted(p.stem for p in self.runs_dir.glob("confirm-*.json"))
        return {"source": source, "runs": runs, "kept": self.kept_id(), "confirmations": confirmations}

    def get(self, run_id: str, with_cases: bool = True) -> Optional[dict]:
        if run_id.startswith("confirm-") and SAFE_NAME.match(run_id):
            path = self.runs_dir / f"{run_id}.json"
            if path.is_file():
                return {"id": run_id, "confirmation": read_json(path)}
            return None
        d = self.resolve(run_id)
        if d is None:
            return None
        out = {"id": run_id, "run": read_json(d / "run.json")}
        out["run"].setdefault("run_id", run_id)
        cases_path = d / "cases.jsonl"
        out["cases"] = read_jsonl(cases_path) if (with_cases and cases_path.exists()) else []
        return out

    def kept_id(self) -> Optional[str]:
        path = self.runs_dir / "kept.json"
        if not path.is_file():
            return None
        try:
            data = read_json(path)
        except (OSError, ValueError):
            return None
        return _pick_kept(data)

    def fingerprint(self) -> str:
        """The kept run's fingerprint, recomputed from the manifest in its run.json (the harness's own formula), never
        the stored string: editing that string changes nothing. "none" when there is no kept run or no manifest."""
        kept = self.kept_id()
        if not kept:
            return "none"
        d = self.resolve(kept)
        if d is None:
            return "none"
        try:
            run = read_json(d / "run.json")
        except (OSError, ValueError):
            return "none"
        manifest = run.get("manifest") if isinstance(run, dict) else None
        if not isinstance(manifest, dict):
            return "none"
        if not self._digest_ok(d, run):
            return "edited"
        body = {k: v for k, v in manifest.items() if k != "fingerprint"}
        return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _digest_ok(d: Path, run: dict) -> bool:
        """The harness's record digest (harness/records.py record_digest): run.json and cases.jsonl unchanged since the
        run finished. A record from before digests existed has none and passes."""
        want = run.get("digest")
        if not isinstance(want, dict):
            return True

        def canon(obj) -> str:
            plain = json.loads(json.dumps(obj, ensure_ascii=False, default=str))
            return json.dumps(plain, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

        try:
            rows = read_jsonl(d / "cases.jsonl") if (d / "cases.jsonl").exists() else []
        except (OSError, ValueError):
            return False
        body = {k: v for k, v in run.items() if k != "digest"}
        return (want.get("record") == hashlib.sha256(canon(body).encode("utf-8")).hexdigest()
                and want.get("cases") == hashlib.sha256(canon(rows).encode("utf-8")).hexdigest())

    def kept_settings(self) -> Optional[dict]:
        """The settings recorded in the kept run, or None when there is no kept run."""
        kept = self.kept_id()
        d = self.resolve(kept) if kept else None
        if d is None:
            return None
        try:
            run = read_json(d / "run.json")
        except (OSError, ValueError):
            return None
        s = run.get("settings") if isinstance(run, dict) else None
        return s if isinstance(s, dict) else None


def _pick_kept(data: Any) -> Optional[str]:
    if isinstance(data, str):
        return data
    if isinstance(data, list) and data:
        return _pick_kept(data[-1])
    if isinstance(data, dict):
        for key in ("run_id", "kept", "current", "id", "history"):
            if key in data and data[key]:
                return _pick_kept(data[key])
    return None


# ----------------------------------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------------------------------

class Auth:
    def __init__(self):
        self.codes: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.lock = threading.Lock()

    def issue_code(self, email: str) -> str:
        code = f"{secrets.randbelow(10**6):06d}"
        with self.lock:
            self.codes[email] = {"code": code, "expires": time.time() + CODE_SECONDS, "attempts": 0}
        return code

    def check_code(self, email: str, code: str) -> bool:
        with self.lock:
            entry = self.codes.get(email)
            if not entry or entry["expires"] < time.time():
                self.codes.pop(email, None)
                return False
            entry["attempts"] += 1
            if entry["attempts"] > MAX_CODE_ATTEMPTS:
                self.codes.pop(email, None)
                return False
            if hmac.compare_digest(entry["code"], code):
                self.codes.pop(email, None)
                return True
            return False

    def new_session(self, principal: Principal) -> str:
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.sessions[token] = {"principal": principal, "created": time.time(), "cited": set()}
        return token

    def session(self, token: Optional[str]) -> Optional[dict]:
        if not token:
            return None
        with self.lock:
            s = self.sessions.get(token)
            if s and time.time() - s["created"] > SESSION_SECONDS:
                self.sessions.pop(token, None)
                return None
            return s

    def drop(self, token: Optional[str]) -> None:
        with self.lock:
            self.sessions.pop(token or "", None)


def test_mode_active() -> bool:
    return os.environ.get("DW_TEST_MODE") == "1"


def exam_token_ok(request: Request) -> bool:
    expected = os.environ.get("DW_EXAM_TOKEN", "")
    given = request.headers.get("x-exam-token", "")
    return bool(expected) and hmac.compare_digest(expected.encode(), given.encode())


def git_commit(root: Path) -> str:
    """HEAD of the repository when there is one (.git exists); DW_COMMIT only for a deploy without .git."""
    if not (Path(root) / ".git").exists():
        return os.environ.get("DW_COMMIT") or "unknown"
    try:
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True,
                             timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


# ----------------------------------------------------------------------------------------------
# The app
# ----------------------------------------------------------------------------------------------

def create_app(root: Optional[Path] = None, runs_dir: Optional[Path] = None,
               agent_factory: Optional[Callable[[], Any]] = None) -> FastAPI:
    root = Path(root) if root else ROOT
    runs_dir = Path(runs_dir or os.environ.get("DW_RUNS_DIR") or root / "runs")
    api = FastAPI(title="Agent chat adapter", docs_url=None, redoc_url=None, openapi_url=None)
    store = RunStore(runs_dir, root / "reference-runs")
    auth = Auth()
    holder = AgentHolder(root, agent_factory)
    api.state.auth = auth
    api.state.agent = holder
    api.state.store = store
    commit = git_commit(root)

    def settings() -> dict:
        try:
            return load_flat_settings(root)
        except Exception:
            return {"pack": "quillon"}

    def principals() -> tuple[dict[str, Principal], dict[str, str]]:
        return load_principals(root, settings().get("pack", "quillon"))

    def error(status: int, code: str, detail: str) -> JSONResponse:
        return JSONResponse({"error": code, "detail": detail}, status_code=status)

    # ---- identity ---------------------------------------------------------------------------

    @api.get("/api/signin/options")
    def signin_options():
        _, emails = principals()
        by_id, _ = principals()
        rows = [{"email": e, "role": by_id[pid].role} for e, pid in sorted(emails.items())]
        return {"pack": settings().get("pack"), "fixture_emails": rows}

    @api.post("/api/signin")
    async def signin(request: Request):
        body = await _json_body(request)
        email = str(body.get("email", "")).strip().lower()
        _, emails = principals()
        if email in emails:
            code = auth.issue_code(email)
            print(f"[sign-in] one-time code for {email}: {code}  (valid {CODE_SECONDS // 60} minutes)", flush=True)
        else:
            print(f"[sign-in] {email!r} is not a fixture email; no code issued", flush=True)
        # The same answer either way, so the page never says which emails exist.
        return {"ok": True, "message": "If that email is in the fixture, a one-time code was printed in the "
                                       "server log."}

    @api.post("/api/verify")
    async def verify(request: Request):
        body = await _json_body(request)
        email = str(body.get("email", "")).strip().lower()
        code = str(body.get("code", "")).strip()
        by_id, emails = principals()
        if email not in emails or not auth.check_code(email, code):
            return error(401, "bad_code", "That code is wrong or has expired. Ask for a new one.")
        principal = by_id[emails[email]]
        token = auth.new_session(principal)
        resp = JSONResponse({"ok": True, "principal": _principal_view(principal)})
        resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=SESSION_SECONDS, path="/")
        return resp

    @api.get("/api/me")
    def me(request: Request):
        s = auth.session(request.cookies.get(SESSION_COOKIE))
        if not s:
            return error(401, "not_signed_in", "Sign in first.")
        return {"principal": _principal_view(s["principal"]), "pack": settings().get("pack")}

    @api.post("/api/signout")
    def signout(request: Request):
        auth.drop(request.cookies.get(SESSION_COOKIE))
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(SESSION_COOKIE, path="/")
        return resp

    # ---- chat -------------------------------------------------------------------------------

    def resolve_principal(request: Request) -> tuple[Optional[Principal], Optional[JSONResponse], Optional[dict]]:
        header = request.headers.get("x-test-principal")
        if header is not None:
            if not (test_mode_active() and exam_token_ok(request)):
                return None, error(403, "test_principal_refused",
                                   "X-Test-Principal needs DW_TEST_MODE=1 and a matching X-Exam-Token."), None
            by_id, _ = principals()
            header = header.strip()
            if header.startswith("{"):
                try:
                    d = json.loads(header)
                    d["id"] = principal_id(d)
                    return principal_from_dict(d), None, None
                except (ValueError, KeyError, TypeError):
                    return None, error(400, "bad_test_principal", "X-Test-Principal is not valid JSON."), None
            if header in by_id:
                return by_id[header], None, None
            return None, error(400, "unknown_test_principal", f"No fixture principal {header!r}."), None
        s = auth.session(request.cookies.get(SESSION_COOKIE))
        if not s:
            return None, error(401, "not_signed_in", "Sign in first."), None
        return s["principal"], None, s

    @api.post("/api/chat")
    async def chat(request: Request):
        principal, refusal, session = resolve_principal(request)
        if refusal is not None:
            return refusal
        body = await _json_body(request)
        text = body.get("text", body.get("message", ""))
        if not isinstance(text, str) or not text.strip():
            return error(400, "empty_message", "Send a non-empty `message`.")
        if len(text) > MAX_TEXT:
            return error(400, "message_too_long", f"A message is at most {MAX_TEXT} characters.")
        request_id = str(body.get("request_id") or uuid.uuid4().hex)
        conversation_id = str(body.get("conversation_id") or "default")
        if not ID_PATTERN.match(request_id) or not ID_PATTERN.match(conversation_id):
            return error(400, "bad_id", "request_id and conversation_id use letters, digits and _.:- only.")
        # Everything about who is speaking comes from `principal`; the body can never set it.
        message = Message(request_id=request_id, conversation_id=conversation_id, principal=principal, text=text)
        import anyio
        try:
            reply = await anyio.to_thread.run_sync(_handle, message)
        except CoreUnavailable as exc:
            return error(503, "agent_core_unavailable", str(exc))
        payload = reply.to_dict(with_eval=test_mode_active())
        if session is not None:
            session["cited"].update(payload.get("citations") or [])
        return payload

    def _handle(message: Message):
        agent = holder.get()
        return agent.handle(message)

    @api.get("/api/docs/{doc_id}")
    def document(doc_id: str, request: Request):
        s = auth.session(request.cookies.get(SESSION_COOKIE))
        if not s:
            return error(401, "not_signed_in", "Sign in first.")
        if not SAFE_NAME.match(doc_id) or doc_id not in s["cited"]:
            return error(404, "not_found", "That document was not cited to you in this session.")
        path = pack_documents(root, settings().get("pack", "quillon")) / f"{doc_id}.md"
        if not path.is_file():
            return error(404, "not_found", "That document is not in the corpus.")
        meta, body = split_front_matter(path.read_text(encoding="utf-8"))
        return {"doc_id": doc_id, "title": meta.get("title", doc_id), "text": body}

    @api.get("/mock-state")
    def mock_state():
        try:
            return holder.mock_state()
        except CoreUnavailable as exc:
            return error(503, "agent_core_unavailable", str(exc))

    # ---- health and runs --------------------------------------------------------------------

    @api.get("/health")
    def health():
        try:
            from app.core import Agent  # noqa: F401  (import only: is the core there?)
            core = "ready" if holder.error is None else f"error: {holder.error}"
        except Exception as exc:
            core = f"unavailable: {type(exc).__name__}"
        served, kept = settings(), store.kept_settings()
        # settings_match: config/settings.toml (what this server answers with) holds the kept run's settings
        match = None if kept is None else all(served.get(k) == v for k, v in kept.items())
        return {"status": "ok", "commit": commit, "fingerprint": store.fingerprint(), "settings_match": match,
                "model": served.get("model", "unknown"), "pack": served.get("pack"), "core": core}

    @api.get("/api/runs")
    def runs(source: str = "runs"):
        return store.listing("reference" if source == "reference" else "runs")

    @api.get("/api/runs/{run_id}")
    def run(run_id: str, cases: int = 1):
        out = store.get(run_id, with_cases=bool(cases))
        if out is None:
            return error(404, "not_found", f"No run {run_id!r}.")
        return out

    @api.get("/api/config/prices")
    def prices():
        path = root / "config" / "prices.toml"
        if not path.is_file():
            return error(404, "not_found", "config/prices.toml is missing.")
        with open(path, "rb") as fh:
            return tomllib.load(fh)

    # ---- static pages -----------------------------------------------------------------------

    static_dir = root / "app" / "static"
    dash_dir = root / "dashboard"

    @api.get("/", include_in_schema=False)
    def index():
        return FileResponse(static_dir / "index.html")

    @api.get("/dashboard", include_in_schema=False)
    def dashboard_index():
        return FileResponse(dash_dir / "index.html")

    @api.get("/dashboard/", include_in_schema=False)
    def dashboard_slash():
        return RedirectResponse("/dashboard", status_code=307)

    if static_dir.is_dir():
        api.mount("/static", StaticFiles(directory=static_dir), name="static")
    if dash_dir.is_dir():
        api.mount("/dashboard", StaticFiles(directory=dash_dir), name="dashboard")

    return api


def _principal_view(p: Principal) -> dict:
    return {"id": p.id, "role": p.role, "verified": p.verified, "account_id": p.account_id}


async def _json_body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


app = create_app()
