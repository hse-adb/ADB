<%inherit file="../app.mako"/>
<%! active_menu_item = "languages" %>

<%block name="title">${ctx.name}</%block>

<%
from clld.web.maps import LanguageMap
from ADB import models
from ADB.helpers import language_description

description_text = language_description(ctx)
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
