document.addEventListener('DOMContentLoaded', function () {
    const containers = document.querySelectorAll('#container');
    const DRAG_SPEED = 2;

    containers.forEach(container => {
        let startX = 0;
        let startY = 0;
        let scrollStart = 0;
        let isDragging = false;
        let isHorizontal = null;
        let isJumping = false;
        let userHasTouched = false;

        // Infinite scroll loop - only active after user touches
        container.addEventListener('scroll', function () {
            if (!userHasTouched || isJumping) return;

            const half = container.scrollWidth / 2;

            if (container.scrollLeft >= half) {
                isJumping = true;
                container.scrollLeft = container.scrollLeft - half;
                isJumping = false;
            } else if (container.scrollLeft <= 0) {
                isJumping = true;
                container.scrollLeft = half;
                isJumping = false;
            }
        });

        container.addEventListener('touchstart', function (e) {
            if (!userHasTouched) {
                // First touch: switch from CSS animation to JS scroll
                userHasTouched = true;
                const banner = container.querySelector('.photobanner');
                if (banner) {
                    // Capture current visual position of the banner
                    const currentTransform = window.getComputedStyle(banner).transform;
                    const matrix = new DOMMatrix(currentTransform);
                    const currentX = matrix.m41;

                    // Freeze animation
                    banner.style.animationPlayState = 'paused';

                    // Switch container to scrollable
                    container.style.overflow = 'hidden'; // briefly
                    container.style.overflowX = 'scroll';

                    // Set scrollLeft to match where the animation had got to
                    // currentX is negative (translateX moves left), so negate it
                    container.scrollLeft = Math.abs(currentX);
                }
            }

            isDragging = true;
            isHorizontal = null;
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            scrollStart = container.scrollLeft;
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