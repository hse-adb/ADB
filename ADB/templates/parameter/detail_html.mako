<%inherit file="../app.mako"/>
<%! active_menu_item = "parameters" %>

<%block name="title">${ctx.name}</%block>

<%
from clld.db.meta import DBSession
from clld.db.models import common

vss = (
    DBSession.query(common.ValueSet)
    .filter(common.ValueSet.parameter_pk == ctx.pk)
    .all()
)

keys = []
for vs in vss:
    jd = vs.jsondata or {}
    for k in jd.keys():
        if k not in keys:
            keys.append(k)

order = [
    "perf_EP", "perf_ES", "perf_P", "perf_P2", "perf_S", "perf_Q", "perf_MP", "perf_EMP",
    "imperf_P", "imperf_P2", "imperf_S", "imperf_MP",
]
keys = [k for k in order if k in keys] + [k for k in keys if k not in order]

vss = sorted(vss, key=lambda vs: (vs.language.name or vs.language.id).lower())
%>

<h2>${ctx.name}</h2>

<table class="table table-striped table-condensed js-table-search-sort">
  <thead>
    <tr>
      <th>Язык</th>
      % for k in keys:
        <th>${k}</th>
      % endfor
    </tr>
  </thead>
  <tbody>
    % for vs in vss:
      <tr>
        <td>${h.link(req, vs.language)}</td>
        % for k in keys:
          <td>${(vs.jsondata or {}).get(k, 0)}</td>
        % endfor
      </tr>
    % endfor
  </tbody>
</table>

