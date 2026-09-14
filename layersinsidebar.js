    ////PFZ Lines
    // Add the WMS layer to the map by default if checkbox is checked
const pfzCheckbox = document.getElementById("PFZ_LINES");
if (pfzCheckbox.checked) {
  wmsLayer2.addTo(map);
}

// Add event listener to toggle on checkbox change
pfzCheckbox.addEventListener("change", () => {
  if (pfzCheckbox.checked) {
    wmsLayer2.addTo(map);     // Add layer when checked
  } else {
    map.removeLayer(wmsLayer2); // Remove layer when unchecked
  }
});
//EEZ Lines
const eezCheckbox = document.getElementById("EEZ_LINES");
if (eezCheckbox.checked) {
  wmsLayer3.addTo(map);
}

// Add event listener to toggle on checkbox change
eezCheckbox.addEventListener("change", () => {
  if (eezCheckbox.checked) {
    wmsLayer3.addTo(map);     // Add layer when checked
  } else {
    map.removeLayer(wmsLayer3); // Remove layer when unchecked
  }
});

//Sectors

const sectorsCheckbox = document.getElementById("Sectors");
if (sectorsCheckbox.checked) {
  wmsLayer4.addTo(map);
}

// Add event listener to toggle on checkbox change
sectorsCheckbox.addEventListener("change", () => {
  if (sectorsCheckbox.checked) {
    wmsLayer4.addTo(map);     // Add layer when checked
  } else {
    map.removeLayer(wmsLayer4); // Remove layer when unchecked
  }
});
//Landingsectors

const landingCentres = document.getElementById("LandingCentres");
if (landingCentres.checked) {
  wmsLayer5.addTo(map);
}

// Add event listener to toggle on checkbox change
landingCentres.addEventListener("change", () => {
  if (landingCentres.checked) {
    wmsLayer5.addTo(map);     // Add layer when checked
  } else {
    map.removeLayer(wmsLayer5); // Remove layer when unchecked
  }
});

//Bathymetry
const bathymetry = document.getElementById("Bathymetry");
if (bathymetry.checked) {
  wmsLayer6.addTo(map);
}

// Add event listener to toggle on checkbox change
bathymetry.addEventListener("change", () => {
  if (bathymetry.checked) {
    wmsLayer6.addTo(map);     // Add layer when checked
  } else {
    map.removeLayer(wmsLayer6); // Remove layer when unchecked
  }
});
