// Hamburger navigation menu — opens/closes a slide-out nav panel

const navToggle = document.getElementById('nav_toggle');

// Open the menu: lock body scroll, compensate for scrollbar width, show menu + backdrop
function openMenu() {
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.paddingRight = scrollbarWidth + 'px';
    document.body.style.overflow = 'hidden';
    document.getElementById('nav_menu').classList.add('is-open');
    document.getElementById('nav_backdrop').classList.add('is-open');
    document.getElementById('nav_icon').classList.add('is-open');
    navToggle.setAttribute('aria-expanded', 'true');
}

// Close the menu: restore body scroll and hide menu + backdrop
function closeMenu() {
    document.getElementById('nav_menu').classList.remove('is-open');
    document.getElementById('nav_backdrop').classList.remove('is-open');
    document.getElementById('nav_icon').classList.remove('is-open');
    navToggle.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
}

// Toggle menu on hamburger button click
navToggle.onclick = function() {
    const isOpen = document.getElementById('nav_icon').classList.contains('is-open');
    isOpen ? closeMenu() : openMenu();
};

// Close menu when clicking the backdrop overlay
document.getElementById('nav_backdrop').onclick = closeMenu;

// Close menu on Escape key
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && document.getElementById('nav_icon').classList.contains('is-open')) {
        closeMenu();
    }
});

// Close menu on back/forward navigation (bfcache restore)
window.addEventListener('pageshow', closeMenu);
