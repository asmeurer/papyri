import ast
import sys
import difflib
from textwrap import indent

import numpy as np

import numpydoc.docscrape


class NodeVisitor:
    """
    A node visitor base class that walks the abstract syntax tree and calls a
    visitor function for every node found.  This function may return a value
    which is forwarded by the `visit` method.

    This class is meant to be subclassed, with the subclass adding visitor
    methods.

    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `visit` method.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.

    Don't use the `NodeVisitor` if you want to apply changes to nodes during
    traversing.  For this a special visitor exists (`NodeTransformer`) that
    allows modifications.
    """

    def __init__(self):
        self.items = []

    def visit(self, node):
        """Visit a node."""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        res = []
        try:
            for field, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for item in value:
                        self.visit(item)
                elif isinstance(value, dict):
                    for k, v in value:
                        res.append(self.visit(v))
                    res.append(self.visit(value))
        except AttributeError:
            print("ATTRE:", node)
            pass

    def visit_FunctionDef(self, node):
        # we can collect function args, and _could_ check the Parameter section.
        for nn in node.args.args:
            nnn = nn.arg

        self.items.append(node)
        self.generic_visit(node)


def w(orig):
    ll = []
    for l in orig:
        if l[0] in "+-":
            # ll.append(l.replace(' ', '⎵'))
            ll.append(l.replace(" ", "·"))

        else:
            ll.append(l)
    lll = []
    for l in ll:
        if l.endswith("\n"):
            lll.append(l[:-1])
        else:
            lll.append(l[:])
    return lll


class DocstringFormatter:
    @classmethod
    def format_Signature(self, s, compact):
        return s

    @classmethod
    def format_Summary(self, s, compact):
        if len(s) == 1 and not s[0].strip():
            return ""
        return "\n".join(s) + "\n"

    @classmethod
    def format_Extended_Summary(self, es, compact):
        return "\n".join(es) + "\n"

    @classmethod
    def _format_ps(cls, name, ps, compact):
        res = cls._format_ps_pref(name, ps, compact=True, force_compact=compact)
        if res is not None:
            return res
        return cls._format_ps_pref(name, ps, compact=False, force_compact=compact)

    @classmethod
    def _format_ps_pref(cls, name, ps, *, compact, force_compact):
        out = name + "\n"
        out += "-" * len(name) + "\n"
        for i, p in enumerate(ps):
            if (not compact) and i:
                out += "\n"
            if p.type:
                out += f"""{p.name} : {p.type}\n"""
            else:
                out += f"""{p.name}\n"""
            if p.desc:
                if (
                    any([l.strip() == "" for l in p.desc])
                    and compact
                    and not force_compact
                ):
                    return None

                out += indent("\n".join(p.desc), "    ")
                out += "\n"
        return out

    @classmethod
    def format_Parameters(cls, ps, compact):
        return cls._format_ps("Parameters", ps, compact)

    @classmethod
    def format_Other_Parameters(cls, ps, compact):
        return cls._format_ps("Other Parameters", ps, compact)

    @classmethod
    def format_See_Also(cls, sas, compact):

        res = cls.format_See_Also_impl(sas, True, force_compact=compact)
        if res is not None:
            return res
        return cls.format_See_Also_impl(sas, False, force_compact=compact)

    @classmethod
    def format_See_Also_impl(cls, sas, compact, force_compact):
        out = "See Also\n"
        out += "--------\n"

        for a, b in sas:
            if b:
                desc = b[0]
            else:
                desc = None
            if len(b) > 1:
                rest_desc = b[1:]
            else:
                rest_desc = []
            _first = True
            for ref, type_ in a:
                if not _first:
                    out += ", "
                if type_ is not None:
                    out += f":{type_}:`{ref}`"
                else:
                    out += f"{ref}"
                _first = False

            if desc:
                if len(a) > 1 or (not compact):
                    out += f"\n    {desc}"
                else:
                    attempt = f" : {desc}"
                    if len(out.splitlines()[-1] + attempt) > 75 and not force_compact:
                        return None
                    out += attempt
            for rd in rest_desc:
                out += "\n    " + rd
            out += "\n"
        return out

    @classmethod
    def format_References(cls, lines, compact):
        out = "References\n"
        out += "----------\n"
        out += "\n".join(lines)
        out += "\n"
        return out

    @classmethod
    def format_Notes(cls, lines, compact):
        out = "Notes\n"
        out += "-----\n"
        out += "\n".join(lines)
        out += "\n"
        return out

    @classmethod
    def format_Examples(cls, lines, compact):
        out = "Examples\n"
        out += "--------\n"
        out += "\n".join(lines)
        out += "\n"
        return out

    @classmethod
    def format_Warnings(cls, lines, compact):
        out = "Warnings\n"
        out += "--------\n"
        out += "\n".join(lines)
        out += "\n"
        return out

    @classmethod
    def format_Warns(cls, ps, compact):
        return cls.format_RRY("Warns", ps)

    @classmethod
    def format_Raises(cls, ps, compact):
        return cls.format_RRY("Raises", ps)

    @classmethod
    def format_Yields(cls, ps, compact):
        return cls.format_RRY("Yields", ps)

    @classmethod
    def format_Returns(cls, ps, compact):
        return cls.format_RRY("Returns", ps)

    @classmethod
    def format_Attributes(cls, ps, compact):
        return cls.format_RRY("Attributes", ps)

    @classmethod
    def format_RRY(cls, name, ps):
        out = name + "\n"
        out += "-" * len(name) + "\n"

        if name == "Returns":
            if len(ps) > 1:
                # do heuristic to check we actually have a description list and not a paragraph
                pass

        for i, p in enumerate(ps):
            # if i:
            #    out += "\n"
            if p.name:
                out += f"""{p.name} : {p.type}\n"""
            else:
                out += f"""{p.type}\n"""
            if p.desc:
                out += indent("\n".join(p.desc), "    ")
                out += "\n"

        return out


def test(docstr, fname, *, indempotenty_check):
    fmt = compute_new_doc(docstr, fname)
    dold = docstr.splitlines()
    dnew = fmt.splitlines()
    diffs = list(difflib.unified_diff(dold, dnew, n=100, fromfile=fname, tofile=fname),)
    if diffs:
        from pygments import highlight
        from pygments.lexers import DiffLexer
        from pygments.formatters import TerminalFormatter

        code = "\n".join(w(diffs))
        hldiff = highlight(code, DiffLexer(), TerminalFormatter())

        print(indent(hldiff, " |   ", predicate=lambda x: True))


def dedend_docstring(docstring):
    import textwrap

    lines = docstring.splitlines()
    if len(lines) >= 2:
        l0, *lns = docstring.split("\n")
        l0 = textwrap.dedent(l0)
        lns = textwrap.dedent("\n".join(lns)).split("\n")
        docstring = [l0] + lns
    else:
        docstring = textwrap.dedent(docstring).split("\n")
    return "\n".join(docstring)


def compute_new_doc(docstr, fname, *, indempotenty_check, level, compact):
    INDENT = level * " "
    NINDENT = "\n" + INDENT
    original_docstr = docstr
    if len(docstr.splitlines()) <= 1:
        return ""
    shortdoc = bool(docstr.splitlines()[0].strip())
    short_with_space = False
    if not docstr.startswith(NINDENT):
        # docstr = NINDENT + docstr
        if original_docstr[0] == " ":
            short_with_space = True

    long_end = True
    long_with_space = True
    if original_docstr.splitlines()[-1].strip():
        long_end = False
    if original_docstr.splitlines()[-2].strip():
        long_with_space = False

    doc = numpydoc.docscrape.NumpyDocString(dedend_docstring(docstr))
    print(str(docstr))

    fmt = ""
    start = True
    # ordered_section is a local patch to that records the docstring order.
    for s in getattr(doc, "sections", doc.sections):
        if doc[s]:
            f = getattr(DocstringFormatter, "format_" + s.replace(" ", "_"))
            res = f(doc[s], compact)
            if not res:
                continue
            if not start:
                fmt += "\n"
            start = False
            fmt += res
    fmt = indent(fmt, INDENT) + INDENT

    # hack to detect if we have seen a header section.
    if "----" in fmt:
        if long_with_space:
            fmt = fmt.rstrip(" ") + NINDENT
        else:
            fmt = fmt.rstrip(" ") + INDENT
    if shortdoc:
        fmt = fmt.lstrip()
        if short_with_space:
            fmt = " " + fmt
    else:
        fmt = "\n" + fmt
    if not long_end:
        fmt = fmt.rstrip()
    if indempotenty_check:
        ff = fmt
        # if not ff.startswith(NINDENT):
        #    ff = NINDENT + ff

        d2 = numpydoc.docscrape.NumpyDocString(dedend_docstring(ff))
        if not d2._parsed_data == doc._parsed_data:
            raise ValueError(
                "Numpydoc parsing seem to differ after reformatting, this may be a reformatting bug. Rerun with --unsafe: "
                + str(fname)
                + "\n"
                + str({k: v for k, v in d2._parsed_data.items() if v})
                + "\n"
                + str({k: v for k, v in doc._parsed_data.items() if v}),
            )
    assert fmt
    # we can't just do that as See Also and a few other would be sphinxified.
    # return indent(str(doc),'    ')+'\n    '
    return fmt


def main():
    import argparse

    parser = argparse.ArgumentParser(description="reformat the docstrigns of some file")
    parser.add_argument("files", metavar="files", type=str, nargs="+", help="TODO")
    parser.add_argument("--context", metavar="context", type=int, default=3)
    parser.add_argument("--unsafe", action="store_true")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument(
        "--write", dest="write", action="store_true", help="print the diff"
    )

    args = parser.parse_args()
    to_format = []
    from pathlib import Path

    for f in args.files:
        p = Path(f)
        if p.is_dir():
            for sf in p.glob("**/*.py"):
                to_format.append(sf)
        else:
            to_format.append(p)

    for file in to_format:
        # print(file)
        with open(file, "r") as f:
            data = f.read()

        tree = ast.parse(data)
        new = data

        # funcs = [t for t in tree.body if isinstance(t, ast.FunctionDef)]
        funcs = NodeVisitor()
        funcs.visit(tree)
        funcs = funcs.items
        for i, func in enumerate(funcs[:]):
            # print(i, "==", func.name, "==")
            try:
                e0 = func.body[0]
                if not isinstance(e0, ast.Expr):
                    continue
                # e0.value is _likely_ a Constant node.
                docstring = e0.value.s
            except AttributeError:
                continue
            if not isinstance(docstring, str):
                continue
            start, nindent, stop = (
                func.body[0].lineno,
                func.body[0].col_offset,
                func.body[0].end_lineno,
            )
            if not docstring in data:
                print(f"skip {file}: {func.name}, can't do replacement yet")

            new_doc = compute_new_doc(
                docstring,
                file,
                indempotenty_check=(not args.unsafe),
                level=nindent,
                compact=args.compact,
            )
            # test(docstring, file)
            if new_doc:
                if ('"""' in new_doc) or ("'''" in new_doc):
                    print(
                        "SKIPPING", file, func.name, "triple quote not handled", new_doc
                    )
                else:
                    if docstring not in new:
                        print("ESCAPE issue:", docstring)
                    new = new.replace(docstring, new_doc)

            # test(docstring, file)
        if new != data:
            dold = data.splitlines()
            dnew = new.splitlines()
            diffs = list(
                difflib.unified_diff(
                    dold, dnew, n=args.context, fromfile=str(file), tofile=str(file)
                ),
            )
            from pygments import highlight
            from pygments.lexers import DiffLexer
            from pygments.formatters import TerminalFormatter

            if not args.write:
                code = "\n".join(diffs)
                hldiff = highlight(code, DiffLexer(), TerminalFormatter())

                print(hldiff)
            else:
                with open(file, "w") as f:
                    f.write(new)