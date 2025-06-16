
function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(sendPosition, showError);
    } else {
        $("#location").html("Geolocation is not supported by this browser.");
    }
}

function sendPosition(position) {
    const latitude = position.coords.latitude;
    const longitude = position.coords.longitude;

    // Save to localStorage
    saveLocationToLocalStorage(latitude, longitude);

    // Send to backend
    $.ajax({
        url: '/save_location',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            latitude: latitude,
            longitude: longitude
        }),
        success: function(data) {
            console.log('Success:', data);
        },
        error: function(error) {
            console.error('Error:', error);
        }
    });
}

function showError(error) {
    switch(error.code) {
        case error.PERMISSION_DENIED:
            $("#location").html("User denied the request for Geolocation.");
            break;
        case error.POSITION_UNAVAILABLE:
            $("#location").html("Location information is unavailable.");
            break;
        case error.TIMEOUT:
            $("#location").html("The request to get user location timed out.");
            break;
        case error.UNKNOWN_ERROR:
            $("#location").html("An unknown error occurred.");
            break;
    }
}

function saveLocationToLocalStorage(latitude, longitude) {
    localStorage.setItem('user_latitude', latitude);
    localStorage.setItem('user_longitude', longitude);
}

// Cache Management Functions
function getCacheKey(searchType, searchTerm) {
    return `search_cache_${searchType}_${searchTerm.toLowerCase().trim()}`;
}

function isValidCache(cacheData) {
    if (!cacheData) return false;
    
    const now = new Date().getTime();
    const cacheTime = cacheData.timestamp;
    const twentyFourHours = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
    
    return (now - cacheTime) < twentyFourHours;
}

function getCachedResults(searchType, searchTerm) {
    try {
        const cacheKey = getCacheKey(searchType, searchTerm);
        const cachedData = localStorage.getItem(cacheKey);
        
        if (cachedData) {
            const parsedCache = JSON.parse(cachedData);
            if (isValidCache(parsedCache)) {
                console.log('Using cached results for:', searchTerm);
                return parsedCache.data;
            } else {
                // Remove expired cache
                localStorage.removeItem(cacheKey);
                console.log('Cache expired for:', searchTerm);
            }
        }
    } catch (error) {
        console.error('Error reading cache:', error);
    }
    
    return null;
}

function setCachedResults(searchType, searchTerm, data) {
    try {
        const cacheKey = getCacheKey(searchType, searchTerm);
        const cacheData = {
            timestamp: new Date().getTime(),
            data: data
        };
        
        localStorage.setItem(cacheKey, JSON.stringify(cacheData));
        console.log('Cached results for:', searchTerm);
    } catch (error) {
        console.error('Error saving to cache:', error);
        // If storage is full, clear old cache entries
        if (error.name === 'QuotaExceededError') {
            clearExpiredCache();
            // Try to cache again after cleanup
            try {
                localStorage.setItem(cacheKey, JSON.stringify(cacheData));
            } catch (e) {
                console.error('Still unable to cache after cleanup:', e);
            }
        }
    }
}

function clearExpiredCache() {
    try {
        const keys = Object.keys(localStorage);
        const now = new Date().getTime();
        const twentyFourHours = 24 * 60 * 60 * 1000;
        
        keys.forEach(key => {
            if (key.startsWith('search_cache_')) {
                const cachedData = localStorage.getItem(key);
                if (cachedData) {
                    const parsedCache = JSON.parse(cachedData);
                    if ((now - parsedCache.timestamp) >= twentyFourHours) {
                        localStorage.removeItem(key);
                        console.log('Removed expired cache:', key);
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error clearing expired cache:', error);
    }
}

// Initialize location on page load
window.addEventListener('DOMContentLoaded', function() {
    const savedLat = localStorage.getItem('user_latitude');
    const savedLng = localStorage.getItem('user_longitude');
    if (savedLat && savedLng) {
        // Send saved location to backend automatically
        $.ajax({
            url: '/save_location',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                latitude: parseFloat(savedLat),
                longitude: parseFloat(savedLng)
            }),
            success: function(data) {
                console.log('Saved location loaded:', data);
            },
            error: function(error) {
                console.error('Error loading saved location:', error);
                // If error, get fresh location
                getLocation();
            }
        });
    } else {
        // Prompt user for location if not saved
        getLocation();
    }
}); 