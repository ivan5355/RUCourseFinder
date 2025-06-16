let currentSearchType = 'title'; 

$(document).ready(function() {

    // Initialize location on page load
    getLocation();
    
    // Event listeners for search type toggles
    $('#toggle-course-title').on('change', function() {
    currentSearchType = 'title';
        $('#search-bar').attr('placeholder', "Enter course title (e.g., Calculus)");
});

    $('#toggle-professor').on('change', function() {
    currentSearchType = 'professor';
        $('#search-bar').attr('placeholder', "Enter professor last name (e.g., Smith)");
});

    $('#toggle-course-code').on('change', function() {
    currentSearchType = 'code';
        $('#search-bar').attr('placeholder', "Enter last 3 digits of course code (e.g., 101)");
});

    // Search form submission
    $('#search-form').on('submit', function(event) {
        event.preventDefault();
        clearSearch();
        search();
    });
});

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

function clearSearch() {
    $('#search-results').empty();
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

function search() {
    const searchTerm = $('#search-bar').val();
    const $loadingElement = $('.loading');
    const $resultsContainer = $('#search-results');

    if (!searchTerm.trim()) {
        $resultsContainer.html('<p class="error-message">Please enter a search term.</p>');
        return;
    }

    // Check cache first
    const cachedResults = getCachedResults(currentSearchType, searchTerm);
    if (cachedResults) {
        // Cache for course searches
        if (currentSearchType === 'title' || currentSearchType === 'code') {
            if (cachedResults.length > 0) {
                displayCourses(cachedResults);
            } else {
                $resultsContainer.html('<p class="no-results">No courses found matching your search.</p>');
            }
        // Cache for professor searches
        } else { 
            if (cachedResults.length > 0) {
                displayProfessorResults(cachedResults);
            } else {
                $resultsContainer.html('<p class="no-results">No professors found matching your search.</p>');
            }
        }
        return;
    }

    // No valid cache, make API call
    $loadingElement.show();
    $resultsContainer.empty();

    let endpoint;
    switch(currentSearchType) {
        case 'title':
            endpoint = '/search_by_title';
            break;
        case 'professor':
            endpoint = '/search_by_professor';
            break;
        case 'code':
            endpoint = '/search_by_code';
            break;
        default:
            endpoint = '/search_by_title';
    }

    $.ajax({
        url: endpoint,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ searchTerm: searchTerm }),
        success: function(data) {
        if (data.status === 'error') {
                $resultsContainer.html(`<p class="error-message">${data.message}</p>`);
            return;
        }
        
        if (currentSearchType === 'title' || currentSearchType === 'code') {
            if (data.courses && data.courses.length > 0) {
                displayCourses(data.courses);
                // Cache the results
                setCachedResults(currentSearchType, searchTerm, data.courses);
            } else {
                    $resultsContainer.html('<p class="no-results">No courses found matching your search.</p>');
                // Cache empty results too
                setCachedResults(currentSearchType, searchTerm, []);
            }
            
            // Cache for professor searches
        } else {
          
            if (data.results && data.results.length > 0) {
                displayProfessorResults(data.results);

                // Cache the results
                setCachedResults(currentSearchType, searchTerm, data.results);
            } else {
                    $resultsContainer.html('<p class="no-results">No professors found matching your search.</p>');
                // Cache empty results too
                setCachedResults(currentSearchType, searchTerm, []);
            }
        }
        },
        error: function(error) {
        console.error('Error:', error);
            $resultsContainer.html('<p class="error-message">An error occurred while searching. Please try again.</p>');
        },
        complete: function() {
            $loadingElement.hide();
        }
    });
}

function displayCourses(courses) {
    const $coursesContainer = $('#search-results');
    $coursesContainer.empty();

    if (courses.length > 0) {
        courses.forEach(course => {
            const $courseDiv = $('<div>').addClass('course');

            // Course Header
            const $headerDiv = $('<div>').addClass('course-header');
            
            const $titleDiv = $('<div>').addClass('course-info');
            const $titleSpan = $('<span>').addClass('course-title').text(course.title);
            const $codeSpan = $('<span>').addClass('course-code').text(course.course_number);
            
            const $catalogLink = $('<a>')
                .addClass('catalog-link')
                .attr('target', '_blank')
                .attr('rel', 'noopener noreferrer');
            
            if (course.synopsisUrl && course.synopsisUrl.trim() !== '') {
                $catalogLink
                    .attr('href', course.synopsisUrl)
                    .html('<i class="fas fa-external-link-alt"></i> Course Details');
            } else {
                $catalogLink
                    .html('<i class="fas fa-info-circle"></i> Details Not Available')
                    .css({
                        'pointer-events': 'none',
                        'opacity': '0.6',
                        'cursor': 'default'
                    })
                    .removeAttr('href target rel');
            }
            
            $titleDiv.append($titleSpan, $codeSpan);
            $headerDiv.append($titleDiv, $catalogLink);
            $courseDiv.append($headerDiv);

            // Professors Section
            if (course.instructors && course.instructors.length > 0) {
                const $profSection = $('<div>').addClass('course-section');
                const $profTitle = $('<div>').addClass('section-title').text('Professors');
                const $profList = $('<ul>').addClass('professor-list');
                
                course.instructors.forEach(instructorGroup => {
                    instructorGroup.forEach(instructor => {
                        const $profItem = $('<li>')
                            .addClass('professor-item')
                            .text(instructor.name);
                        $profList.append($profItem);
                    });
                });
                
                $profSection.append($profTitle, $profList);
                $courseDiv.append($profSection);
            }

            // Prerequisites Section
            const $prereqSection = $('<div>').addClass('course-section');
            const $prereqTitle = $('<div>').addClass('section-title').text('Prerequisites');
            const $prereqContent = $('<div>').addClass('prerequisites').text(course.prerequisites);
            
            $prereqSection.append($prereqTitle, $prereqContent);
            $courseDiv.append($prereqSection);

            // Equivalencies Section
            if (course.equivalencies && course.equivalencies.length > 0) {
                const $equivSection = $('<div>').addClass('equivalencies');
                const $equivTitle = $('<div>').addClass('section-title').text('Community College Equivalencies');
                $equivSection.append($equivTitle);
                
                course.equivalencies.forEach(equiv => {
                    const $equivItem = $('<div>').addClass('equivalency-item');
                    
                    const $collegeName = $('<span>')
                        .addClass('college-name')
                        .text(equiv.community_college);
                    
                    const $distance = $('<span>')
                        .addClass('distance')
                        .text(`${equiv.Distance} miles`);
                    
                    const $equivCode = $('<span>')
                        .addClass('course-code-equiv')
                        .text(`${equiv.code} ${equiv.name}`);
                    
                    $equivItem.append($collegeName, $distance, $equivCode);
                    $equivSection.append($equivItem);
                });
                
                $courseDiv.append($equivSection);
            }

            $coursesContainer.append($courseDiv);
        });
    } else {
        const $messageElement = $('<div>')
            .addClass('no-results')
            .text('No courses found matching your search.');
        $coursesContainer.append($messageElement);
    }
}

function displayProfessorResults(results) {
    const $coursesContainer = $('#search-results');
    $coursesContainer.empty();

    if (results.length > 0) {
        results.forEach(result => {

            // Only display normal professor results (skip suggestions)
            if (result.professor && result.courses && !result.suggestions) {
                const $professorDiv = $('<div>').addClass('course');
                const $professorName = $('<h3>').text(result.professsor);
                const $coursesList = $('<div>');

                result.courses.forEach(course => {
                    const $courseInfo = $('<p>').text(`${course.courseString} - ${course.title}`);
                    $coursesList.append($courseInfo);
                });

                $professorDiv.append($professorName, $coursesList);
                $coursesContainer.append($professorDiv);
            }
        });
    } else {
        const $messageElement = $('<p>')
            .addClass('no-results')
            .text('No professors found.');
        $coursesContainer.append($messageElement);
    }
}

function saveLocationToLocalStorage(latitude, longitude) {
    localStorage.setItem('user_latitude', latitude);
    localStorage.setItem('user_longitude', longitude);
}


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