// json data adding

// Helper functions to format date and time
function formatDate(date) {
    var year = date.getFullYear();
    var month = String(date.getMonth() + 1).padStart(2, '0');
    var day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function formatTime(hour, minute, second) {
    return `${String(hour).padStart(2, '0')}-${String(minute).padStart(2, '0')}-${String(second).padStart(2, '0')}`;
  }

  // Generate time slots dynamically
  function generateTimeSlots(startHour, interval, count) {
    let timeSlots = [];
    for (let i = 0; i < count; i++) {
      let hour = startHour + (i * interval);
      if (hour >= 24) hour -= 24;
      timeSlots.push({ hour: hour, minute: 30, second: 0 });
    }
    return timeSlots;
  }

  var current2Date = new Date();
  var formattedDate = formatDate(current2Date);
  var timeSlots = generateTimeSlots(1, 3, 8);
  var baseUrl2 = '/geoportal/pfzjsondata/OSF_Json/';
  let velocityLayers = [];

  document.getElementById('CURRENTS_IO').addEventListener('change', function () {
    if (this.checked) {
      loadJsonData();
    } else {
      velocityLayers.forEach(layer => map.removeLayer(layer));
      velocityLayers = [];
    }
  });

  function loadJsonData() {
    timeSlots.forEach(function (slot) {
      var formattedTime = formatTime(slot.hour, slot.minute, slot.second);
      var jsonUrl = `${baseUrl2}${formattedDate}_00-00-00_current_0m.json`;

      fetch(jsonUrl)
        .then(response => response.json())
        .then(data => {
          var uData = data.find(item => item.header.parameterNumberName === "U_Current");
          var vData = data.find(item => item.header.parameterNumberName === "V_Current");

          if (uData && vData) {
            var velocityLayer = L.velocityLayer({
              displayValues: false,
              displayOptions: {
                velocityType: 'Current',
                displayPosition: 'bottomleft',
                displayEmptyString: 'No current data available',
              },
              data: data,
              lineWidth: 0.5,
              velocityScale: 0.2,
              colorScale: ["rgb(255,255,255)", "rgb(0,0,255)"],
            });

            velocityLayer.addTo(map);
            velocityLayers.push(velocityLayer);

            map.on('click', function (e) {
                var isCurrentsIoChecked = document.getElementById('CURRENTS_IO').checked;

  if (!isCurrentsIoChecked) {
    // If unchecked, do nothing
    return;
  }
              var clickedLatLng = e.latlng;
              var nx = uData.header.nx;
              var ny = uData.header.ny;

              var gridX = Math.floor((clickedLatLng.lng - uData.header.lo1) / uData.header.dx);
              var gridY = Math.floor((clickedLatLng.lat - uData.header.la1) / -uData.header.dy);
              var index = gridY * nx + gridX;

              if (index >= 0 && index < uData.data.length) {
                var u = uData.data[index];
                var v = vData.data[index];
                var speed = Math.sqrt(u * u + v * v).toFixed(2);
                var direction = (Math.atan2(v, u) * (180 / Math.PI) + 360) % 360;

                var cardinalDirection = getCardinalDirection(direction);

                L.popup()
                  .setLatLng(clickedLatLng)
                  .setContent(
                    `Latitude: ${e.latlng.lat.toFixed(3)}<br>Longitude: ${e.latlng.lng.toFixed(3)}<br>Speed: ${speed} m/s<br>Direction: ${direction.toFixed(2)}° ${cardinalDirection}`
                  )
                  .openOn(map);
              } else {
                L.popup()
                  .setLatLng(clickedLatLng)
                  .setContent("Data unavailable for this location.")
                  .openOn(map);
              }
            });
          }
        })
        .catch(error => console.error('Error loading JSON data:', error));
    });
  }

  function getCardinalDirection(degrees) {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.floor((degrees + 22.5) / 45) % 8;
    return directions[index];
  }