#!/usr/bin/env python3
"""Read the LionDriver SysML v2 model into Python objects (standard library only).

This is not a SysML v2 implementation. It reads the subset of the textual notation that the
files in ../model use, and refuses anything else with the line it stopped at, so that a new
construct is either added here on purpose or not used. Conformance to SysML v2 is checked
separately by the OMG pilot implementation (tools/pilot/validate.sh, CI job "sysml model").

The reader builds two things:

- the declarations (packages, definitions, usages) as written, and
- the instance tree of `LionDriverArchitecture::context`: every part usage expanded through
  its definition, with paths such as `context.ldsda.safetyFirmware.safetyLayer.core`.

Connections, allocations and `perform` statements are resolved against that tree.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE.parent / "model"
MODEL_FILES = ["LionDriverLibrary.sysml", "Mechanisms.sysml", "Functions.sysml", "Architecture.sysml", "Security.sysml", "Integration.sysml", "Behaviour.sysml", "Requirements.sysml", "Satisfaction.sysml",
               "Verification.sysml", "Needs.sysml", "StateRecords.sysml", "Sequences.sysml", "Lifecycle.sysml", "Timing.sysml",
               "Signals.sysml", "Views.sysml"]
ROOT_USAGE = ("LionDriverArchitecture", "context")


class ModelError(Exception):
  pass


# ---------------------------------------------------------------- tokens

TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)
  | (?P<line>//[^\n]*)
  | (?P<block>/\*.*?\*/)
  | (?P<str>"(?:[^"\\]|\\.)*")
  | (?P<num>[0-9]+(?:\.[0-9]+)?)
  | (?P<qname>'(?:[^'\\]|\\.)*')
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<sym>::>|:>>|:>|::|\*\*|[{};:=(),<>\[\].*~@#])
""", re.S | re.X)


@dataclass
class Tok:
  kind: str
  text: str
  line: int


def tokenize(text: str, fname: str) -> list[Tok]:
  out: list[Tok] = []
  pos, line = 0, 1
  while pos < len(text):
    m = TOKEN_RE.match(text, pos)
    if not m:
      raise ModelError(f"{fname}:{line}: unexpected character {text[pos]!r}")
    kind, s = m.lastgroup, m.group()
    if kind == "block":
      out.append(Tok("block", s, line))
    elif kind not in ("ws", "line"):
      out.append(Tok(kind, s, line))
    line += s.count("\n")
    pos = m.end()
  out.append(Tok("eof", "", line))
  return out


def doc_text(block: str) -> str:
  """Body of a /* ... */ comment without the comment markers and leading asterisks."""
  body = block[2:-2]
  lines = [re.sub(r"^\s*\*\s?", "", ln).rstrip() for ln in body.splitlines()]
  return " ".join(" ".join(lines).split())


# ---------------------------------------------------------------- declarations

@dataclass
class Decl:
  kind: str                 # package, part def, part, port def, port, action, view, ...
  name: str | None
  short: str | None = None
  type: str | None = None   # typed by (`:`)
  supers: list[str] = field(default_factory=list)  # specializes (`:>`)
  doc: str = ""
  meta: dict[str, dict] = field(default_factory=dict)
  values: dict[str, object] = field(default_factory=dict)  # `:>> name = value`
  members: list[Decl] = field(default_factory=list)
  ends: list[tuple[str, str]] = field(default_factory=list)  # connect: (end name, target chain)
  target: str | None = None  # alias for, perform, expose, render, allocate source
  target2: str | None = None  # allocate target
  fname: str = ""
  line: int = 0
  parent: Decl | None = field(default=None, repr=False)

  def member(self, name: str) -> Decl | None:
    for m in self.members:
      if m.name == name or (m.short is not None and m.short == name):
        return m
    return None


def unquote(s: str) -> str:
  return s[1:-1].replace("\\'", "'") if s.startswith("'") else s


class Parser:
  def __init__(self, toks: list[Tok], fname: str):
    self.toks, self.i, self.fname = toks, 0, fname

  # -- token helpers
  def peek(self, k: int = 0) -> Tok:
    j = self.i
    seen = 0
    while True:
      t = self.toks[j]
      if t.kind != "block":
        if seen == k:
          return t
        seen += 1
      j += 1

  def next(self) -> Tok:
    while self.toks[self.i].kind == "block":
      self.i += 1
    t = self.toks[self.i]
    self.i += 1
    return t

  def take_doc_block(self) -> str:
    t = self.toks[self.i]
    if t.kind != "block":
      raise self.error(t, "expected /* ... */ after doc")
    self.i += 1
    return doc_text(t.text)

  def skip_comments(self) -> None:
    while self.toks[self.i].kind == "block":
      self.i += 1

  def error(self, t: Tok, msg: str) -> ModelError:
    return ModelError(f"{self.fname}:{t.line}: {msg} (at {t.text!r})")

  def expect(self, text: str) -> Tok:
    t = self.next()
    if t.text != text:
      raise self.error(t, f"expected {text!r}")
    return t

  def accept(self, text: str) -> bool:
    if self.peek().text == text:
      self.next()
      return True
    return False

  def name(self) -> str:
    t = self.next()
    if t.kind not in ("name", "qname"):
      raise self.error(t, "expected a name")
    return unquote(t.text)

  def qualified(self) -> str:
    """Qualified name or feature chain: A::B::c.d.e, optionally ending in ::* or ::**."""
    parts = [self.name()]
    while self.peek().text in ("::", "."):
      sep = self.next().text
      if self.peek().text in ("*", "**"):
        parts.append(sep + self.next().text)
        break
      parts.append(sep + self.name())
    return "".join(parts)

  def multiplicity(self) -> None:
    if self.accept("["):
      while not self.accept("]"):
        self.next()

  def value(self):
    t = self.peek()
    if t.text == "(":
      self.next()
      vals = [self.value()]
      while self.accept(","):
        vals.append(self.value())
      self.expect(")")
      return vals
    if t.kind == "str":
      self.next()
      return t.text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if t.kind == "num":
      self.next()
      return float(t.text) if "." in t.text else int(t.text)
    if t.text in ("true", "false"):
      self.next()
      return t.text == "true"
    return self.qualified()

  # -- statements
  def parse_file(self) -> list[Decl]:
    out = []
    while self.peek().kind != "eof":
      out.append(self.statement(None))
    return out

  def body(self, d: Decl) -> None:
    if self.accept(";"):
      return
    self.expect("{")
    while not self.accept("}"):
      s = self.statement(d)
      if s is not None:
        s.parent = d
        d.members.append(s)

  def head(self, kind: str, t: Tok) -> Decl:
    """[<short>] [name] [: Type] [:> Super, ...] [multiplicity]"""
    d = Decl(kind, None, fname=self.fname, line=t.line)
    if self.accept("<"):
      d.short = self.name()
      self.expect(">")
    if self.peek().kind in ("name", "qname") and self.peek().text not in ("connect",):
      d.name = self.name()
    self.multiplicity()
    while self.peek().text in (":", ":>"):
      op = self.next().text
      q = self.qualified()
      if op == ":":
        d.type = q
      else:
        d.supers.append(q)
        while self.accept(","):
          d.supers.append(self.qualified())
      self.multiplicity()
    return d

  def statement(self, owner: Decl | None) -> Decl | None:
    self.skip_comments()
    t = self.peek()
    kw = t.text
    if kw == "doc":
      self.next()
      if owner is None:
        raise self.error(t, "doc outside a declaration")
      owner.doc = self.take_doc_block()
      return None
    if kw in ("private", "public"):
      self.next()
      return self.statement(owner)
    if kw == "import":
      self.next()
      d = Decl("import", None, target=self.qualified(), fname=self.fname, line=t.line)
      self.expect(";")
      return d
    if kw == "package":
      self.next()
      d = Decl("package", self.name(), fname=self.fname, line=t.line)
      self.body(d)
      return d
    if kw == "@":
      self.next()
      mname = self.qualified()
      vals: dict[str, object] = {}
      if self.accept("{"):
        while not self.accept("}"):
          self.accept(":>>")
          k = self.name()
          self.expect("=")
          vals[k] = self.value()
          self.expect(";")
      else:
        self.expect(";")
      if owner is None:
        raise self.error(t, "metadata outside a declaration")
      owner.meta[mname] = vals
      return None
    if kw == ":>>":
      self.next()
      k = self.name()
      self.expect("=")
      v = self.value()
      self.expect(";")
      if owner is None:
        raise self.error(t, "redefinition outside a declaration")
      owner.values[k] = v
      return None
    if kw == "alias":
      self.next()
      d = Decl("alias", self.name(), fname=self.fname, line=t.line)
      self.expect("for")
      d.target = self.qualified()
      self.expect(";")
      return d
    if kw in ("perform", "expose", "render"):
      self.next()
      d = Decl(kw, None, target=self.qualified(), fname=self.fname, line=t.line)
      self.expect(";")
      return d
    if kw == "allocate":
      self.next()
      d = Decl("allocate", None, target=self.qualified(), fname=self.fname, line=t.line)
      self.expect("to")
      d.target2 = self.qualified()
      self.expect(";")
      return d
    if kw == "connect":
      self.next()
      d = Decl("connect", None, fname=self.fname, line=t.line)
      self.connect_ends(d)
      self.body(d)
      return d
    if kw == "end" and self.peek(1).text == "#":
      # end of a #derivation connection: end #original ::> chain;  /  end #derive ::> chain;
      self.next()
      self.next()
      d = Decl("end role", self.name(), fname=self.fname, line=t.line)
      self.expect("::>")
      d.target = self.qualified()
      self.expect(";")
      return d
    if kw == "#":
      self.next()
      prefix = self.name()
      if prefix != "derivation" or self.peek().text != "connection":
        raise self.error(t, "only '#derivation connection' is supported")
      self.next()
      d = self.head("derivation", t)
      self.body(d)
      return d
    if kw == "satisfy":
      self.next()
      self.accept("requirement")
      d = Decl("satisfy", None, target=self.qualified(), fname=self.fname, line=t.line)
      self.expect("by")
      d.target2 = self.qualified()
      self.expect(";")
      return d
    if kw == "verify":
      self.next()
      self.accept("requirement")
      d = Decl("verify", None, target=self.qualified(), fname=self.fname, line=t.line)
      self.expect(";")
      return d
    if kw == "require":
      # require <requirement>;  (inside a use case objective: the need the use case serves)
      self.next()
      d = Decl("require", None, target=self.qualified(), fname=self.fname, line=t.line)
      self.expect(";")
      return d
    if kw in ("subject", "actor", "stakeholder"):
      # subject name : Type;  /  subject :>> name;  (also actor, stakeholder: parameters of cases and requirements)
      self.next()
      if self.accept(":>>"):
        d = Decl(kw, None, target=self.qualified(), fname=self.fname, line=t.line)
      else:
        d = self.head(kw, t)
      self.expect(";")
      return d
    if kw == "message":
      # message [<short>] name from <lifeline> to <lifeline> (; | { body })
      self.next()
      d = Decl("message", None, fname=self.fname, line=t.line)
      if self.accept("<"):
        d.short = self.name()
        self.expect(">")
      d.name = self.name()
      self.expect("from")
      d.target = self.qualified()
      self.expect("to")
      d.target2 = self.qualified()
      self.body(d)
      return d
    if kw == "first":
      # first <a> then <b>;  (a succession: b happens after a)
      self.next()
      d = Decl("succession", None, target=self.qualified(), fname=self.fname, line=t.line)
      self.expect("then")
      d.target2 = self.qualified()
      self.expect(";")
      return d
    if kw == "use" and self.peek(1).text == "case":
      self.next()
      self.next()
      kind = "use case def" if self.accept("def") else "use case"
      d = self.head(kind, t)
      self.body(d)
      return d
    if kw == "objective":
      self.next()
      d = Decl("objective", None, fname=self.fname, line=t.line)
      self.body(d)
      return d
    if kw == "end":
      self.next()
      k = self.next()
      if k.text not in ("port", "part"):
        raise self.error(k, "expected 'end port' or 'end part'")
      d = self.head("end " + k.text, t)
      self.body(d)
      return d
    if kw == "enum":
      self.next()
      if self.accept("def"):
        d = self.head("enum def", t)
        self.body(d)
        return d
      d = Decl("enum", self.name(), fname=self.fname, line=t.line)
      self.expect(";")
      return d
    if kw == "entry":
      # entry; then <state>;  (the initial state of a state definition or composite state)
      self.next()
      self.expect(";")
      d = Decl("entry", None, fname=self.fname, line=t.line)
      if self.accept("then"):
        d.target = self.qualified()
        self.expect(";")
      return d
    if kw == "transition":
      # transition [<short>] name first <source> then <target> (; | { body })
      self.next()
      d = Decl("transition", None, fname=self.fname, line=t.line)
      if self.accept("<"):
        d.short = self.name()
        self.expect(">")
      if self.peek().text != "first":
        d.name = self.name()
      self.expect("first")
      d.target = self.qualified()
      self.expect("then")
      d.target2 = self.qualified()
      self.body(d)
      return d
    if kw in ("part", "port", "action", "view", "metadata", "interface", "connection", "attribute", "requirement",
              "verification", "state", "occurrence", "constraint", "item"):
      self.next()
      is_def = self.accept("def")
      kind = kw + (" def" if is_def else "")
      if kind == "metadata":
        raise self.error(t, "metadata usages are written with @")
      d = self.head(kind, t)
      if kw in ("interface", "connection") and not is_def:
        self.expect("connect")
        self.connect_ends(d)
      self.body(d)
      return d
    raise self.error(t, "construct not supported by sysml_lite (extend the reader or use the pilot)")

  def connect_ends(self, d: Decl) -> None:
    def end() -> tuple[str, str]:
      if self.peek(1).text == "::>":
        n = self.name()
        self.next()
        return n, self.qualified()
      return "", self.qualified()
    d.ends.append(end())
    self.expect("to")
    d.ends.append(end())


def parse_text(text: str, fname: str = "<text>") -> list[Decl]:
  return Parser(tokenize(text, fname), fname).parse_file()


# ---------------------------------------------------------------- instance model

@dataclass
class Element:
  path: str
  name: str
  short: str | None
  definition: str | None
  kind: str               # part, port
  decl: Decl
  doc: str = ""
  meta: dict[str, dict] = field(default_factory=dict)
  children: list[Element] = field(default_factory=list)
  ports: list[Element] = field(default_factory=list)
  performs: list[str] = field(default_factory=list)   # mechanism short names
  parent: Element | None = field(default=None, repr=False)
  classes: list[str] = field(default_factory=list)    # definition and its supertypes

  @property
  def ident(self) -> str:
    return self.short or self.name

  def walk(self):
    yield self
    for c in self.children:
      yield from c.walk()

  def ancestors(self):
    e = self.parent
    while e is not None:
      yield e
      e = e.parent

  def integrity(self) -> str | None:
    """Integrity from the nearest @Safety on this element or an ancestor."""
    for e in (self, *self.ancestors()):
      s = e.meta.get("Safety")
      if s and "integrity" in s:
        return str(s["integrity"]).split("::")[-1]
    return None

  def scope(self) -> str:
    for e in (self, *self.ancestors()):
      b = e.meta.get("Boundary")
      if b and "scope" in b:
        return str(b["scope"]).split("::")[-1]
    return "inside"

  def zone(self) -> str | None:
    """Security zone from the nearest @Zone on this element or an ancestor (WP-S-07 §3.1)."""
    for e in (self, *self.ancestors()):
      z = e.meta.get("Zone")
      if z and "id" in z:
        return str(z["id"])
    return None


@dataclass
class Connection:
  name: str | None
  kind: str               # interface, connection, connect
  definition: str | None
  ends: list[str]         # element paths (ports resolved to their owning element in `owners`)
  end_ports: list[str]    # the port paths as written (or element paths for part-to-part connects)
  owner: str
  doc: str
  meta: dict[str, dict]
  values: dict[str, object]
  decl: Decl

  @property
  def interface_id(self) -> str | None:
    m = self.meta.get("InterfaceId")
    return m.get("id") if m else None


@dataclass
class Mechanism:
  short: str
  name: str
  doc: str
  covers: str
  dc_target: str
  tsr: list[str]
  performers: list[str] = field(default_factory=list)  # element paths
  values: dict[str, object] = field(default_factory=dict)  # every attribute as written


@dataclass
class Step:
  short: str
  name: str
  doc: str
  stage: str
  function: str                                        # short of the function it belongs to
  performers: list[str] = field(default_factory=list)  # element paths


@dataclass
class Record:
  """A package-level usage read for its attributes only: a security zone or a trust boundary."""
  short: str
  name: str
  doc: str
  values: dict[str, object]


@dataclass
class State:
  path: str            # dotted path inside the state definition (engaged.enabled)
  doc: str
  meta: dict[str, dict]
  children: list[str] = field(default_factory=list)
  initial: str | None = None


@dataclass
class Transition:
  name: str
  source: str          # state path
  target: str
  doc: str
  meta: dict[str, dict]


@dataclass
class StateMachine:
  short: str
  name: str
  doc: str
  meta: dict[str, dict]
  states: dict[str, State] = field(default_factory=dict)
  transitions: list[Transition] = field(default_factory=list)
  initial: str | None = None


def _state_machine(d: Decl) -> StateMachine:
  sm = StateMachine(d.short or d.name or "", d.name or "", d.doc, dict(d.meta))

  def walk(decl: Decl, prefix: str, parent: State | None):
    for m in decl.members:
      if m.kind == "state":
        path = f"{prefix}{m.name}"
        st = State(path, m.doc, dict(m.meta))
        sm.states[path] = st
        if parent is not None:
          parent.children.append(path)
        walk(m, path + ".", st)
      elif m.kind == "entry" and m.target:
        if parent is None:
          sm.initial = prefix + m.target
        else:
          parent.initial = prefix + m.target
      elif m.kind == "transition":
        sm.transitions.append(Transition(m.name or m.short or "", prefix + m.target, prefix + m.target2, m.doc,
                                         dict(m.meta)))
  walk(d, "", None)
  for t in sm.transitions:
    for end in (t.source, t.target):
      if end not in sm.states:
        raise ModelError(f"{d.fname}:{d.line}: transition {t.name} names state {end!r}, which {sm.short} does not have")
  if sm.initial not in sm.states:
    raise ModelError(f"{d.fname}:{d.line}: {sm.short} has no initial state (entry; then …)")
  return sm


@dataclass
class Message:
  short: str
  name: str
  doc: str
  source: str          # lifeline name
  target: str
  meta: dict[str, dict]


@dataclass
class Sequence:
  short: str
  name: str
  doc: str
  lifelines: list[tuple[str, str]]                      # (name, element identifier it stands for)
  messages: list[Message] = field(default_factory=list)  # in the order of the successions


def _sequence(d: Decl) -> Sequence:
  lifelines = [(m.name, str(m.values.get("element", ""))) for m in d.members if m.kind == "part" and m.name]
  names = {n for n, _ in lifelines}
  msgs = {}
  for m in d.members:
    if m.kind == "message":
      for end in (m.target, m.target2):
        if end not in names:
          raise ModelError(f"{m.fname}:{m.line}: message {m.short or m.name} names {end!r}, which is not a lifeline of {d.short}")
      msgs[m.name] = Message(m.short or m.name, m.name, m.doc, m.target, m.target2, dict(m.meta))
  nxt, has_pred = {}, set()
  for m in d.members:
    if m.kind == "succession":
      for end in (m.target, m.target2):
        if end not in msgs:
          raise ModelError(f"{m.fname}:{m.line}: succession names {end!r}, which is not a message of {d.short}")
      if m.target in nxt or m.target2 in has_pred:
        raise ModelError(f"{m.fname}:{m.line}: the messages of {d.short} must form one chain")
      nxt[m.target] = m.target2
      has_pred.add(m.target2)
  starts = [n for n in msgs if n not in has_pred]
  if len(starts) != 1:
    raise ModelError(f"{d.fname}:{d.line}: the messages of {d.short} must form one chain ({len(starts)} start messages)")
  order, cur = [], starts[0]
  while cur is not None:
    order.append(msgs[cur])
    cur = nxt.get(cur)
  if len(order) != len(msgs):
    raise ModelError(f"{d.fname}:{d.line}: the messages of {d.short} must form one chain")
  return Sequence(d.short or d.name or "", d.name or "", d.doc, lifelines, order)


@dataclass
class Function:
  short: str
  name: str
  doc: str
  steps: list[Step] = field(default_factory=list)


@dataclass
class UseCase:
  short: str
  name: str
  doc: str
  goal: str                                            # doc of its objective
  actors: list[tuple[str, str]]                        # (name, actor definition)
  functions: list[str] = field(default_factory=list)   # shorts of the functions it performs
  needs: list[str] = field(default_factory=list)       # requirement shorts its objective requires


@dataclass
class Requirement:
  short: str
  name: str
  definition: str           # SystemRequirement, TechnicalSafetyRequirement, ...
  doc: str
  values: dict[str, object]
  package: str
  derived_from: list[str] = field(default_factory=list)   # requirement shorts this one is derived from
  satisfied_by: list[str] = field(default_factory=list)   # element paths
  verified_by: list[str] = field(default_factory=list)    # verification case shorts
  stakeholders: list[tuple[str, str]] = field(default_factory=list)  # (name, definition) of its stakeholder parameters


@dataclass
class Verification:
  short: str
  name: str
  definition: str
  doc: str
  values: dict[str, object]
  verifies: list[str] = field(default_factory=list)       # requirement shorts


@dataclass
class View:
  short: str
  name: str
  definition: str
  doc: str
  exposes: list[str]
  render: str


@dataclass
class Activity:
  """An action def whose actions are phases (LifecyclePhase), each with the actions it contains, and the successions
  between the phases."""
  name: str
  doc: str
  phases: list[Record]                                   # in the order of the model
  steps: dict[str, list[Record]]                        # phase name -> its actions
  flows: list[tuple[str, str]]                          # (from phase, to phase); "start" and "done" as in SysML v2


@dataclass
class Model:
  packages: dict[str, Decl]
  root: Element
  elements: dict[str, Element]
  connections: list[Connection]
  allocations: list[tuple[str, str]]
  mechanisms: dict[str, Mechanism]
  aliases: dict[str, str]           # alias name -> element path
  views: dict[str, View]
  files: list[Path]
  requirements: dict[str, Requirement] = field(default_factory=dict)
  verifications: dict[str, Verification] = field(default_factory=dict)
  functions: dict[str, Function] = field(default_factory=dict)
  zones: dict[str, Record] = field(default_factory=dict)
  boundaries: dict[str, Record] = field(default_factory=dict)
  integration: dict[str, Record] = field(default_factory=dict)  # steps I-n of WP-S-08 §3.1
  state_machines: dict[str, StateMachine] = field(default_factory=dict)
  use_cases: dict[str, UseCase] = field(default_factory=dict)
  sequences: dict[str, Sequence] = field(default_factory=dict)
  budgets: dict[str, Record] = field(default_factory=dict)       # timing budgets of WP-S-04 §3.7, by row label
  signals: dict[str, Record] = field(default_factory=dict)       # HSI signals S-nn of WP-S-05 §11
  responsibilities: dict[str, Record] = field(default_factory=dict)  # HW/SW responsibilities HSI-nn of WP-S-05 §11.4
  activities: dict[str, Activity] = field(default_factory=dict)     # action defs made of phases (WP-S-06 §3)
  code_times: dict[str, Record] = field(default_factory=dict)       # code-derived times T-nn of WP-S-04 §4
  reactions: dict[str, Record] = field(default_factory=dict)        # fault reaction times of WP-S-04 §5, by fault class

  def by_ident(self) -> dict[str, Element]:
    return {e.short: e for e in self.elements.values() if e.short}

  def find(self, ident: str) -> Element | None:
    e = self.by_ident().get(ident)
    if e is None and ident in self.aliases:
      e = self.elements.get(self.aliases[ident])
    return e

  def owner_element(self, path: str) -> Element:
    """The part an element path or port path belongs to."""
    while path not in self.elements or self.elements[path].kind != "part":
      if "." not in path:
        raise ModelError(f"no element for {path}")
      path = path.rsplit(".", 1)[0]
    return self.elements[path]


def _as_list(v) -> list[str]:
  if v is None:
    return []
  return [str(x) for x in v] if isinstance(v, list) else [str(v)]


class Resolver:
  def __init__(self, packages: dict[str, Decl]):
    self.packages = packages
    self.defs: dict[str, Decl] = {}
    for pkg in packages.values():
      for m in pkg.members:
        if m.kind.endswith(" def") and m.name:
          self.defs[m.name] = m

  def lookup_def(self, q: str | None) -> Decl | None:
    if q is None:
      return None
    return self.defs.get(q.split("::")[-1])

  def def_chain(self, q: str | None) -> list[Decl]:
    out, todo = [], [q]
    while todo:
      d = self.lookup_def(todo.pop(0))
      if d is not None and d not in out:
        out.append(d)
        todo.extend(d.supers)
    return out

  def usage_members(self, usage: Decl) -> list[Decl]:
    """Members of a usage: those of its definition chain, then its own (which win by name)."""
    merged: dict[str, Decl] = {}
    order: list[str] = []
    anon = 0
    for src in [*reversed(self.def_chain(usage.type)), usage] if usage.kind != "part def" else [usage]:
      for m in src.members:
        key = m.name or m.short
        if key is None:
          anon += 1
          key = f"#{anon}"
        if key not in merged:
          order.append(key)
        merged[key] = m
    return [merged[k] for k in order]

  def instantiate(self, usage: Decl, path: str, parent: Element | None) -> Element:
    defs = self.def_chain(usage.type)
    e = Element(path=path, name=usage.name or usage.short or "", short=usage.short,
                definition=usage.type.split("::")[-1] if usage.type else None,
                kind=usage.kind, decl=usage, parent=parent,
                classes=[d.name for d in defs if d.name])
    e.doc = usage.doc or next((d.doc for d in defs if d.doc), "")
    for d in reversed(defs):
      e.meta.update({k: v for k, v in d.meta.items() if k == "Source"})
    e.meta.update(usage.meta)
    for m in self.usage_members(usage):
      if m.kind == "part" and m.name:
        e.children.append(self.instantiate(m, f"{path}.{m.name}", e))
      elif m.kind == "port" and m.name:
        e.ports.append(self.instantiate(m, f"{path}.{m.name}", e))
      elif m.kind == "perform":
        e.performs.append(m.target)
    return e


def load(files: list[Path] | None = None) -> Model:
  files = files or [MODEL_DIR / f for f in MODEL_FILES]
  packages: dict[str, Decl] = {}
  for f in files:
    for d in parse_text(f.read_text(encoding="utf-8"), f.name):
      if d.kind != "package":
        raise ModelError(f"{f.name}:{d.line}: top-level declarations must be packages")
      packages[d.name] = d
  r = Resolver(packages)

  pkg, usage_name = ROOT_USAGE
  root_decl = packages[pkg].member(usage_name)
  if root_decl is None:
    raise ModelError(f"{pkg}::{usage_name} not found")
  root = r.instantiate(root_decl, usage_name, None)

  elements: dict[str, Element] = {}

  def index(e: Element):
    elements[e.path] = e
    for p in e.ports:
      elements[p.path] = p
    for c in e.children:
      index(c)
  index(root)

  # definition-scoped names (LdSda::safetyFirmware) -> first instance path that realises them
  def_paths: dict[str, str] = {}
  for e in elements.values():
    if e.parent is not None and e.parent.definition:
      def_paths.setdefault(f"{e.parent.definition}::{e.name}", e.path)

  def resolve_chain(owner: str, chain: str, where: Decl) -> str:
    p = f"{owner}.{chain}"
    if p not in elements:
      raise ModelError(f"{where.fname}:{where.line}: cannot resolve {chain!r} from {owner}")
    return p

  # connections, allocations: declared inside definitions; resolve them for each instance
  connections: list[Connection] = []
  allocations: list[tuple[str, str]] = []
  for e in list(elements.values()):
    if e.kind != "part":
      continue
    for m in r.usage_members(e.decl):
      if m.kind in ("interface", "connection", "connect"):
        ends = [resolve_chain(e.path, chain, m) for _, chain in m.ends]
        owners = []
        for p in ends:
          owners.append(p if elements[p].kind == "part" else elements[p].parent.path)
        defs = r.def_chain(m.type)
        doc = m.doc
        values = {k: v for d in reversed(defs) for k, v in d.values.items()}
        values.update(m.values)
        connections.append(Connection(m.name, m.kind, m.type.split("::")[-1] if m.type else None,
                                      owners, ends, e.path, doc, dict(m.meta), values, m))
      elif m.kind == "allocate":
        allocations.append((resolve_chain(e.path, m.target, m), resolve_chain(e.path, m.target2, m)))

  # mechanisms
  mechanisms: dict[str, Mechanism] = {}
  mech_names: dict[str, str] = {}
  for pkg_decl in packages.values():
    for m in pkg_decl.members:
      if m.kind == "action" and m.short and m.type == "SafetyMechanism":
        mechanisms[m.short] = Mechanism(m.short, m.name or "", m.doc, str(m.values.get("covers", "")),
                                        str(m.values.get("dcTarget", "")), _as_list(m.values.get("tsr")),
                                        values=dict(m.values))
        mech_names[m.name] = m.short
        mech_names[f"{pkg_decl.name}::{m.name}"] = m.short
  # functions and their steps (LionDriverFunctions)
  functions: dict[str, Function] = {}
  step_names: dict[str, Step] = {}
  for pkg_decl in packages.values():
    for m in pkg_decl.members:
      if m.kind == "action" and m.short and m.type == "ItemFunction":
        f = Function(m.short, m.name or "", m.doc)
        for st in m.members:
          if st.kind == "action" and st.type == "FunctionStep":
            if not st.short:
              raise ModelError(f"{st.fname}:{st.line}: step of {m.short} has no short name")
            step = Step(st.short, st.name or "", st.doc, str(st.values.get("stage", "")).split("::")[-1], m.short)
            f.steps.append(step)
            for key in (f"{m.name}.{st.name}", f"{pkg_decl.name}::{m.name}.{st.name}"):
              step_names[key] = step
        functions[m.short] = f
  for e in elements.values():
    resolved = []
    for p in e.performs:
      step = step_names.get(p) or step_names.get(p.split("::")[-1])
      if step is not None:
        step.performers.append(e.path)
        continue
      short = mech_names.get(p) or mech_names.get(p.split("::")[-1])
      if short is None:
        raise ModelError(f"{e.path}: perform {p!r} does not name a safety mechanism or a function step")
      resolved.append(short)
      mechanisms[short].performers.append(e.path)
    e.performs = resolved

  # aliases
  aliases: dict[str, str] = {}
  for pkg_decl in packages.values():
    for m in pkg_decl.members:
      if m.kind == "alias":
        tgt = def_paths.get(m.target) or def_paths.get("::".join(m.target.split("::")[-2:]))
        if tgt is None:
          raise ModelError(f"{m.fname}:{m.line}: alias target {m.target!r} is not part of the instance tree")
        aliases[m.name] = tgt

  # views
  views: dict[str, View] = {}
  for pkg_decl in packages.values():
    for m in pkg_decl.members:
      if m.kind == "view" and m.short:
        views[m.short] = View(m.short, m.name or "", (m.type or "").split("::")[-1], m.doc,
                              [x.target for x in m.members if x.kind == "expose"],
                              next((x.target.split("::")[-1] for x in m.members if x.kind == "render"), ""))

  shorts = [e.short for e in elements.values() if e.short]
  dupes = sorted({s for s in shorts if shorts.count(s) > 1})
  if dupes:
    raise ModelError(f"short names used more than once in the instance tree: {', '.join(dupes)}")

  requirements, verifications = _requirements(packages, elements)
  use_cases = _use_cases(packages, requirements, functions)
  zones: dict[str, Record] = {}
  boundaries: dict[str, Record] = {}
  integration: dict[str, Record] = {}
  state_machines: dict[str, StateMachine] = {}
  sequences: dict[str, Sequence] = {}
  budgets: dict[str, Record] = {}
  signals: dict[str, Record] = {}
  responsibilities: dict[str, Record] = {}
  activities: dict[str, Activity] = {}
  code_times: dict[str, Record] = {}
  reactions: dict[str, Record] = {}
  for pkg_decl in packages.values():
    for m in pkg_decl.members:
      if m.kind == "part" and m.short and m.type in ("SecurityZone", "TrustBoundary"):
        rec = Record(m.short, m.name or "", m.doc, dict(m.values))
        (zones if m.type == "SecurityZone" else boundaries)[m.short] = rec
      if m.kind == "action" and m.short and m.type == "IntegrationStep":
        integration[m.short] = Record(m.short, m.name or "", m.doc, dict(m.values))
      if m.kind == "state def":
        sm = _state_machine(m)
        state_machines[sm.short] = sm
      if m.kind == "constraint" and m.short and m.type == "TimingBudget":
        budgets[m.short] = Record(m.short, m.name or "", m.doc, dict(m.values))
      if m.kind == "constraint" and m.short and m.type == "FaultReactionTime":
        reactions[m.short] = Record(m.short, m.name or "", m.doc, dict(m.values))
      if m.kind == "item" and m.short and m.type == "CodeDerivedTime":
        code_times[m.short] = Record(m.short, m.name or "", m.doc, dict(m.values))
      if m.kind == "item" and m.short and m.type == "Signal":
        signals[m.short] = Record(m.short, m.name or "", m.doc, dict(m.values))
      if m.kind == "item" and m.short and m.type == "HsiResponsibility":
        responsibilities[m.short] = Record(m.short, m.name or "", m.doc, dict(m.values))
      if m.kind == "occurrence def" and m.short:
        sq = _sequence(m)
        sequences[sq.short] = sq
      if m.kind == "action def" and any(x.kind == "action" and x.type == "LifecyclePhase" for x in m.members):
        phases = [x for x in m.members if x.kind == "action" and x.type == "LifecyclePhase"]
        names = {x.name for x in phases} | {"start", "done"}  # start and done: the start and end of every action
        flows = [(x.target, x.target2) for x in m.members if x.kind == "succession"]
        for a, b in flows:
          if a not in names or b not in names:
            raise ModelError(f"{m.fname}:{m.line}: succession {a} then {b} joins something that is not a phase of {m.name}")
        activities[m.name] = Activity(
          m.name, m.doc, [Record(str(x.values.get("section", "")), x.name, x.doc, dict(x.values)) for x in phases],
          {x.name: [Record(y.name, y.name, y.doc, dict(y.values)) for y in x.members if y.kind == "action"] for x in phases},
          flows)
  for e in elements.values():
    z = (e.meta.get("Zone") or {}).get("id")
    if z is not None and zones and z not in zones:
      raise ModelError(f"{e.path}: @Zone names {z!r}, which is not a security zone")
  return Model(packages, root, elements, connections, allocations, mechanisms, aliases, views, files,
               requirements, verifications, functions, zones, boundaries, integration, state_machines, use_cases, sequences, budgets, signals,
               responsibilities, activities, code_times, reactions)


def _use_cases(packages: dict[str, Decl], reqs: dict[str, Requirement], functions: dict[str, Function]) -> dict[str, UseCase]:
  """Use cases with their actors, the functions they perform and the needs their objective requires."""
  by_name = {r.name: s for s, r in reqs.items()}
  fn_names = {f.name: s for s, f in functions.items()}
  out: dict[str, UseCase] = {}
  for pkg in packages.values():
    for m in pkg.members:
      if m.kind != "use case":
        continue
      if not m.short or not m.name:
        raise ModelError(f"{m.fname}:{m.line}: a use case needs a short name (its ID) and a name")
      goal, needs = "", []
      for o in (x for x in m.members if x.kind == "objective"):
        goal = o.doc
        for x in o.members:
          if x.kind == "require":
            short = by_name.get(x.target.split("::")[-1])
            if short is None:
              raise ModelError(f"{x.fname}:{x.line}: {x.target!r} does not name a requirement")
            needs.append(short)
      fns = []
      for x in m.members:
        if x.kind == "perform":
          short = fn_names.get(x.target.split("::")[-1])
          if short is None:
            raise ModelError(f"{x.fname}:{x.line}: use case {m.short} performs {x.target!r}, which is not a function")
          fns.append(short)
      out[m.short] = UseCase(m.short, m.name, m.doc, goal,
                             [(x.name, (x.type or "").split("::")[-1]) for x in m.members if x.kind == "actor" and x.name],
                             fns, needs)
  return out


def _requirements(packages: dict[str, Decl], elements: dict[str, Element]):
  """Requirement and verification usages, with derivation, satisfy and verify relationships resolved."""
  reqs: dict[str, Requirement] = {}
  by_name: dict[str, str] = {}
  vers: dict[str, Verification] = {}
  for pkg in packages.values():
    for m in pkg.members:
      if m.kind == "requirement":
        if not m.short or not m.name:
          raise ModelError(f"{m.fname}:{m.line}: a requirement needs a short name (its ID) and a name")
        if m.short in reqs:
          raise ModelError(f"{m.fname}:{m.line}: requirement {m.short} declared twice")
        reqs[m.short] = Requirement(m.short, m.name, (m.type or "").split("::")[-1], m.doc, dict(m.values), pkg.name,
                                    stakeholders=[(x.name, (x.type or "").split("::")[-1]) for x in m.members
                                                  if x.kind == "stakeholder" and x.name])
        by_name[m.name] = by_name[f"{pkg.name}::{m.name}"] = m.short

  def req(q: str, where: Decl) -> str:
    short = by_name.get(q) or by_name.get(q.split("::")[-1])
    if short is None:
      raise ModelError(f"{where.fname}:{where.line}: {q!r} does not name a requirement")
    return short

  for pkg in packages.values():
    for m in pkg.members:
      if m.kind == "derivation":
        roles = {x.name: x.target for x in m.members if x.kind == "end role"}
        if set(roles) != {"original", "derive"}:
          raise ModelError(f"{m.fname}:{m.line}: a derivation needs exactly one #original and one #derive end")
        reqs[req(roles["derive"], m)].derived_from.append(req(roles["original"], m))
      elif m.kind == "satisfy":
        r = req(m.target, m)
        path = m.target2
        if path.startswith(f"{ROOT_USAGE[0]}::"):
          path = path.split("::", 1)[1]
        if path not in elements:
          raise ModelError(f"{m.fname}:{m.line}: satisfy target {m.target2!r} is not an element of the instance tree")
        reqs[r].satisfied_by.append(path)
      elif m.kind == "verification":
        if not m.short:
          raise ModelError(f"{m.fname}:{m.line}: a verification case needs a short name (its ID)")
        v = Verification(m.short, m.name or "", (m.type or "").split("::")[-1], m.doc, dict(m.values))
        for o in m.members:
          if o.kind == "objective":
            for x in o.members:
              if x.kind == "verify":
                v.verifies.append(req(x.target, x))
        for r in v.verifies:
          reqs[r].verified_by.append(v.short)
        vers[v.short] = v
  return reqs, vers


if __name__ == "__main__":
  m = load()
  parts = [e for e in m.elements.values() if e.kind == "part"]
  print(f"sysml_lite: {len(m.files)} files, {len(parts)} parts, {len(m.elements) - len(parts)} ports, " +
        f"{len(m.connections)} connections, {len(m.allocations)} allocations, {len(m.mechanisms)} mechanisms, " +
        f"{len(m.aliases)} aliases, {len(m.views)} views, {len(m.requirements)} requirements, " +
        f"{len(m.verifications)} verification cases")
