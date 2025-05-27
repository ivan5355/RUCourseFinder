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
            console.log("User denied the request for Geolocation.");
            break;
        case error.POSITION_UNAVAILABLE:
            console.log("Location information is unavailable.");
            break;
        case error.TIMEOUT:
            console.log("The request to get user location timed out.");
            break;
        case error.UNKNOWN_ERROR:
            console.log("An unknown error occurred.");
            break;
    }
}

function clearSearch() {
    $('#search-results').empty();
}

function search() {
    const searchTerm = $('#search-bar').val();
    const $loadingElement = $('.loading');
    const $resultsContainer = $('#search-results');

    if (!searchTerm.trim()) {
        $resultsContainer.html('<p class="error-message">Please enter a search term.</p>');
        return;
    }

    $loadingElement.show();
    $resultsContainer.empty();

    const cacheKey = `${currentSearchType}:${searchTerm}`; 
    const cachedResults = localStorage.getItem(cacheKey);

    if (cachedResults) {
        displayCourses(JSON.parse(cachedResults));
        $loadingElement.hide(); 
        return; 
    }

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
                    localStorage.setItem(cacheKey, JSON.stringify(data.courses));
                } else {
                    $resultsContainer.html('<p class="no-results">No courses found matching your search.</p>');
                }
            } else {
                if (data.results && data.results.length > 0) {
                    displayProfessorResults(data.results);
                } else {
                    $resultsContainer.html('<p class="no-results">No professors found matching your search.</p>');
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
            const $professorDiv = $('<div>').addClass('course');
            const $professorName = $('<h3>').text(result.professor);
            const $coursesList = $('<div>');

            result.courses.forEach(course => {
                const $courseInfo = $('<p>').text(`${course.courseString} - ${course.title}`);
                $coursesList.append($courseInfo);
            });

            $professorDiv.append($professorName, $coursesList);
            $coursesContainer.append($professorDiv);
        });
    } else {
        const $messageElement = $('<p>')
            .addClass('no-results')
            .text('No professors found.');
        $coursesContainer.append($messageElement);
    }
} 