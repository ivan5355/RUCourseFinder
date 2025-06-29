
// Storing and Caching User Location 

//1. Gets the user's cached location from localStorage
//2. If valid location exists, send to backend
//3. If no valid location exists, prompt user for fresh location
//4. If user denies location, show error message

// Getting and Caching Search Results

//1. Gets the user's cached search results from localStorage
//2. If valid search results exist, use them
//3. If no valid search results exist, prompt user for fresh search results
//4. If user denies search results, show error message


// Initialize location on page load
window.addEventListener('DOMContentLoaded', function() {
    // Check if valid location is cached
    const cachedLocation = getCachedLocation();

    // If valid location exists, send to backend
    if (cachedLocation) {
        saveLocationToBackend(cachedLocation.latitude, cachedLocation.longitude);
    } else {
        // No valid cached location, prompt user for fresh location
        getLocation();
    }
}); 

function getLocation() {
    if (navigator.geolocation) {

        //position argument is implicitly passed to sendPosition
        navigator.geolocation.getCurrentPosition(sendPosition, showError);
    } else {
        $("#location").html("Geolocation is not supported by this browser.");
    }
}

// Send location to backend
function saveLocationToBackend(latitude, longitude) {
    $.ajax({
        url: '/save_location',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            latitude: latitude,
            longitude: longitude
        }),
        success: function(data) {
            console.log('Location saved successfully:', data);
        },
        error: function(error) {
            console.error('Error saving location:', error);
            // If error with cached location, try to get fresh location
            if (!position) {
                getLocation();
            }
        }
    });
}

function sendPosition(position) {
    const latitude = position.coords.latitude;
    const longitude = position.coords.longitude;

    // Save to localStorage
    saveLocationToLocalStorage(latitude, longitude);

    // Send to backend
    saveLocationToBackend(latitude, longitude);
}

function saveLocationToLocalStorage(latitude, longitude) {
    const locationData = {
        latitude: latitude,
        longitude: longitude,
        timestamp: new Date().getTime()
    };
    localStorage.setItem('user_location', JSON.stringify(locationData));
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


function getCachedLocation() {
    try {
        const cachedData = localStorage.getItem('user_location');
        
        if (cachedData) {
            const locationData = JSON.parse(cachedData);
            if (isValidCache(locationData)) {
                console.log('Using cached location');
                return {
                    latitude: locationData.latitude,
                    longitude: locationData.longitude
                };
            } else {
                // Remove expired location cache
                localStorage.removeItem('user_location');
                console.log('Location cache expired');
            }
        }
    } catch (error) {
        console.error('Error reading location cache:', error);
        localStorage.removeItem('user_location');
    }
    
    return null;
}


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

        // Get all keys in localStorage
        const keys = Object.keys(localStorage);
        const now = new Date().getTime();
        const twentyFourHours = 24 * 60 * 60 * 1000;
        
        // Iterate through all keys in localStorage
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


