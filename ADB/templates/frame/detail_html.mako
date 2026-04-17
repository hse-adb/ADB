<%inherit file="../app.mako"/>
<%! active_menu_item = "frames" %>

<%block name="title">${ctx.frame}</%block>

<%
from clld.db.meta import DBSession
from sqlalchemy.orm import joinedload
from clld.web.maps import SelectedLanguagesMap
from ADB import models

language_id = req.params.get('language')
language = None
if language_id:
    language = DBSession.query(models.Variety).filter(models.Variety.id == language_id).first()

languages = (
    DBSession.query(models.Variety)
    .join(models.Group, models.Group.variety_pk == models.Variety.pk)
    .filter(models.Group.frame_pk == ctx.pk)
    .distinct()
    .order_by(models.Variety.name)
    .all()
)

language_meanings = {}
for language_obj, meaning in (
    DBSession.query(models.Variety, models.Meaning)
    .join(models.Group, models.Group.variety_pk == models.Variety.pk)
    .join(models.Lexeme, models.Lexeme.group_pk == models.Group.pk)
    .join(models.lexeme_meaning, models.lexeme_meaning.c.lexeme_pk == models.Lexeme.pk)
    .join(models.Meaning, models.Meaning.pk == models.lexeme_meaning.c.meaning_pk)
    .filter(models.Group.frame_pk == ctx.pk)
    .all()
):
    language_meanings.setdefault(language_obj.id, {})[meaning.pk] = meaning

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

frame_map = SelectedLanguagesMap(ctx, req, languages, eid='frame-map') if languages else None

groups = []
if language is not None:
    groups = (
        DBSession.query(models.Group)
        .options(joinedload(models.Group.lexemes).joinedload(models.Lexeme.meanings))
        .filter(models.Group.frame_pk == ctx.pk)
        .filter(models.Group.variety_pk == language.pk)
        .order_by(models.Group.term)
        .all()
    )
%>

% if language is not None:
  <h2><a href="${req.route_url('frame', id=ctx.id)}">${ctx.frame}</a></h2>
% else:
  <h2>${ctx.frame}</h2>
% endif

% if frame_map and language is None:
  ${frame_map.render()}
% endif

% if language is None:
  <table class="table table-striped table-condensed js-table-search-sort">
    <thead>
      <tr>
        <th>Language</th>
        <th>A-class</th>
      </tr>
    </thead>
    <tbody>
      % for variety in languages:
        <tr>
          <td>
            <a href="${req.route_url('frame', id=ctx.id, _query={'language': variety.id})}">${variety.name}</a>
          </td>
          <td>${fmt_values(language_meanings.get(variety.id, {}).values())}</td>
        </tr>
      % endfor
    </tbody>
  </table>
% endif

% if language is not None:
  <p>
	  <strong>Language:</strong> ${h.link(req, language)}
  </p>
  % for group in groups:
    <h4>${h.link(req, group, label=group.term)}</h4>
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
        % for lex in sorted(group.lexemes, key=lambda item: item.lexeme):
          <tr>
            <td style="vertical-align: middle;">${lex.lexeme}</td>
            <td style="vertical-align: middle;">${lex.russian or ''}</td>
            <td style="vertical-align: middle; white-space: nowrap;">${fmt_values(lex.meanings)}</td>
          </tr>
        % endfor
      </tbody>
    </table>
  % endfor
% endif
