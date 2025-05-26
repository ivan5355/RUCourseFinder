let currentSearchType = 'title'; 

document.getElementById('toggle-course-title').addEventListener('change', function() {
    currentSearchType = 'title';
    document.getElementById('search-bar').placeholder = "Enter course title (e.g., Calculus)";
});

document.getElementById('toggle-professor').addEventListener('change', function() {
    currentSearchType = 'professor';
    document.getElementById('search-bar').placeholder = "Enter professor last name (e.g., Smith)";
});

document.getElementById('toggle-course-code').addEventListener('change', function() {
    currentSearchType = 'code';
    document.getElementById('search-bar').placeholder = "Enter last 3 digits of course code (e.g., 101)";
});

window.onload = function() {
     getLocation();
};

function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(sendPosition, showError);
    } else {
        document.getElementById("location").innerHTML = "Geolocation is not supported by this browser.";
    }
}

function sendPosition(position) {
    var latitude = position.coords.latitude;
    var longitude = position.coords.longitude;

    fetch('/save_location', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            latitude: latitude,
            longitude: longitude
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
    })
    .catch((error) => {
        console.error('Error:', error);
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

document.getElementById('search-form').addEventListener('submit', function(event) {
    event.preventDefault();
    clearSearch();
    search();
});

function clearSearch() {
    var resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = '';
}

function search() {
    var searchTerm = document.getElementById('search-bar').value;
    var loadingElement = document.querySelector('.loading');
    var resultsContainer = document.getElementById('search-results');

    if (!searchTerm.trim()) {
        resultsContainer.innerHTML = '<p class="error-message">Please enter a search term.</p>';
        return;
    }

    loadingElement.style.display = 'block';
    resultsContainer.innerHTML = '';

    const cacheKey = `${currentSearchType}:${searchTerm}`; 
    const cachedResults = localStorage.getItem(cacheKey);

    if (cachedResults) {
        displayCourses(JSON.parse(cachedResults));
        loadingElement.style.display = 'none'; 
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

    fetch(endpoint, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ searchTerm: searchTerm }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'error') {
            resultsContainer.innerHTML = `<p class="error-message">${data.message}</p>`;
            return;
        }
        
        if (currentSearchType === 'title' || currentSearchType === 'code') {
            if (data.courses && data.courses.length > 0) {
                displayCourses(data.courses);
                localStorage.setItem(cacheKey, JSON.stringify(data.courses));
            } else {
                resultsContainer.innerHTML = '<p class="no-results">No courses found matching your search.</p>';
            }
        } else {
            if (data.results && data.results.length > 0) {
                displayProfessorResults(data.results);
            } else {
                resultsContainer.innerHTML = '<p class="no-results">No professors found matching your search.</p>';
            }
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        resultsContainer.innerHTML = '<p class="error-message">An error occurred while searching. Please try again.</p>';
    })
    .finally(() => {
        loadingElement.style.display = 'none';
    });
}

function displayCourses(courses) {
    var coursesContainer = document.getElementById('search-results');
    coursesContainer.innerHTML = '';

    if (courses.length > 0) {
        courses.forEach(course => {
            var courseDiv = document.createElement('div');
            courseDiv.className = 'course';

            // Course Header
            var headerDiv = document.createElement('div');
            headerDiv.className = 'course-header';
            
            var titleDiv = document.createElement('div');
            titleDiv.className = 'course-info';
            var titleSpan = document.createElement('span');
            titleSpan.className = 'course-title';
            titleSpan.textContent = course.title;
            
            var codeSpan = document.createElement('span');
            codeSpan.className = 'course-code';
            codeSpan.textContent = course.course_number;
            
            var catalogLink = document.createElement('a');
            catalogLink.href = course.synopsisUrl || '#';
            catalogLink.className = 'catalog-link';
            catalogLink.target = '_blank';
            catalogLink.rel = 'noopener noreferrer';
            
            if (course.synopsisUrl && course.synopsisUrl.trim() !== '') {
                catalogLink.innerHTML = '<i class="fas fa-external-link-alt"></i> Course Details';
            } else {
                catalogLink.innerHTML = '<i class="fas fa-info-circle"></i> Details Not Available';
                catalogLink.style.pointerEvents = 'none';
                catalogLink.style.opacity = '0.6';
                catalogLink.style.cursor = 'default';
                catalogLink.removeAttribute('href');
                catalogLink.removeAttribute('target');
                catalogLink.removeAttribute('rel');
            }
            
            titleDiv.appendChild(titleSpan);
            titleDiv.appendChild(codeSpan);
            headerDiv.appendChild(titleDiv);
            headerDiv.appendChild(catalogLink);
            courseDiv.appendChild(headerDiv);

            // Professors Section
            if (course.instructors && course.instructors.length > 0) {
                var profSection = document.createElement('div');
                profSection.className = 'course-section';
                
                var profTitle = document.createElement('div');
                profTitle.className = 'section-title';
                profTitle.textContent = 'Professors';
                
                var profList = document.createElement('ul');
                profList.className = 'professor-list';
                
                course.instructors.forEach(instructorGroup => {
                    instructorGroup.forEach(instructor => {
                        var profItem = document.createElement('li');
                        profItem.className = 'professor-item';
                        profItem.textContent = instructor.name;
                        profList.appendChild(profItem);
                    });
                });
                
                profSection.appendChild(profTitle);
                profSection.appendChild(profList);
                courseDiv.appendChild(profSection);
            }

            // Prerequisites Section
            var prereqSection = document.createElement('div');
            prereqSection.className = 'course-section';
            
            var prereqTitle = document.createElement('div');
            prereqTitle.className = 'section-title';
            prereqTitle.textContent = 'Prerequisites';
            
            var prereqContent = document.createElement('div');
            prereqContent.className = 'prerequisites';
            prereqContent.textContent = course.prerequisites;
            
            prereqSection.appendChild(prereqTitle);
            prereqSection.appendChild(prereqContent);
            courseDiv.appendChild(prereqSection);

            // Equivalencies Section
            if (course.equivalencies && course.equivalencies.length > 0) {
                var equivSection = document.createElement('div');
                equivSection.className = 'equivalencies';
                
                var equivTitle = document.createElement('div');
                equivTitle.className = 'section-title';
                equivTitle.textContent = 'Community College Equivalencies';
                equivSection.appendChild(equivTitle);
                
                course.equivalencies.forEach(equiv => {
                    var equivItem = document.createElement('div');
                    equivItem.className = 'equivalency-item';
                    
                    var collegeName = document.createElement('span');
                    collegeName.className = 'college-name';
                    collegeName.textContent = equiv.community_college;
                    
                    var distance = document.createElement('span');
                    distance.className = 'distance';
                    distance.textContent = `${equiv.Distance} miles`;
                    
                    var equivCode = document.createElement('span');
                    equivCode.className = 'course-code-equiv';
                    equivCode.textContent = `${equiv.code} ${equiv.name}`;
                    
                    equivItem.appendChild(collegeName);
                    equivItem.appendChild(distance);
                    equivItem.appendChild(equivCode);
                    equivSection.appendChild(equivItem);
                });
                
                courseDiv.appendChild(equivSection);
            }

            coursesContainer.appendChild(courseDiv);
        });
    } else {
        var messageElement = document.createElement('div');
        messageElement.className = 'no-results';
        messageElement.textContent = 'No courses found matching your search.';
        coursesContainer.appendChild(messageElement);
    }
}

function displayProfessorResults(results) {
    var coursesContainer = document.getElementById('search-results');
    coursesContainer.innerHTML = '';

    if (results.length > 0) {
        for (var i = 0; i < results.length; i++) {
            var result = results[i];
            var professorDiv = document.createElement('div');
            professorDiv.className = 'course';

            var professorName = document.createElement('h3');
            professorName.textContent = result.professor;
            professorDiv.appendChild(professorName);

            var coursesList = document.createElement('div');

            for (var j = 0; j < result.courses.length; j++) {
                var course = result.courses[j];
                var courseInfo = document.createElement('p');
                courseInfo.textContent = `${course.courseString} - ${course.title}`;
                coursesList.appendChild(courseInfo);
            }

            professorDiv.appendChild(coursesList);
            coursesContainer.appendChild(professorDiv);
        }
    } else {
        var messageElement = document.createElement('p');
        messageElement.className = 'no-results';
        messageElement.textContent = 'No professors found.';
        coursesContainer.appendChild(messageElement);
    }
} 