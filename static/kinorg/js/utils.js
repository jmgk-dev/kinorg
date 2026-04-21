// Shared utilities used across all Kinorg JS files.
// Loaded in base.html before any page-specific scripts.

// CSRF token — needed for all POST requests to Django.
// Reads the 'csrftoken' cookie set by Django's CSRF middleware.
// Returns an empty string if the cookie isn't found (e.g. logged-out pages).
function getCsrf() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
}
