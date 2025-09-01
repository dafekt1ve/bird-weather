// Updated checklist-wind-map.js - Extract data and provide options for viewing weather
(async function () {
    if (document.getElementById("weather-options-container")) {
        console.log("Weather options already exists. Skipping injection.");
        return;
    }

    // Configuration - Update this URL to your weather website
    const WEATHER_SITE_URL = 'https://dafekt1ve.github.io'; // CHANGE THIS to your actual domain
    
    // === Coordinate & date extraction ===
    function getLatLonFromLink() {
        const link = document.querySelector("a[title='View with Google Maps']");
        if (!link) return null;
        const match = new URL(link.href).search.match(/query=(-?\d+\.?\d*),(-?\d+\.?\d*)/);
        return match ? { lat: parseFloat(match[1]), lon: parseFloat(match[2]) } : null;
    }

    function getChecklistDate() {
        const timeEl = document.querySelector("time[datetime]");
        return timeEl?.getAttribute("datetime") ?? null;
    }

    function getChecklistId() {
        const url = window.location.href;
        const match = url.match(/\/checklist\/([A-Z0-9]+)/);
        return match ? match[1] : null;
    }

    function getLocationName() {
        // Try multiple selectors to find the actual location name
        const locationSelectors = [
            // Primary location selectors (most specific first)
            '.Heading-main .Heading-main-text',
            '.Checklist-meta-location',
            '.Checklist-meta-location a',
            '.Heading-main h1',
            
            // Secondary selectors
            'a[href*="/region/"]',
            'h1:not([class*="Date"]):not([class*="Time"])',
            
            // Fallback selectors
            '.Heading-main',
            'h1'
        ];
        
        for (const selector of locationSelectors) {
            const element = document.querySelector(selector);
            if (element && element.textContent.trim()) {
                const text = element.textContent.trim();
                
                // Skip if it looks like a date
                if (isDateString(text)) {
                    console.log(`Skipping date-like text: ${text}`);
                    continue;
                }
                
                // Skip if it contains obvious date patterns
                if (text.match(/\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b/i) ||
                    text.match(/\b\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4}\b/) ||
                    text.match(/\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/i)) {
                    console.log(`Skipping date pattern: ${text}`);
                    continue;
                }
                
                console.log(`Found location: ${text}`);
                return text;
            }
        }
        
        // If we still can't find a good location name, try to extract from URL or other sources
        const urlPath = window.location.pathname;
        const regionMatch = urlPath.match(/\/region\/([^\/]+)/);
        if (regionMatch) {
            return regionMatch[1].replace(/-/g, ' ');
        }
        
        return 'Unknown Location';
    }

    function isDateString(text) {
        // Check if the text looks like a date
        const datePatterns = [
            /^\w+\s+\d{1,2}\s+\w+\s+\d{4}$/,  // "Sun 31 Aug 2025"
            /^\d{1,2}\/\d{1,2}\/\d{2,4}$/,     // "8/31/2025"
            /^\d{4}-\d{2}-\d{2}$/,             // "2025-08-31"
            /^\w+,?\s+\w+\s+\d{1,2},?\s+\d{4}$/  // "Sunday, August 31, 2025"
        ];
        
        return datePatterns.some(pattern => pattern.test(text.trim()));
    }

    // === Create weather options UI ===
    function createWeatherOptionsUI() {
        const container = document.createElement("div");
        container.id = "weather-options-container";
        container.style.cssText = `
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            border: 1px solid #475569;
            border-radius: 12px;
            padding: 20px;
            margin: 1em 0;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            position: relative;
            overflow: hidden;
        `;

        // Add background pattern
        container.innerHTML = `
            <div style="position: absolute; top: -50%; right: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%); pointer-events: none;"></div>
            
            <div style="position: relative; z-index: 2;">
                <div style="display: flex; align-items: center; margin-bottom: 16px;">
                    <span style="font-size: 24px; margin-right: 12px;">🌤️</span>
                    <h3 style="margin: 0; font-size: 20px; font-weight: 600; background: linear-gradient(135deg, #3b82f6, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">Weather Mapping Options</h3>
                </div>
                
                <div style="display: grid; gap: 12px; margin-bottom: 16px;">
                    <div id="location-info" style="background: rgba(30, 41, 59, 0.6); padding: 12px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 4px;">Checklist Location</div>
                        <div id="location-details" style="font-weight: 500;">Loading location data...</div>
                    </div>
                    
                    <div id="date-info" style="background: rgba(30, 41, 59, 0.6); padding: 12px; border-radius: 8px; border-left: 4px solid #06b6d4;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 4px;">Observation Date</div>
                        <div id="date-details" style="font-weight: 500;">Loading date...</div>
                    </div>
                </div>
                
                <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                    <button id="launch-weather-btn" style="
                        flex: 1;
                        background: linear-gradient(135deg, #3b82f6, #06b6d4);
                        color: white;
                        border: none;
                        padding: 14px 20px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 15px;
                        font-weight: 500;
                        transition: all 0.3s ease;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        min-width: 200px;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 25px rgba(59, 130, 246, 0.4)';" 
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none';">
                        <span>🚀</span> Launch Weather Map
                    </button>
                    
                    <button id="show-inline-btn" style="
                        background: rgba(75, 85, 99, 0.8);
                        color: white;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        padding: 14px 20px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 15px;
                        font-weight: 500;
                        transition: all 0.3s ease;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        min-width: 150px;
                    " onmouseover="this.style.background='rgba(107, 114, 128, 0.9)'; this.style.transform='translateY(-1px)';" 
                       onmouseout="this.style.background='rgba(75, 85, 99, 0.8)'; this.style.transform='translateY(0)';">
                        <span>📍</span> Show Here
                    </button>
                </div>
                
                <div id="status-message" style="margin-top: 12px; font-size: 13px; opacity: 0.8;">
                    Choose how you'd like to view weather conditions for this checklist location.
                </div>
            </div>
        `;

        return container;
    }

    // === Launch weather website ===
    function launchWeatherSite(checklistData) {
        const params = new URLSearchParams({
            lat: checklistData.lat,
            lng: checklistData.lng,
            datetime: checklistData.datetime,
            // location: checklistData.location,  // REMOVED - we don't need it in URL
            checklistId: checklistData.checklistId || '',
            source: 'ebird-extension'
        });

        const weatherUrl = `https://dafekt1ve.github.io/index.html?${params.toString()}`;
        console.log('Opening weather URL:', weatherUrl);
        window.open(weatherUrl, '_blank');
        
        const statusEl = document.getElementById('status-message');
        if (statusEl) {
            statusEl.innerHTML = '✅ <span style="color: #86efac;">Weather map opened in new tab!</span>';
        }
    }

    // === Your existing inline map functionality ===
    async function showInlineWeatherMap(checklistData) {
        // Update status to show loading
        const statusEl = document.getElementById('status-message');
        if (statusEl) {
            statusEl.innerHTML = '⏳ <span style="color: #fbbf24;">Loading inline weather map...</span>';
        }

        // Hide the options container to make room for the map
        const optionsContainer = document.getElementById('weather-options-container');
        if (optionsContainer) {
            optionsContainer.style.display = 'none';
        }

        // Load your existing inline map code here
        // This would be your current checklist-wind-map.js functionality
        try {
            await loadInlineWindMap(checklistData);
            
            // Add a "back to options" button
            addBackToOptionsButton();
            
        } catch (error) {
            console.error('Failed to load inline weather map:', error);
            if (statusEl) {
                statusEl.innerHTML = '❌ <span style="color: #fca5a5;">Failed to load weather map. Try the external site option.</span>';
            }
            // Show options again if inline fails
            if (optionsContainer) {
                optionsContainer.style.display = 'block';
            }
        }
    }

    // === Your existing wind map code (refactored as a function) ===
    async function loadInlineWindMap(checklistData) {
        if (!window.L || !window.d3) {
            throw new Error("Leaflet or D3 not loaded.");
        }

        if (document.getElementById("gfs-wind-map")) {
            document.getElementById("gfs-wind-map").remove();
        }

        // Cache for wind data per pressure level
        const windDataByLevel = {};
        let currentVelocityLayer = null;

        // Map container
        const mapDiv = document.createElement("div");
        mapDiv.id = "gfs-wind-map";
        mapDiv.style =
            "height: 400px; margin: 1em 0; border: 2px solid #ccc; border-radius: 8px; position: relative;";

        // Insert map
        const targetElement = document.querySelector("div.Page-section.Page-section--white.Page-section--grid-content.u-inset-responsive div.Page-section-inner");
        if (!targetElement) throw new Error("Target element not found");
        targetElement.parentNode.insertBefore(mapDiv, targetElement);

        // Add spinner and loading overlay (your existing code)
        const spinner = document.createElement("div");
        spinner.id = "loading-spinner";
        spinner.style.cssText = `
            position: absolute; top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            width: 50px; height: 50px;
            border: 6px solid #f3f3f3;
            border-top: 6px solid #3498db;
            border-radius: 50%;
            animation: spin 2s linear infinite;
            z-index: 99999;
        `;
        mapDiv.appendChild(spinner);

        // Add CSS for spinner animation
        if (!document.querySelector('#spinner-style')) {
            const style = document.createElement("style");
            style.id = 'spinner-style';
            style.innerHTML = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }`;
            document.head.appendChild(style);
        }

        // Check date validity
        const checklistDate = new Date(checklistData.datetime);
        const earliestGFSDate = new Date("2021-01-01T00:00:00Z");
        if (checklistDate < earliestGFSDate) {
            throw new Error("No wind data available before January 1, 2021.");
        }

        // Initialize map (your existing map initialization code)
        const map = L.map("gfs-wind-map", {maxBounds: [[-90, -Infinity], [90, Infinity]]})
            .setView([checklistData.lat, checklistData.lng], 5);

        // Add your existing base layers
        const googleStreets = L.tileLayer('https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',{
            maxZoom: 15,
            subdomains:['mt0','mt1','mt2','mt3'],
            attribution: "&copy; Google",
        }).addTo(map);

        // ... (add other base layers as in your original code)

        // Add controls
        map.addControl(new L.Control.Fullscreen());

        // Load wind data for all levels (your existing data loading)
        for (const level of ["925", "900", "850", "800", "750", "700"]) {
            try {
                const data = await requestGFSDataViaBackground(checklistData.lat, checklistData.lng, checklistData.datetime, level);
                if (Array.isArray(data)) windDataByLevel[level] = data;
            } catch (err) {
                console.warn(`❌ Failed to fetch ${level}mb data:`, err);
            }
        }

        spinner.style.display = "none";
        
        // Update wind layer (use your existing updateWindLayer function)
        // ... (your existing wind layer code)

        console.log("Inline weather map loaded successfully");
    }

    // === Request GFS data via background script ===
    function requestGFSDataViaBackground(lat, lon, date, level) {
        return new Promise((resolve, reject) => {
            chrome.runtime.sendMessage(
                {
                    type: "fetchGFSData",
                    lat, lon, date, level
                },
                (response) => {
                    if (chrome.runtime.lastError) return reject(chrome.runtime.lastError);
                    response?.success ? resolve(response.data) : reject(response?.error || "Unknown error");
                }
            );
        });
    }

    // === Add back to options button ===
    function addBackToOptionsButton() {
        const backBtn = document.createElement('button');
        backBtn.innerHTML = '← Back to Options';
        backBtn.style.cssText = `
            background: rgba(75, 85, 99, 0.9);
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            margin: 10px 0;
            transition: background 0.2s ease;
        `;
        backBtn.onmouseover = () => backBtn.style.background = 'rgba(107, 114, 128, 0.9)';
        backBtn.onmouseout = () => backBtn.style.background = 'rgba(75, 85, 99, 0.9)';
        backBtn.onclick = () => {
            // Remove inline map
            const mapEl = document.getElementById("gfs-wind-map");
            if (mapEl) mapEl.remove();
            
            // Show options again
            const optionsContainer = document.getElementById('weather-options-container');
            if (optionsContainer) {
                optionsContainer.style.display = 'block';
            }
            backBtn.remove();
        };

        const targetElement = document.querySelector("div.Page-section.Page-section--white.Page-section--grid-content.u-inset-responsive div.Page-section-inner");
        if (targetElement) {
            targetElement.parentNode.insertBefore(backBtn, targetElement);
        }
    }

    // === Main logic ===
    try {
        const coords = getLatLonFromLink();
        const date = getChecklistDate();
        const checklistId = getChecklistId();
        const location = getLocationName();
        
        if (!coords || !date) {
            console.warn("Missing coordinates or date - cannot show weather options");
            return;
        }

        const checklistData = {
            lat: coords.lat,
            lng: coords.lon,
            datetime: date,
            location: location,
            checklistId: checklistId
        };

        // Create and insert weather options UI
        const weatherOptions = createWeatherOptionsUI();
        const targetElement = document.querySelector("div.Page-section.Page-section--white.Page-section--grid-content.u-inset-responsive div.Page-section-inner");
        if (!targetElement) return;
        
        targetElement.parentNode.insertBefore(weatherOptions, targetElement);

        // Update the UI with extracted data
        document.getElementById('location-details').innerHTML = `
            <strong>${location}</strong><br>
            <small style="opacity: 0.8;">${coords.lat.toFixed(4)}, ${coords.lon.toFixed(4)}</small>
        `;

        const dateObj = new Date(date);
        document.getElementById('date-details').innerHTML = `
            <strong>${dateObj.toLocaleDateString()}</strong> at <strong>${dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</strong><br>
            <small style="opacity: 0.8;">${checklistId ? `Checklist ${checklistId}` : 'Individual observation'}</small>
        `;

        // Add event listeners
        document.getElementById('launch-weather-btn').addEventListener('click', () => {
            launchWeatherSite(checklistData);
        });

        document.getElementById('show-inline-btn').addEventListener('click', () => {
            showInlineWeatherMap(checklistData);
        });

        console.log("Weather options UI loaded successfully", checklistData);

    } catch (error) {
        console.warn("Could not initialize weather options:", error);
    }
})();