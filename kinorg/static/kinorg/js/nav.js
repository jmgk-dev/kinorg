function openMenu() {
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.paddingRight = scrollbarWidth + 'px';
    document.body.style.overflow = 'hidden';
    document.getElementById('nav_menu').classList.add('is-open');
    document.getElementById('nav_backdrop').classList.add('is-open');
    document.getElementById('nav_icon').classList.add('is-open');
}

function closeMenu() {
    document.getElementById('nav_menu').classList.remove('is-open');
    document.getElementById('nav_backdrop').classList.remove('is-open');
    document.getElementById('nav_icon').classList.remove('is-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
}

document.getElementById('nav_toggle').onclick = function() {
    const isOpen = document.getElementById('nav_icon').classList.contains('is-open');
    isOpen ? closeMenu() : openMenu();
};

document.getElementById('nav_backdrop').onclick = closeMenu;

window.addEventListener('pageshow', closeMenu);
