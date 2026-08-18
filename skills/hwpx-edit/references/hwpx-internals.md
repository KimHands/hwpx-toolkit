# HWPX internals — the XML facts you need to edit safely

HWPX is a ZIP container of OWPML XML. The body text lives in
`Contents/section0.xml` (large documents may have `section1.xml`, ...). Header
styles live in `Contents/header.xml`. Read `Contents/content.hpf` to see the
section list. Everything below is about `section0.xml`.

## Package layout (entry order matters — see repackage script)
```
mimetype            (STORED, MUST be first, content: application/hwp+zip)
version.xml
Contents/header.xml
BinData/*.png       (STORED)
Contents/section0.xml
Preview/PrvImage.png (STORED)  Preview/PrvText.txt
META-INF/*          (manifest.xml is EMPTY — no hashes; container.xml/.rdf)
Contents/content.hpf
settings.xml
```

## Reading the body as plain text
Paragraphs are `<hp:p>…</hp:p>`; visible text is inside `<hp:t>…</hp:t>` runs.
To dump readable text in order:
```python
import re
paras = re.findall(r'<hp:p\b.*?</hp:p>', xml, re.S)
for p in paras:
    txt = "".join(re.findall(r'<hp:t>(.*?)</hp:t>', p, re.S))
    if txt.strip(): print(txt.strip())
```
Note: equation objects (see below) render as EMPTY in this dump — subscripted
terms like `device_key` won't show up as text. Keep that in mind when locating
anchors: anchor on nearby *plain* text, not on a run that contains an equation.

## `linesegarray` — the overlap trap (most important)
Each `<hp:p>` may carry `<hp:linesegarray>…</hp:linesegarray>`: a cache of line
positions (vertpos/baseline/horzsize) computed for the paragraph's *current*
text. If you insert or shift text, downstream paragraphs keep their stale cache
and **HWP renders text on top of itself** (visible overlap the author will
report). Fix: **strip every `<hp:linesegarray>` in the whole section** before
repackaging — HWP recomputes clean layout on open. Never emit linesegarray in
paragraphs you author.
```python
xml = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', xml, flags=re.S)
```

## Citations `[n]` — plain inline text
In-text citations are literal `[8]`, `[4],[5]` inside `<hp:t>`. Renumber by
string replacement, but **use temp tokens to avoid a cascade** (e.g. renaming
`[11]→[12]` must not then be caught by a later `[12]→…`):
```python
for old,tmp in {'[10]':'[T11]','[11]':'[T12]','[12]':'[T15]'}.items():
    body = body.replace(old, tmp)
for tmp,fin in {'[T11]':'[11]','[T12]':'[12]','[T15]':'[15]'}.items():
    body = body.replace(tmp, fin)
```
Split the document at the reference-list heading (`[참고문헌]`) first and only
renumber the part *before* it — the list itself gets rebuilt separately.
Brackets with non-digits (`[표 1]`, `[식 6]`, `[그림 1]`) are safe; only pure
`[digit]` are citations.

## Reference list — plain paragraphs, easy to rebuild
Each entry is a plain paragraph: `<hp:p … paraPrIDRef="26"><hp:run
charPrIDRef="18"><hp:t>[n] …</hp:t></hp:run><hp:linesegarray>…</hp:linesegarray></hp:p>`.
To reorder/renumber (e.g. strict appearance-order), find the contiguous run of
these paragraphs (charPr matching + `<hp:t>` starting `^\[\d+\]\s`), and replace
the whole block with freshly built paragraphs (no linesegarray). Emit `<hp:t>`
text HTML-escaped (`& < >`).

### Strict appearance-order renumbering (when the paper uses 등장순서)
1. Walk `<hp:t>` in body order, collect first-appearance of each `[n]` → the map.
2. Inserting a *new* citation early shifts every later number: recompute the map
   by paragraph position of each citation's first appearance.
3. Apply the old→new map to in-text citations (temp-token) AND rebuild the list
   in the new order. Verify the body's first-appearance sequence is `1,2,…,N`.

## Equations / subscripted terms — `<hp:equation>` objects
Terms like `device_key`, `Session_CEK`, `session_id`, `time_slot` are NOT plain
text — each is a self-contained `<hp:equation id="…">…<hp:script>device
_{key}</hp:script>…</hp:equation>` (HancomEQN script: `_{sub}`, `^{sup}`,
`le`=≤, `ge`=≥, `epsilon`=ε, `larrow`=←). To reuse a term in text you author,
**clone the existing object and give it a fresh unique id** (dup ids can
mis-render), then wrap it in a run:
```python
eq = extract_equation(xml, 'device _{key}')          # the <hp:equation>…</hp:equation>
eq = re.sub(r'(<hp:equation id=")\d+(")', r'\g<1>1150000001\g<2>', eq, count=1)
run = f'<hp:run charPrIDRef="{C}">{eq}</hp:run>'      # C = a body text charPr
```
Authoring a brand-new multi-subscript display equation by hand (e.g. a bound
with `q_k`, `D_prf`) is error-prone. Prefer **prose** ("KDF 질의 횟수", "PRF 구별
이점") unless the author insists on typeset math. This keeps consistency with
[[crypto-paper-subscript-notation]] without fragile HancomEQN authoring.

## Authoring an insert paragraph
Sample `paraPrIDRef` and the text `charPrIDRef` from an adjacent body paragraph
so the new text matches surrounding font/size. Build:
```
<hp:p id="0" paraPrIDRef="{P}" styleIDRef="0" pageBreak="0" columnBreak="0"
      merged="0">{runs}</hp:p>
```
where `{runs}` interleaves `<hp:run charPrIDRef="{C}"><hp:t>…</hp:t></hp:run>`
(escape text) with cloned equation runs. No linesegarray. Insert by finding an
anchor's `<hp:t>` and splicing after the next `</hp:p>`.

## Tables — structural edits are the riskiest
`<hp:tbl rowCnt="R" colCnt="C">` with `<hp:tr>`/`<hp:tc>`. Adding a column means
changing colCnt, adding a `<hp:tc>` (correct `cellAddr colAddr`, `cellSpan`,
`cellSz`, `cellMargin`) to every row, AND recomputing all cell widths to fit the
fixed table width. This is fragile. When low risk matters, prefer expressing the
comparison in prose instead of restructuring the table.
