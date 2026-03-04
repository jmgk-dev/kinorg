document.addEventListener('DOMContentLoaded', function () {
    const containers = document.querySelectorAll('#container');

    containers.forEach(container => {
        let startX = 0;
        let startY = 0;
        let scrollStart = 0;
        let isDragging = false;
        let isHorizontal = null;

        container.addEventListener('touchstart', function (e) {
            isDragging = true;
            isHorizontal = null;
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            scrollStart = container.scrollLeft;

            const banner = container.querySelector('.photobanner');
            if (banner) banner.style.animationPlayState = 'paused';
        }, { passive: true });

        container.addEventListener('touchmove', function (e) {
            if (!isDragging) return;

            const diffX = e.touches[0].clientX - startX;
            const diffY = e.touches[0].clientY - startY;

            // Determine direction on first move
            if (isHorizontal === null) {
                isHorizontal = Math.abs(diffX) > Math.abs(diffY);
            }

            if (isHorizontal) {
                e.preventDefault(); // Block vertical scroll only when swiping horizontally
                container.scrollLeft = scrollStart - diffX;
            }
        }, { passive: false }); // Must be false to allow preventDefault

        container.addEventListener('touchend', function () {
            isDragging = false;
            isHorizontal = null;
        });
    });
});