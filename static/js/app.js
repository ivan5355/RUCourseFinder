let currentSearchType = 'title'; 

$(document).ready(function() {
    
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

    // Check cache first (only for course searches, not professor searches)
    if (currentSearchType === 'title' || currentSearchType === 'code') {
        const cachedResults = getCachedResults(currentSearchType, searchTerm);
        if (cachedResults) {
            if (cachedResults.length > 0) {
                displayCourses(cachedResults);
            } else {
                $resultsContainer.html('<p class="no-results">No courses found matching your search.</p>');
            }
            return;
        }
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
        } else { // Professor searches - no caching
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

    if (!results || results.length === 0) {
        $coursesContainer.html('<p class="no-results">No professors found matching your search.</p>');
        return;
    }

    // Check if the result is a suggestion object
    const firstResult = results[0];
    if (firstResult.suggestions && Array.isArray(firstResult.suggestions)) {
        const $suggestionsDiv = $('<div>').addClass('course suggestions-container');
        const $messageDiv = $('<div>').addClass('suggestions-message').text(firstResult.message);
        const $suggestionsList = $('<div>').addClass('suggestions-list');

        firstResult.suggestions.forEach(suggestion => {
            const $suggestionItem = $('<div>')
                .addClass('suggestion-item')
                .text(suggestion)
                .on('click', function() {
                    $('#search-bar').val(suggestion);
                    search();
                });
            $suggestionsList.append($suggestionItem);
        });

        $suggestionsDiv.append($messageDiv, $suggestionsList);
        $coursesContainer.append($suggestionsDiv);
    } else {
        // Otherwise, display the list of matched professors and their courses
        results.forEach(result => {
            if (result.professor && result.courses) {
                const $professorDiv = $('<div>').addClass('course');
                const $professorName = $('<h3>').text(result.professor);
                const $coursesList = $('<div>');

                if (result.courses.length > 0) {
                    result.courses.forEach(course => {
                        const $courseInfo = $('<p>').text(`${course.courseString} - ${course.title}`);
                        $coursesList.append($courseInfo);
                    });
                } else {
                    $coursesList.append($('<p>').text('No courses found for this professor.'));
                }

                $professorDiv.append($professorName, $coursesList);
                $coursesContainer.append($professorDiv);
            }
        });
    }
} 