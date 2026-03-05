document.addEventListener('DOMContentLoaded', function () {
    const containers = document.querySelectorAll('#container');
    const DRAG_SPEED = 2;

    containers.forEach(container => {
        let startX = 0;
        let startY = 0;
        let scrollStart = 0;
        let isDragging = false;
        let isHorizontal = null;

        // Infinite scroll: when past halfway, jump back to start
        container.addEventListener('scroll', function () {
            const half = container.scrollWidth / 2;
            if (container.scrollLeft >= half) {
                container.scrollLeft = container.scrollLeft - half;
            } else if (container.scrollLeft <= 0) {
                container.scrollLeft = half;
            }
        });

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

            if (isHorizontal === null) {
                isHorizontal = Math.abs(diffX) > Math.abs(diffY);
            }

            if (isHorizontal) {
                e.preventDefault();
                container.scrollLeft = scrollStart - (diffX * DRAG_SPEED);
            }
        }, { passive: false });

        container.addEventListener('touchend', function () {
            isDragging = false;
            isHorizontal = null;
        });
    });
});