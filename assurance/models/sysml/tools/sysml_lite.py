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
MODEL_FILES = ["LionDriverLibrary.sysml", "Mechanisms.sysml", "Architecture.sysml", "Views.sysml"]
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
  | (?P<sym>::>|:>>|:>|::|\*\*|[{};:=(),<>\[\].*~@])
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
    if kw in ("part", "port", "action", "view", "metadata", "interface", "connection", "attribute"):
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


@dataclass
class View:
  short: str
  name: str
  definition: str
  doc: str
  exposes: list[str]
  render: str


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
      if m.kind == "action" and m.short:
        mechanisms[m.short] = Mechanism(m.short, m.name or "", m.doc, str(m.values.get("covers", "")),
                                        str(m.values.get("dcTarget", "")), _as_list(m.values.get("tsr")))
        mech_names[m.name] = m.short
        mech_names[f"{pkg_decl.name}::{m.name}"] = m.short
  for e in elements.values():
    resolved = []
    for p in e.performs:
      short = mech_names.get(p) or mech_names.get(p.split("::")[-1])
      if short is None:
        raise ModelError(f"{e.path}: perform {p!r} does not name a safety mechanism")
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

  return Model(packages, root, elements, connections, allocations, mechanisms, aliases, views, files)


if __name__ == "__main__":
  m = load()
  parts = [e for e in m.elements.values() if e.kind == "part"]
  print(f"sysml_lite: {len(m.files)} files, {len(parts)} parts, {len(m.elements) - len(parts)} ports, " +
        f"{len(m.connections)} connections, {len(m.allocations)} allocations, {len(m.mechanisms)} mechanisms, " +
        f"{len(m.aliases)} aliases, {len(m.views)} views")
