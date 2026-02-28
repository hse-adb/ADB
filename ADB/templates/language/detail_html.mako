<%inherit file="../app.mako"/>
<%! active_menu_item = "languages" %>

<%block name="title">${ctx.name}</%block>

<%
from ADB import models
dt = req.get_datatable('groups', models.Group, variety=ctx)
%>

<h2>${ctx.name}</h2>
${dt.render()}
