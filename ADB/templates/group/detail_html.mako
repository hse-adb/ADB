<%inherit file="../app.mako"/>

<%block name="title">${ctx.term}</%block>

<%
from clld.web.util.htmllib import literal

lexemes = sorted(ctx.lexemes, key=lambda lex: lex.lexeme)

def id_sort_key(value):
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, str(value))

def fmt_values(meaning_objs):
    if not meaning_objs:
        return "&mdash;"
    ordered = sorted(meaning_objs, key=lambda item: id_sort_key(item.id))
    left = [m.name for m in ordered if m.order == 1]
    right = [m.name for m in ordered if m.order == 2]
    return "&lt;{}, {}&gt;".format(" ".join(left) or "&mdash;", " ".join(right) or "&mdash;")
%>

<h2>
  <a href="${req.route_url('frame', id=ctx.frame.id, _query={'language': ctx.variety.id})}">${ctx.term}</a>
</h2>

<p>
  <strong>Frame:</strong> ${h.link(req, ctx.frame, label=ctx.frame.frame)}
</p>
<p>
  <strong>Language:</strong> ${h.link(req, ctx.variety)}
</p>

<table class="table table-striped table-condensed js-table-search-sort" style="table-layout: fixed; width: 100%;">
  <colgroup>
    <col style="width: 35%;">
    <col style="width: 40%;">
    <col style="width: 25%;">
  </colgroup>
  <thead>
    <tr>
      <th>Lexeme</th>
      <th>Meaning</th>
      <th>A-class</th>
    </tr>
  </thead>
  <tbody>
    % for lex in lexemes:
      <tr>
        <td style="vertical-align: middle;">${lex.lexeme}</td>
        <td style="vertical-align: middle;">${lex.russian or ''}</td>
        <td style="vertical-align: middle; white-space: nowrap;">${literal(fmt_values(lex.meanings))}</td>
      </tr>
    % endfor
  </tbody>
</table>
