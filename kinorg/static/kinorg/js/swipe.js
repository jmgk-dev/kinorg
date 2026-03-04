document.addEventListener('DOMContentLoaded', function () {
    const containers = document.querySelectorAll('#container');

    containers.forEach(container => {
        let startX = 0;
        let scrollStart = 0;
        let isDragging = false;

        container.addEventListener('touchstart', function (e) {
            isDragging = true;
            startX = e.touches[0].clientX;
            scrollStart = container.scrollLeft;

            // Pause the CSS animation on the banner inside
            const banner = container.querySelector('.photobanner');
            if (banner) banner.style.animationPlayState = 'paused';
        }, { passive: true });

        container.addEventListener('touchmove', function (e) {
            if (!isDragging) return;
            const diff = startX - e.touches[0].clientX;
            container.scrollLeft = scrollStart + diff;
        }, { passive: true });

        container.addEventListener('touchend', function () {
            isDragging = false;
            // Don't resume - leave paused after user interacts
        });
    });
});