<%inherit file="../app.mako"/>
<%! active_menu_item = "languages" %>

<%block name="title">${ctx.name}</%block>

<%
import csv
from pathlib import Path
import ADB
from clld.web.maps import LanguageMap
from ADB import models

iso_code = (ctx.iso_code or '').strip().lower()
if not iso_code:
    languages_path = Path(ADB.__file__).parent / 'data' / 'languages.csv'
    if languages_path.exists():
        with languages_path.open(newline='', encoding='utf-8') as fp:
            for row in csv.DictReader(fp):
                if row.get('language_id') == ctx.id:
                    iso_code = (row.get('ISO639P3code') or '').strip().lower()
                    break

description_text = ''
if iso_code:
    description_path = Path(ADB.__file__).parent / 'data' / 'descriptions' / '{}.txt'.format(iso_code)
    if description_path.exists():
        description_text = description_path.read_text(encoding='utf-8').strip()

language_map = None
if ctx.latitude is not None and ctx.longitude is not None:
    language_map = LanguageMap(ctx, req, eid='language-map')

dt = req.get_datatable('groups', models.Group, variety=ctx)
%>

<h2>${ctx.name}</h2>
% if language_map:
  <div class="pull-right" style="width: 320px; margin: 0 0 12px 12px;">
    ${language_map.render()}
  </div>
% endif

% if description_text:
  <div style="white-space: pre-wrap;">${description_text}</div>
% endif

<div style="clear: both;"></div>
${dt.render()}
