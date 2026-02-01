<%inherit file="app.mako"/>

<%block name="header">
    ##<a href="${request.route_url('dataset')}">
    ##    <img src="${request.static_url('myapp:static/header.gif')}"/>
    ##</a>
</%block>

${next.body()}
