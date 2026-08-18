#!/usr/bin/env python3
"""hwpx-toolkit CLI. Safe read/edit of 한글(HWPX) files.

All write subcommands: never modify input in place; strip linesegarray on
text changes; verify well-formed; repackage via structure-clone.
"""
import argparse
import sys

import _hwpxlib as lib


def _write(original, out, new_section):
    lib.is_wellformed(new_section)
    lib.repackage(original, out,
                  {lib.SECTION_PATH: new_section.encode("utf-8")})


def cmd_extract(a):
    xml = lib.read_section(a.file)
    if a.paragraphs:
        for i, p in enumerate(lib.paragraph_texts(xml)):
            print("[%d] %s" % (i, p))
    elif a.memos:
        for m in lib.list_memos(xml):
            print("%s\t%s\t%s" % (m["id"], m["author"], m["comment"]))
    elif a.equations:
        for script, n in lib.list_equations(xml).most_common():
            print("%3d  %s" % (n, script))
    else:
        print(lib.plain_text(xml))
    return 0


def cmd_memo_clear(a):
    xml = lib.read_section(a.file)
    new_xml, n = lib.remove_memos(xml)
    new_xml = lib.strip_linesegarray(new_xml)
    _write(a.file, a.out, new_xml)
    print("removed %d memo(s) -> %s" % (n, a.out))
    return 0


def _parse_replace(items):
    pairs = []
    for it in items:
        if "\t" not in it:
            raise SystemExit("--replace needs old<TAB>new: %r" % it)
        old, new = it.split("\t", 1)
        pairs.append((old, new))
    return pairs


def cmd_edit(a):
    xml = lib.read_section(a.file)
    pairs = _parse_replace(a.replace)
    try:
        new_xml, results = lib.apply_replacements(xml, pairs)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    for r in results:
        print("delta %+d  %r -> %r" % (r["delta"], r["old"][:30], r["new"][:30]))
    if a.check:
        print("(--check: no file written)")
        return 0
    new_xml = lib.strip_linesegarray(new_xml)
    _write(a.file, a.out, new_xml)
    print("wrote %s" % a.out)
    return 0


def cmd_figure_swap(a):
    with open(a.png, "rb") as f:
        png = f.read()
    xml = lib.read_section(a.file)
    dims = lib.img_dims(xml)
    pw, ph = lib.png_dimensions(png)
    print("new PNG %dx%d (aspect %.3f)" % (pw, ph, pw / ph))
    for w, h in dims:
        print("  imgDim %dx%d (aspect %.3f)" % (w, h, w / h))
    arc = "BinData/%s.png" % a.slot
    lib.repackage(a.file, a.out, {arc: png})
    print("swapped %s -> %s" % (arc, a.out))
    return 0


def cmd_equation_clone(a):
    xml = lib.read_section(a.file)
    new_xml = lib.clone_equation(xml, a.template, a.anchor)
    new_xml = lib.strip_linesegarray(new_xml)
    _write(a.file, a.out, new_xml)
    print("cloned equation -> %s" % a.out)
    return 0


def cmd_verify(a):
    print(lib.verify(a.file))
    return 0


def cmd_repackage(a):
    reps = {}
    for it in a.replace:
        arc, path = it.split("=", 1)
        with open(path, "rb") as f:
            reps[arc] = f.read()
    lib.repackage(a.original, a.out, reps)
    print("repackaged -> %s" % a.out)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="hwpx")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract")
    e.add_argument("file")
    g = e.add_mutually_exclusive_group()
    g.add_argument("--paragraphs", action="store_true")
    g.add_argument("--memos", action="store_true")
    g.add_argument("--equations", action="store_true")
    e.set_defaults(func=cmd_extract)

    m = sub.add_parser("memo")
    msub = m.add_subparsers(dest="mcmd", required=True)
    mc = msub.add_parser("clear")
    mc.add_argument("file")
    mc.add_argument("-o", "--out", required=True)
    mc.set_defaults(func=cmd_memo_clear)

    ed = sub.add_parser("edit")
    ed.add_argument("file")
    ed.add_argument("-o", "--out", required=True)
    ed.add_argument("--replace", action="append", default=[],
                    help="old<TAB>new (repeatable)")
    ed.add_argument("--check", action="store_true")
    ed.set_defaults(func=cmd_edit)

    fg = sub.add_parser("figure")
    fsub = fg.add_subparsers(dest="fcmd", required=True)
    fs = fsub.add_parser("swap")
    fs.add_argument("file")
    fs.add_argument("-o", "--out", required=True)
    fs.add_argument("--slot", required=True, help="e.g. image2")
    fs.add_argument("--png", required=True)
    fs.set_defaults(func=cmd_figure_swap)

    eq = sub.add_parser("equation")
    esub = eq.add_subparsers(dest="ecmd", required=True)
    ec = esub.add_parser("clone")
    ec.add_argument("file")
    ec.add_argument("-o", "--out", required=True)
    ec.add_argument("--template", required=True)
    ec.add_argument("--anchor", required=True)
    ec.set_defaults(func=cmd_equation_clone)

    v = sub.add_parser("verify")
    v.add_argument("file")
    v.set_defaults(func=cmd_verify)

    rp = sub.add_parser("repackage")
    rp.add_argument("--original", required=True)
    rp.add_argument("-o", "--out", required=True)
    rp.add_argument("--replace", action="append", default=[],
                    help="arcname=path (repeatable)")
    rp.set_defaults(func=cmd_repackage)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
