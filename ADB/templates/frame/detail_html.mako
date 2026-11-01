<%inherit file="../app.mako"/>
<%! active_menu_item = "frames" %>

<%block name="title">${ctx.frame}</%block>
<%block name="head">
  <link href="${req.static_url('ADB:static/project.css', _query={'v': 'frame-pie-v3'})}" rel="stylesheet">
  <script src="${req.static_url('ADB:static/project.js', _query={'v': 'frame-pie-v3'})}"></script>
</%block>

<%
from clld.db.meta import DBSession
from clld.web.util.htmllib import literal
from sqlalchemy.orm import joinedload, subqueryload
from ADB import models
from ADB.frame_map import FramePieMap, build_frame_map_data, css_variables
from ADB.helpers import collect_group_meanings, format_group_meanings, format_meanings

frame_groups = (
    DBSession.query(models.Group)
    .options(
        joinedload(models.Group.variety),
        subqueryload(models.Group.lexemes).subqueryload(models.Lexeme.meanings),
    )
    .filter(models.Group.frame_pk == ctx.pk)
    .order_by(models.Group.term)
    .all()
)

languages = sorted(
    {group.variety_pk: group.variety for group in frame_groups}.values(),
    key=lambda item: item.name,
)
language_id = req.matchdict.get('language') or req.params.get('language')
language = next((item for item in languages if item.id == language_id), None)

language_group_meanings = {}
for group in frame_groups:
    language_group_meanings.setdefault(group.variety.id, []).append(collect_group_meanings(group))

frame_map_data = build_frame_map_data(frame_groups)
frame_map = (
    FramePieMap(
        ctx,
        req,
        languages,
        frame_map_data['sectors_by_language'],
        eid='frame-map',
    )
    if languages else None
)

groups = [group for group in frame_groups if language is not None and group.variety_pk == language.pk]
%>

% if language is not None:
  <h2><a href="${req.route_url('frame', id=ctx.id)}">${ctx.frame}</a></h2>
% else:
  <h2>${ctx.frame}</h2>
% endif

% if frame_map and language is None:
  <div class="frame-map-layout js-frame-map-colors"
       data-map-id="frame-map"
       style="${css_variables(frame_map_data)}">
    <div class="frame-map-layout-map">
      ${frame_map.render()}
    </div>
    <div class="frame-map-legend">
      <div class="frame-map-legend-heading">
        <h4>A-class colors</h4>
        % if frame_map_data['legend_values']:
          <button class="btn btn-mini js-frame-map-reset" type="button">Reset</button>
        % endif
      </div>
      % for item in frame_map_data['legend_values']:
        <label class="frame-map-legend-row">
          <input class="js-frame-map-color"
                 type="color"
                 value="${item['color']}"
                 data-color-var="${item['css_var']}"
                 data-default-color="${item['color']}">
          <span class="frame-map-legend-swatch"
                style="background-color: var(${item['css_var']}, ${item['color']});"></span>
          <span class="frame-map-legend-label">${literal(item['label'])}</span>
          <span class="frame-map-legend-count">${item['language_count']}</span>
        </label>
      % endfor
      % if frame_map_data['has_unique']:
        <div class="frame-map-legend-row frame-map-legend-row-fixed">
          <span class="frame-map-legend-control-spacer"></span>
          <span class="frame-map-legend-swatch"
                style="background-color: var(--frame-map-unique, ${frame_map_data['unique_color']});"></span>
          <span class="frame-map-legend-label">unique</span>
        </div>
      % endif
      % if frame_map_data['has_no_data']:
        <div class="frame-map-legend-row frame-map-legend-row-fixed">
          <span class="frame-map-legend-control-spacer"></span>
          <span class="frame-map-legend-swatch"
                style="background-color: var(--frame-map-no-data, ${frame_map_data['no_data_color']});"></span>
          <span class="frame-map-legend-label">no data</span>
        </div>
      % endif
    </div>
  </div>
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
            <a href="${req.route_url('frame_language', id=ctx.id, language=variety.id)}">${variety.name}</a>
          </td>
          <td>${literal(format_group_meanings(language_group_meanings.get(variety.id, [])))}</td>
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
            <td style="vertical-align: middle; white-space: nowrap;">${literal(format_meanings(lex.meanings))}</td>
          </tr>
        % endfor
      </tbody>
    </table>
  % endfor
% endif
