<%inherit file="app.mako"/>

<%block name="header">
    ##<a href="${request.route_url('dataset')}">
    ##    <img src="${request.static_url('ADB:static/header.gif')}"/>
    ##</a>
</%block>

${next.body()}

<script>
$(function () {
  function syncTopInfo(api) {
    var $wrapper = $(api.table().container());
    var $bottomInfo = $wrapper.find('div.dataTables_info').last();
    if (!$bottomInfo.length) {
      return;
    }
    var $topInfo = $wrapper.find('div.dataTables_info.top-info');
    if (!$topInfo.length) {
      $topInfo = $('<div class="dataTables_info top-info"></div>');
      var $filter = $wrapper.find('div.dataTables_filter').first();
      if ($filter.length) {
        $filter.before($topInfo);
      } else {
        $wrapper.prepend($topInfo);
      }
    }
    $topInfo.text($bottomInfo.text());
  }

  $(document).on('init.dt draw.dt', function (e, settings) {
    if (settings && settings.oInstance && settings.oInstance.api) {
      syncTopInfo(settings.oInstance.api());
    } else if (settings) {
      syncTopInfo(new $.fn.dataTable.Api(settings));
    }
  });

  $('table.js-table-search-sort').each(function () {
    if ($.fn.DataTable && !$.fn.DataTable.isDataTable(this)) {
      $(this).DataTable({
        paging: true,
        searching: true,
        ordering: true,
        autoWidth: false
      });
    }
  });
});
</script>
