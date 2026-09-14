/***********************
 * NAVBAR & HELPER FUNCTIONS
 ***********************/

// Adjust layer control height on window resize
$(window).resize(function () {
  sizeLayerControl();
});

// Show the About modal when the About button is clicked
$("#about-btn").click(function () {
  $("#aboutModal").modal("show");
  $(".navbar-collapse.in").collapse("hide");
  return false;
});

// Toggle the sidebar when the Tools (list) button is clicked
$("#list-btn").click(function () {
  animateSidebar();
  return false;
});

// Toggle the navbar collapse when the nav icon is clicked
$("#nav-btn").click(function () {
  $(".navbar-collapse").collapse("toggle");
  return false;
});

// Toggle the sidebar when the sidebar search icon is clicked
$("#sidebar-toggle-btn").click(function () {
  animateSidebar();
  return false;
});

// Animate the sidebar (toggle its width)
function animateSidebar() {
  $("#sidebar").animate(
    {
      width: "toggle",
    },
    350,
    function () {
      map.invalidateSize();
    }
  );
}

// Set maximum height for the layer control based on the map height
function sizeLayerControl() {
  $(".leaflet-control-layers").css("max-height", $("#map").height() - 50);
}


/***********************
 * MAP INITIALIZATION & GLOBAL SETTINGS
 ***********************/

// Default view settings (using new code’s values for India)
const defaultCenter = [20.5937, 78.9629]; // [lat, lng]
/*const defaultZoom = 5.578;*/

// Check if the device is mobile (adjust width as needed)
const isMobile = window.innerWidth <= 768;

// Use zoom level 5 on mobile, 5.578 otherwise
const defaultZoom = isMobile ? 5 : 5.4;

var map = L.map("map", {
  timeDimension: true,
  timeDimensionControl: true,
  timeDimensionControlOptions: {
    position: "bottomleft",
    autoPlay: true,
    loopButton: true,
    minSpeed: 1,
    maxSpeed: 10,
    speedStep: 1,
  },
  zoomControl: false,
  attributionControl: false,
  minZoom: 5,  // 👈 prevent zooming out beyond level 4
  maxZoom: 18, // 👈 optional: prevent zooming in too far
}).setView(defaultCenter, defaultZoom);


// Set max bounds (restrict vertical panning as desired)
const maxLatitude = 25; // Adjust as needed
const bounds = L.latLngBounds(L.latLng(-90, -180), L.latLng(maxLatitude, 180));
map.setMaxBounds(bounds);
map.on("drag", function () {
  map.panInsideBounds(bounds, { animate: false });
});

// Create additional panes for layer display order
map.createPane("geojsonPane");
map.getPane("geojsonPane").style.zIndex = 200; // Background
map.createPane("overlayPane");
map.getPane("overlayPane").style.zIndex = 400;
map.createPane("overlayPane2");
map.getPane("overlayPane2").style.zIndex = 401;



/***********************
 * CONTROLS & GEOPLACEMENT
 ***********************/

// Add a zoom control to the bottom right (since we disabled the default)
L.control.zoom({ position: "topleft" }).addTo(map);


// Add geolocation (locate) control (from your original code)
L.control.locate({
  position: "bottomright",
  drawCircle: true,
  follow: true,
  setView: true,
  keepCurrentZoomLevel: true,
  markerStyle: {
    weight: 1,
    opacity: 0.8,
    fillOpacity: 0.8,
  },
  circleStyle: {
    weight: 1,
    clickable: false,
  },
  icon: "fa fa-location-arrow",
  metric: false,
  strings: {
    title: "My location",
    popup: "You are within {distance} {unit} from this point",
    outsideMapBoundsMsg: "You seem located outside the boundaries of the map",
  },
  locateOptions: {
    maxZoom: 18,
    watch: true,
    enableHighAccuracy: true,
    maximumAge: 10000,
    timeout: 10000,
  },
}).addTo(map);

// Optional: Display coordinates on mousemove (ensure an element with id "coordinates" exists)
const coordDiv = document.getElementById("coordinates");

if (coordDiv) {
  map.on("mousemove", function (e) {
    const { lat, lng } = e.latlng;
    coordDiv.innerHTML = `Latitude: ${lat.toFixed(3)}<br>Longitude: ${lng.toFixed(3)}`;
    coordDiv.style.display = "block"; // Show coordinates only when on the map
  });

  map.on("mouseout", function () {
    coordDiv.style.display = "none"; // Hide when the mouse leaves the map
  });
}


/***********************
 * BASEMAP & OVERLAY LAYERS (NEW DEFINITIONS)
 ***********************/

// Base layers
 const topoMap = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        maxZoom: 17,
        attribution: '© OpenTopoMap contributors',
		 transparent: true,
    });

     
    /*const openStreetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors',
        transparent: true,
    });*/
	
	const cartoLight = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors, © CARTO',
});

const esriWorldStreetMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 20,
    attribution: '© Esri, HERE, Garmin, FAO, NOAA, USGS, © OpenStreetMap contributors',
});

const esriWorldImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
	maxZoom: 16,
    attribution: '© Esri & the GIS User Community',
});

const osmTopographic = L.tileLayer.wms("https://ows.mundialis.de/services/service?", {
  layers: "TOPO-WMS",
  format: "image/png",
  transparent: true,
  attribution: "© OpenStreetMap contributors",
  zIndex: 901,
});
var osmBrightGray =  L.tileLayer(
  "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
  {
    attribution:
      "Tiles courtesy of the <a href='https://usgs.gov/'>U.S. Geological Survey</a>",
    maxZoom: 20,
  }
);
const usgsImagery = L.tileLayer(
  "https://basemap.nationalmap.gov/ArcGIS/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
  {
    maxZoom: 16,
    attribution: "USGS Imagery",
    zIndex: 900,
  }).addTo(map);
const usgsTopographic = L.tileLayer.wms(
  "https://basemap.nationalmap.gov/arcgis/services/USGSTopo/MapServer/WMSServer",
  {
    layers: "0",
    format: "image/png",
    transparent: true,
    attribution: "© USGS",
    zIndex: 902,
  }
);
const cartoDark = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap contributors, © CARTO",
  zIndex: 903,
});

// Overlay layers (WMS)
/*const indmap = L.tileLayer.wms("/geoserver/IndianShp/wms?", {
  pane: "overlayPane",
  layers: "IndianShp:India2025",
  format: "image/png",
  transparent: true,
});*/
const indmap = L.tileLayer.wms("/geoserver/PFZ-IndianShapefile/wms", {
  pane: "overlayPane",
  layers: "PFZ-IndianShapefile:gdam_410_l0_india_corrected",
  format: "image/png",
  transparent: true,
});
const wmsLayer2 = L.tileLayer.wms("/geoserver/PFZ_Automation/wms", {
  pane: "overlayPane",
  layers: "PFZ_Automation:pfzlines",
  format: "image/png",
  transparent: true,
});
const wmsLayer3 = L.tileLayer.wms("/geoserver/PFZ_EEZ/wms", {
  pane: "overlayPane",
  layers: "PFZ_Automation:indiaeez",
  format: "image/png",
  transparent: true,
});
const wmsLayer4 = L.tileLayer.wms("/geoserver/PFZ_Sectors/wms", {
  pane: "overlayPane2",
  layers: "PFZ_Sectors:sector_new",
  format: "image/png",
  transparent: true,
});
const wmsLayer5 = L.tileLayer.wms("/geoserver/PFZ_LandingCentres/wms", {
  pane: "overlayPane",
  layers: "PFZ_LandingCentres:LandingCenters_29Apr2024",
  format: "image/png",
  transparent: true,
});
const wmsLayer6 = L.tileLayer.wms("/geoserver/BathymteryImage/wms", {
  pane: "overlayPane",
  layers: "BathymteryImage:gebcobathymtery",
  format: "image/png",
  transparent: true,
});

// Define baseMaps and overlayMaps for the layer control
const baseMaps = {
  "OSM Topographic": osmTopographic,
  "USGS Imagery": usgsImagery,
  "USGS Topographic": usgsTopographic,
  "Carto Dark": cartoDark,
  //"Open Street Map":openStreetMap,
"Carto Light":cartoLight,
"ESRI World Street Map":esriWorldStreetMap,
"ESRI World Imagery":esriWorldImagery,
"OSM BrightGray":osmBrightGray,
};

const overlayMaps = {
  //PFZ_LINES: wmsLayer2,
  //EEZ_Lines: wmsLayer3,
  //Sectors: wmsLayer4,
  //LandingCentres: wmsLayer5,
  //Bathymetry: wmsLayer6,
};

// Add the layer control to the map
const layersControl = L.control.layers(baseMaps, overlayMaps, { collapsed: true }).addTo(map);
const layersControlContainer = layersControl.getContainer();

// Add a title element to the layers control (initially hidden)
const title = document.createElement("div");
title.innerHTML = "<strong>Base Layers</strong>";
title.style.textAlign = "center";
title.style.padding = "5px";
title.style.display = "none"; // Initially hidden
layersControlContainer.insertBefore(title, layersControlContainer.firstChild);

// Use a Mutation Observer to show/hide the title when the layers control is expanded/collapsed
const observer = new MutationObserver(() => {
  if (layersControlContainer.classList.contains("leaflet-control-layers-expanded")) {
    title.style.display = "block";
  } else {
    title.style.display = "none";
  }
});
observer.observe(layersControlContainer, { attributes: true, attributeFilter: ["class"] });

// Add some overlay layers to the map by default
indmap.addTo(map);
//wmsLayer2.addTo(map);
//wmsLayer3.addTo(map);
//wmsLayer4.addTo(map);
//wmsLayer5.addTo(map);


/***********************
 * EXTENT NAVIGATION & HOME BUTTON
 ***********************/

// Home button: reset the map view to the default center/zoom
const homeButton = document.getElementById("homeButton");
if (homeButton) {
  homeButton.addEventListener("click", () => {
    map.setView(defaultCenter, defaultZoom, { animate: false });
  });
}

// Extent navigation: record history of extents for “previous” and “next” extent buttons
const extentHistory = [];
const futureHistory = [];

map.on("moveend", () => {
  if (!futureHistory.length || !compareBounds(map.getBounds(), futureHistory[0])) {
    extentHistory.push(map.getBounds());
  }
});

function compareBounds(b1, b2) {
  return b1.equals(b2);
}

const previousExtentButton = document.getElementById("previousExtent");
if (previousExtentButton) {
  previousExtentButton.addEventListener("click", () => {
    if (extentHistory.length > 1) {
      const currentExtent = extentHistory.pop();
      futureHistory.unshift(currentExtent);
      const previousExtent = extentHistory[extentHistory.length - 1];
      map.fitBounds(previousExtent);
    }
  });
}

const nextExtentButton = document.getElementById("nextExtent");
if (nextExtentButton) {
  nextExtentButton.addEventListener("click", () => {
    if (futureHistory.length > 0) {
      const nextExtent = futureHistory.shift();
      extentHistory.push(nextExtent);
      map.fitBounds(nextExtent);
    }
  });
}


/***********************
 * GET FEATURE INFO – FISH ICON & PFZ LINES (WFS)
 ***********************/

// Define a fish icon for temporary markers
/*
var fishIcon = L.icon({
  iconUrl: "./img/fish.gif", // Update with your icon path
  iconSize: [50, 50],
  iconAnchor: [16, 16],
});

// Fetch PFZ lines via WFS and add temporary fish markers at midpoints
function fetchPFZLines() {
  var wfsUrl =
    "/geoserver/PFZ_Automation/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=PFZ_Automation:pfzlines&outputFormat=application/json";
  fetch(wfsUrl)
    .then((response) => response.json())
    .then((data) => {
      var latLngs = extractCoordinates(data);
      addFishMarkers(latLngs);
    })
    .catch((error) => console.error("Error fetching PFZ lines:", error));
}

// Extract midpoints (or desired points) from GeoJSON line features
function extractCoordinates(geojsonData) {
  var points = [];
  geojsonData.features.forEach((feature) => {
    var geometry = feature.geometry;
    if (geometry.type === "LineString") {
      var coords = geometry.coordinates;
      var midIndex = Math.floor(coords.length / 2);
      var midCoord = coords[midIndex];
      points.push([midCoord[1], midCoord[0]]); // Convert [lng, lat] to [lat, lng]
    }
    if (geometry.type === "MultiLineString") {
      geometry.coordinates.forEach((line) => {
        var midIndex = Math.floor(line.length / 2);
        var midCoord = line[midIndex];
        points.push([midCoord[1], midCoord[0]]);
      });
    }
  });
  return points;
}

// Add fish markers at the extracted points (and remove after 5 seconds)
function addFishMarkers(points) {
  points.forEach((point) => {
    var marker = L.marker(point, { icon: fishIcon }).addTo(map);
    setTimeout(() => {
      map.removeLayer(marker);
    }, 5000);
  });
}

fetchPFZLines();
*/

/***********************
 * ADDITIONAL CONTROLS & DYNAMIC LABELS
 ***********************/

// Append new checkbox controls to the existing Leaflet layers control
function appendCheckboxesToLeaflet() {
  var leafletControl = document.querySelector(".leaflet-control-layers");
  var newControlDiv = document.createElement("div");
  newControlDiv.classList.add("leaflet-control-layers-list");
  var newCheckboxContainer = document.getElementById("new-layer-controls");
  if (newCheckboxContainer) {
    newControlDiv.appendChild(newCheckboxContainer);
    leafletControl.appendChild(newControlDiv);
  }
}
appendCheckboxesToLeaflet();

// Dynamically add text labels for landing centre features (fetched via WFS)
let labelMarkers = [];

// Fetch GeoJSON features for labels
async function fetchFeatures() {
  const url =
    "/geoserver/PFZ_LandingCentres/ows?" +
    "service=WFS&version=1.0.0&request=GetFeature&typeName=PFZ_LandingCentres:LandingCenters_29Apr2024" +
    "&outputFormat=application/json";
  const response = await fetch(url);
  const data = await response.json();
  return data;
}

// Check if two markers are overlapping (within a pixel threshold)
function isOverlapping(markerA, markerB) {
  const positionA = map.latLngToLayerPoint(markerA.getLatLng());
  const positionB = map.latLngToLayerPoint(markerB.getLatLng());
  const distance = positionA.distanceTo(positionB);
  const threshold = 20; // Adjust based on label size/requirements
  return distance < threshold;
}

// Add labels (using the LC_NAME attribute) if the zoom level is above a threshold
async function addLabels(zoomThreshold) {
  // Remove any existing label markers
  labelMarkers.forEach((marker) => map.removeLayer(marker));
  labelMarkers = [];
  if (map.getZoom() >= zoomThreshold) {
    const geoJsonData = await fetchFeatures();
    geoJsonData.features.forEach((feature) => {
      const { LC_NAME } = feature.properties; // Adjust attribute name if needed
      let [lng, lat] = feature.geometry.coordinates;
      // Create a small random offset so labels don’t exactly overlap
      const randomAngle = Math.random() * Math.PI * 2;
      const randomDistance = Math.random() * 20 + 10; // pixels
      const offsetLat = (randomDistance * Math.sin(randomAngle)) / 111000;
      const offsetLng = (randomDistance * Math.cos(randomAngle)) / (111000 * Math.cos(lat * Math.PI / 180));
      const offsetLatLng = L.latLng(lat + offsetLat, lng + offsetLng);
      const labelMarker = L.marker(offsetLatLng, {
        icon: L.divIcon({
          className: "label-icon",
          html: `<div style="color:white;">${LC_NAME}</div>`,
          iconSize: [0, 0],
        }),
      });
      // Only add the label if it does not overlap with an existing one
      const overlaps = labelMarkers.some((existingMarker) => isOverlapping(existingMarker, labelMarker));
      if (!overlaps) {
        labelMarker.addTo(map);
        labelMarkers.push(labelMarker);
      }
    });
  }
}

// Monitor zoom changes and update labels accordingly
map.on("zoomend", () => {
  const zoomThreshold = 7; // Set desired zoom threshold
  addLabels(zoomThreshold);
});
// Initial label rendering
addLabels(7);

//L.control.browserPrint({title: 'Print Map',printModes: ["Portrait", "Landscape"],closePopupsOnPrint: false}).addTo(map);

L.control.navbar().addTo(map);


   
// Create a special pane for CHL that stays on top
map.createPane("chlPane");
map.getPane("chlPane").style.zIndex = 300; // Highest z-index
// Create a special pane for CHL that stays on top
map.createPane("sstPane");
map.getPane("sstPane").style.zIndex = 301; // Highest z-index

// Create CHL layer using the dedicated pane
var chlLayer = L.tileLayer.wms("/geoserver/PFZ-TUNA-SST-CHL/wms", {
    layers: "PFZ-TUNA-SST-CHL:chl",
    format: "image/png",
    transparent: true,
    version: "1.1.0",
    opacity: 0.85,
    attribution: "INCOIS – Chlorophyll",
    pane: "chlPane"  // Use custom pane
});

// Rest of the code same as Solution 1
var sstLayer = L.tileLayer.wms("/geoserver/PFZ-TUNA-SST-CHL/wms", {
    layers: "PFZ-TUNA-SST-CHL:sst",
    format: "image/png",
    transparent: true,
    version: "1.1.0",
    opacity: 0.85,
    attribution: "INCOIS – SST",
    pane: "sstPane",
	colorscalerange: '280,302' 
});

function toggleSST(checkbox) {
    var legendBox = document.getElementById("sst-legend-container");
    if (checkbox.checked) {
        map.addLayer(sstLayer);
        legendBox.style.display = "block";
    } else {
        map.removeLayer(sstLayer);
        legendBox.style.display = "none";
    }
}

// 👇 PASTE THE CLICK CODE RIGHT HERE — after toggleSST, end of file

map.on("click", function (e) {
  var latlng = e.latlng;
  var size = map.getSize();
  var bounds = map.getBounds();

  if (!map.hasLayer(sstLayer) && !map.hasLayer(chlLayer)) return;

  function buildGFIUrl(layerName) {
    var sw = bounds.getSouthWest();
    var ne = bounds.getNorthEast();
    var bbox = sw.lng + "," + sw.lat + "," + ne.lng + "," + ne.lat;
    var point = map.latLngToContainerPoint(latlng);
    return (
      "/geoserver/PFZ-TUNA-SST-CHL/wms?" +
      "SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo" +
      "&LAYERS=PFZ-TUNA-SST-CHL:" + layerName +
      "&QUERY_LAYERS=PFZ-TUNA-SST-CHL:" + layerName +
      "&BBOX=" + bbox +
      "&WIDTH=" + size.x +
      "&HEIGHT=" + size.y +
      "&X=" + Math.round(point.x) +
      "&Y=" + Math.round(point.y) +
      "&INFO_FORMAT=application/json" +
      "&SRS=EPSG:4326"
    );
  }

  var queries = [];
  if (map.hasLayer(sstLayer)) queries.push({ name: "sst", label: "🌡️ SST" });
  if (map.hasLayer(chlLayer)) queries.push({ name: "chl", label: "🟢 CHL" });

  Promise.all(
    queries.map(q => fetch(buildGFIUrl(q.name)).then(r => r.json()).catch(() => null))
  ).then(function (results) {

    var popupContent = `<div style="font-size:13px; line-height:1.8;">
      <b>📍 Location</b><br>
      Lat: ${latlng.lat.toFixed(4)}, Lng: ${latlng.lng.toFixed(4)}<br><br>`;

    queries.forEach(function (q, i) {
      var val = "No data";
      var data = results[i];
      if (data && data.features && data.features.length > 0) {
        var raw = Object.values(data.features[0].properties)[0];
        if (raw !== null && raw !== undefined) {
          if (q.name === "sst") {
  var rawVal = parseFloat(raw);
  var celsius;
  
  if (rawVal > 200) {
    celsius = (rawVal - 273.15).toFixed(2); // it's in Kelvin
  } else {
    celsius = rawVal.toFixed(2); // already Celsius
  }
  val = celsius + " °C";
}else {
            val = parseFloat(raw).toFixed(4) + " mg/m³";
          }
        }
      }
      popupContent += `<b>${q.label}:</b> ${val}<br>`;
    });

    popupContent += "</div>";
    L.popup().setLatLng(latlng).setContent(popupContent).openOn(map);
  });
});