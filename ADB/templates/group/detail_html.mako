<%inherit file="../app.mako"/>

<%block name="title">${ctx.term}</%block>

<%
from clld.web.util.htmllib import literal
from ADB.helpers import format_meanings

lexemes = sorted(ctx.lexemes, key=lambda lex: lex.lexeme)
lexeme_meaning_examples = [example for lexeme in lexemes for example in lexeme.examples]
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
        <td style="vertical-align: middle; white-space: nowrap;">${literal(format_meanings(lex.meanings))}</td>
      </tr>
    % endfor
  </tbody>
</table>

% if lexeme_meaning_examples:
<p>
  <strong>Examples:</strong>
</p>
  
<table class="table table-striped table-condensed js-table-search-sort" style="table-layout: fixed; width: 100%;">
  <colgroup>
    <col style="width: 20%;">
    <col style="width: 25%;">
    <col style="width: 10%;">
    <col style="width: 45%;">
  </colgroup>
  <thead>
    <tr>
      <th>Lexeme</th>
      <th>Meaning</th>
      <th>A-meaning</th>
      <th>Example</th>
    </tr>
  </thead>
  <tbody>
    % for lme in lexeme_meaning_examples:
      <tr>
        <td style="vertical-align: middle;">${lme.lexeme.lexeme}</td>
        <td style="vertical-align: middle;">${lme.lexeme.russian}</td>
        <td style="vertical-align: middle;">${lme.meaning}</td>
        <td style="vertical-align: middle; white-space: nowrap;">
          <%include file="../utils/gloss.mako" args="
            primary_text=lme.example.primary_text,
            analyzed_word=lme.example.analyzed_word,
            gloss=lme.example.gloss,
            translated_text=lme.example.translated_text,
            position=lme.position_list,
            grammatical=lme.example.grammaticality_judgement
          "/>
        </td>
      </tr>
    % endfor
  </tbody>
</table>

% endif
