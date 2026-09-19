
(function () {
  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, function (char) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      }[char];
    });
  }

  function sliceColor(slice) {
    var color = slice.color || '#8a8f98';
    if (slice.css_var) {
      return 'var(' + slice.css_var + ', ' + color + ')';
    }
    return color;
  }

  function sliceColorKey(slice) {
    return slice.css_var || slice.color || '#8a8f98';
  }

  function polarToCartesian(cx, cy, radius, angle) {
    var radians = (angle - 90) * Math.PI / 180.0;
    return {
      x: cx + radius * Math.cos(radians),
      y: cy + radius * Math.sin(radians)
    };
  }

  function describeSector(cx, cy, radius, startAngle, endAngle) {
    var start = polarToCartesian(cx, cy, radius, endAngle);
    var end = polarToCartesian(cx, cy, radius, startAngle);
    var largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';
    return [
      'M', cx, cy,
      'L', start.x.toFixed(3), start.y.toFixed(3),
      'A', radius, radius, 0, largeArcFlag, 0, end.x.toFixed(3), end.y.toFixed(3),
      'Z'
    ].join(' ');
  }

  function renderCircle(slice) {
    return [
      '<circle class="frame-pie-slice frame-pie-slice-', escapeHtml(slice.id), '"',
      ' cx="50" cy="50" r="46"',
      ' style="fill: ', sliceColor(slice), ';">',
      '<title>', escapeHtml(slice.label), '</title>',
      '</circle>'
    ].join('');
  }

  function renderSector(slice, index, count) {
    var startAngle = index * 360 / count;
    var endAngle = (index + 1) * 360 / count;
    return [
      '<path class="frame-pie-slice frame-pie-slice-', escapeHtml(slice.id), '"',
      ' d="', describeSector(50, 50, 46, startAngle, endAngle), '"',
      ' style="fill: ', sliceColor(slice), ';">',
      '<title>', escapeHtml(slice.label), '</title>',
      '</path>'
    ].join('');
  }

  function renderSeparator(angle) {
    var end = polarToCartesian(50, 50, 46, angle);
    return [
      '<line class="frame-pie-separator"',
      ' x1="50" y1="50"',
      ' x2="', end.x.toFixed(3), '"',
      ' y2="', end.y.toFixed(3), '"></line>'
    ].join('');
  }

  function renderSeparators(slices) {
    var lines = [];
    var count = slices.length;
    for (var i = 0; i < count; i += 1) {
      var previous = slices[(i + count - 1) % count];
      var current = slices[i];
      if (sliceColorKey(previous) !== sliceColorKey(current)) {
        lines.push(renderSeparator(i * 360 / count));
      }
    }
    return lines.join('');
  }

  function renderPie(slices) {
    var svg = [
      '<svg class="frame-pie-svg" viewBox="0 0 100 100" aria-hidden="true" focusable="false">'
    ];
    var count = slices.length;
    if (count === 1) {
      svg.push(renderCircle(slices[0]));
    } else {
      for (var i = 0; i < count; i += 1) {
        svg.push(renderSector(slices[i], i, count));
      }
      svg.push(renderSeparators(slices));
    }
    svg.push('<circle class="frame-pie-outline" cx="50" cy="50" r="46"></circle>');
    svg.push('</svg>');
    return svg.join('');
  }

  if (window.CLLD && CLLD.MapIcons) {
    CLLD.MapIcons.framePie = function (feature, size) {
      var framePie = feature.properties.frame_pie || {};
      var slices = framePie.slices || [];
      if (!slices.length) {
        slices = [{
          id: 'no-data',
          label: 'no data',
          color: '#d9dde3',
          css_var: '--frame-map-no-data'
        }];
      }
      return L.divIcon({
        html: [
          '<div class="frame-pie-icon" style="width: ', size, 'px; height: ', size, 'px;">',
          renderPie(slices),
          '</div>'
        ].join(''),
        iconSize: [size, size],
        iconAnchor: [Math.floor(size / 2), Math.floor(size / 2)],
        popupAnchor: [0, 0],
        className: 'frame-pie-leaflet-icon'
      });
    };
  }

  function applyFrameMapColor(scope, input) {
    var colorVar = input.getAttribute('data-color-var');
    if (colorVar) {
      scope.style.setProperty(colorVar, input.value);
    }
  }

  $(function () {
    $('.js-frame-map-colors').each(function () {
      var scope = this;
      var $scope = $(scope);

      $scope.find('.js-frame-map-color').each(function () {
        applyFrameMapColor(scope, this);
      });

      $scope.off('.frameMapColors');

      $scope.on('input.frameMapColors change.frameMapColors', '.js-frame-map-color', function () {
        applyFrameMapColor(scope, this);
      });

      $scope.on('click.frameMapColors', '.js-frame-map-reset', function () {
        $scope.find('.js-frame-map-color').each(function () {
          this.value = this.getAttribute('data-default-color');
          applyFrameMapColor(scope, this);
        });
      });
    });
  });
}());
