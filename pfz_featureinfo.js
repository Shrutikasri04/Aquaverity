 // Handle map click to fetch WFS data
 /*map.on('click', async function (e) {
    const wfsUrl = `/geoserver/PFZ_Automation/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=PFZ_Automation:pfzlines&outputFormat=application/json`;

    try {
        const response = await fetch(wfsUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const geojson = await response.json();

        // Find the closest feature to the clicked point
        const clickedPoint = turf.point([e.latlng.lng, e.latlng.lat]);
        let closestFeature = null;
        let minDistance = 50;

        geojson.features.forEach((feature) => {
            const featurePoint = turf.centroid(feature);
            const distance = turf.distance(clickedPoint, featurePoint);
            if (distance < minDistance) {
                closestFeature = feature;
                minDistance = distance;
            }
        });

        // Display feature info in a popup
        if (closestFeature) {
            const { State_Name, Julian_day, Length, Shape_Area } = closestFeature.properties;
            const popupContent = `
                <strong>State_Name:</strong> ${State_Name || 'N/A'}<br>
                <strong>Julian_Day:</strong> ${Julian_day || 'N/A'}<br>
                <strong>Length:</strong> ${Length || 'N/A'}<br>
                <strong>Shape_Area:</strong> ${Shape_Area || 'N/A'}
            `;
            L.popup()
                .setLatLng(e.latlng)
                .setContent(popupContent)
                .openOn(map);
        } else {
            L.popup()
                .setLatLng(e.latlng)
                .setContent("No feature found near the clicked location.")
                .openOn(map);
        }
    } catch (error) {
        console.error("Error fetching WFS data:", error);
        L.popup()
            .setLatLng(e.latlng)
            .setContent("No feature found near the clicked location.")
            .openOn(map);
    }
});*/


 // Handle map click to fetch WFS data
 map.on('click', async function (e) {
    const pfzWfsUrl = `/geoserver/PFZ_Automation/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=PFZ_Automation:pfzlines&outputFormat=application/json`;
    const landingCentersWfsUrl = `/geoserver/PFZ_LandingCentres/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=PFZ_LandingCentres:LandingCenters_29Apr2024&outputFormat=application/json`;

    try {
        const [pfzResponse, landingCentersResponse] = await Promise.all([
            fetch(pfzWfsUrl),
            fetch(landingCentersWfsUrl)
        ]);

        if (!pfzResponse.ok || !landingCentersResponse.ok) {
            throw new Error(`HTTP error! Status: ${pfzResponse.status}, ${landingCentersResponse.status}`);
        }

        const [pfzGeojson, landingCentersGeojson] = await Promise.all([
            pfzResponse.json(),
            landingCentersResponse.json()
        ]);

        const clickedPoint = turf.point([e.latlng.lng, e.latlng.lat]);
        let popupContent = "";

        // Handle PFZ Layer Data
        let closestPFZFeature = null;
        let pfzMinDistance = 50;
        pfzGeojson.features.forEach((feature) => {
            const featurePoint = turf.centroid(feature);
            const distance = turf.distance(clickedPoint, featurePoint);
            if (distance < pfzMinDistance) {
                closestPFZFeature = feature;
                pfzMinDistance = distance;
            }
        });

        // Handle Landing Centers Data
        let closestLandingFeature = null;
        let landingMinDistance = 50;

        landingCentersGeojson.features.forEach((feature) => {
            if (feature.geometry.type === "Point") {
                const featurePoint = turf.point(feature.geometry.coordinates);
                const distance = turf.distance(clickedPoint, featurePoint);
                if (distance < landingMinDistance) {
                    closestLandingFeature = feature;
                    landingMinDistance = distance;
                }
            }
        });

        // Compare the closest features and show the nearest one
        if (closestPFZFeature && closestLandingFeature) {
            // Compare distances and show the closest one
            if (pfzMinDistance < landingMinDistance) {
                const { State_Name, Julian_day, Length, Shape_Area } = closestPFZFeature.properties;
                popupContent += `
                
                    <strong>PFZ Layer Info:</strong><br>
                    <strong>State:</strong> ${State_Name || 'N/A'}<br>
                    <strong>JulianDay:</strong> ${Julian_day || 'N/A'}<br>
                    <strong>Length:</strong> ${Length || 'N/A'}<br>
                    <strong>Area:</strong> ${Shape_Area || 'N/A'}<br><br>
                `;
            } else {
                const { LC_NAME, DIST_NAME, LATITUDE, LONGITUDE, SECTOR_NAM } = closestLandingFeature.properties;
                popupContent += `
                    <strong>Landing Centers:</strong><br>
                    <strong>LCName:</strong> ${LC_NAME || 'N/A'}<br>
                    <strong>District:</strong> ${DIST_NAME || 'N/A'}<br>
                    <strong>Lat:</strong> ${LATITUDE || 'N/A'}<br>
                    <strong>Long:</strong> ${LONGITUDE || 'N/A'}<br>
                    <strong>Sector:</strong> ${SECTOR_NAM || 'N/A'}
                `;
            }
        } else if (closestPFZFeature) {
            const { State_Name, Julian_day, Length, Shape_Area } = closestPFZFeature.properties;
            popupContent += `
               
                <strong>PFZ Layer:</strong><br>
                <strong>State:</strong> ${State_Name || 'N/A'}<br>
                <strong>JulianDay:</strong> ${Julian_day || 'N/A'}<br>
                <strong>Length:</strong> ${Length || 'N/A'}<br>
                <strong>Area:</strong> ${Shape_Area || 'N/A'}<br><br>
            `;
        } else if (closestLandingFeature) {
            const { LC_NAME, DIST_NAME, LATITUDE, LONGITUDE, SECTOR_NAM } = closestLandingFeature.properties;
            popupContent += `
                <strong>Landing Centers:</strong><br>
                <strong>LCName:</strong> ${LC_NAME || 'N/A'}<br>
                <strong>District:</strong> ${DIST_NAME || 'N/A'}<br>
                <strong>Lat:</strong> ${LATITUDE || 'N/A'}<br>
                <strong>Long:</strong> ${LONGITUDE || 'N/A'}<br>
                <strong>Sector:</strong> ${SECTOR_NAM || 'N/A'}
            `;
        }

        // Display Popup
        if (popupContent) {
            L.popup()
                .setLatLng(e.latlng)
                .setContent(popupContent)
                .openOn(map);
        } 
    } catch (error) {
        console.error("Error fetching WFS data:", error);
        
    }
});