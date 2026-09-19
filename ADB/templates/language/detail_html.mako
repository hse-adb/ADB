<%inherit file="../app.mako"/>
<%! active_menu_item = "languages" %>

<%block name="title">${ctx.name}</%block>
<%block name="head">
  <link href="${req.static_url('ADB:static/project.css', _query={'v': 'language-sidebar-v1'})}" rel="stylesheet">
</%block>

<%
from clld.web.maps import LanguageMap
from ADB import models
from ADB.helpers import (
    language_description,
    language_external_links,
    language_identifier_badges,
    language_wals_breadcrumb,
    language_wals_spoken_in,
)

description_text = language_description(ctx)
external_links = language_external_links(ctx)
identifier_badges = language_identifier_badges(ctx)
wals_breadcrumb = language_wals_breadcrumb(ctx)
wals_spoken_in = language_wals_spoken_in(ctx)
language_map = None
if ctx.latitude is not None and ctx.longitude is not None:
    language_map = LanguageMap(ctx, req, eid='language-map')

dt = req.get_datatable('groups', models.Group, variety=ctx)
%>

% if wals_breadcrumb:
  <ul class="breadcrumb language-wals-breadcrumb">
    % for index, item in enumerate(wals_breadcrumb):
      <li class="${'active' if not item['url'] else ''}">
        ${item['label']}:
        % if item['url']:
          <a class="${item['label']}" href="${item['url']}">${item['value']}</a>
        % else:
          ${item['value']}
        % endif
        % if index < len(wals_breadcrumb) - 1:
          <span class="divider">/</span>
        % endif
      </li>
    % endfor
  </ul>
% endif

<h2>${ctx.name}</h2>
% if identifier_badges or language_map or external_links:
  <div class="language-sidebar pull-right">
    % if identifier_badges:
      <div class="codes pull-right language-identifier-badges">
        <ul class="inline codes pull-right">
          % for badge in identifier_badges:
            <li>
              <span class="large label label-info">
                ${badge['label']}
                <span class="language_identifier ${badge['identifier_class']}">
                  <a href="${badge['url']}" style="color: white;" title="${badge['value']}">
                    <i class="icon-share icon-white"></i> ${badge['value']}
                  </a>
                </span>
              </span>
            </li>
          % endfor
        </ul>
      </div>
      <div style="clear: both;"></div>
    % endif
    % if language_map:
      <div class="language-map-panel well well-small">
        ${language_map.render()}
        % if wals_spoken_in:
          <table class="table table-condensed table-nonfluid language-spoken-in">
            <tbody>
              <tr>
                <td class="key">Spoken in:</td>
                <td>
                  % for index, country in enumerate(wals_spoken_in):
                    % if index:
                      ${', '}
                    % endif
                    % if country['url']:
                      <a class="Country" href="${country['url']}" title="${country['label']}">${country['label']}</a>
                    % else:
                      ${country['label']}
                    % endif
                  % endfor
                </td>
              </tr>
            </tbody>
          </table>
        % endif
      </div>
    % endif
    % if external_links:
      <div class="language-links-panel accordion" id="language-links-accordion">
        <div class="accordion-group">
          <div class="accordion-heading">
            <a class="accordion-toggle"
               data-toggle="collapse"
               data-parent="#language-links-accordion"
               href="#language-links"
               title="click to hide or show Links">
              Links
            </a>
          </div>
          <div id="language-links" class="accordion-body collapse in">
            <div class="accordion-inner">
              <ul class="nav nav-tabs nav-stacked language-links-list">
                % for link in external_links:
                  <li>
                    <a href="${link['url']}" rel="noopener noreferrer" target="_blank" title="${link['label']}">
                      % if link['icon_url']:
                        <img alt="${link['icon_alt']}" height="20" src="${link['icon_url']}" width="20">
                      % endif
                      ${link['label']}
                    </a>
                  </li>
                % endfor
              </ul>
            </div>
          </div>
        </div>
      </div>
    % endif
  </div>
% endif

% if description_text:
  <div style="white-space: pre-wrap;">${description_text}</div>
% endif

<div style="clear: both;"></div>
${dt.render()}
