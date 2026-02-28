<%inherit file="../app.mako"/>

<%block name="title">${ctx.term}</%block>

<%
lexemes = sorted(ctx.lexemes, key=lambda lex: lex.lexeme)

def id_sort_key(value):
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, str(value))

def fmt_values(meaning_objs):
    if not meaning_objs:
        return "<>"
    ordered = sorted(meaning_objs, key=lambda item: id_sort_key(item.id))
    left = [m.name for m in ordered if m.order == 1]
    right = [m.name for m in ordered if m.order == 2]
    return "<{}, {}>".format(" ".join(left), " ".join(right))
%>

<h2>${ctx.term}</h2>

<p>
  <strong>Frame:</strong> ${h.link(req, ctx.frame)}
</p>
<p>
  <strong>Language:</strong> ${h.link(req, ctx.variety)}
</p>

<table class="table table-striped table-condensed js-table-search-sort">
  <thead>
    <tr>
      <th>Lexeme</th>
      <th>A-class</th>
    </tr>
  </thead>
  <tbody>
    % for lex in lexemes:
      <tr>
        <td>${lex.lexeme}</td>
        <td>${fmt_values(lex.meanings)}</td>
      </tr>
    % endfor
  </tbody>
</table>
