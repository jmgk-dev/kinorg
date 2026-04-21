// Home page poster carousels — auto-scrolling rows of film posters.
// Each carousel contains two copies of the posters for seamless infinite scroll.
// Normal carousels scroll right; reverse carousels scroll left.
// Pauses on hover/touch, resumes on leave.

const SPEED = 60; // scroll speed in pixels per second

document.querySelectorAll('.carousel_container').forEach(container => {
    const inner = container.querySelector('.carousel_inner');
    const isReverse = inner.classList.contains('carousel_reverse');
    let isPaused = false;
    let lastTime = null;

    // Half the scroll width = one full copy of the posters
    function getHalfWidth() {
        return inner.scrollWidth / 2;
    }

    // Set initial scroll position (reverse starts in the middle so it can scroll left)
    function init() {
        container.scrollLeft = isReverse ? getHalfWidth() : 0;
    }

    // Seamless infinite loop: jump back when reaching the end of the first copy
    container.addEventListener('scroll', () => {
        const half = getHalfWidth();
        if (!isReverse && container.scrollLeft >= half) {
            container.scrollLeft -= half;
        } else if (isReverse && container.scrollLeft <= 0) {
            container.scrollLeft = half;
        }
    }, { passive: true });

    // Animation loop — moves scroll position by SPEED pixels/sec using requestAnimationFrame
    function step(timestamp) {
        if (!isPaused && lastTime !== null) {
            const delta = timestamp - lastTime;
            const move = SPEED * delta / 1000;
            container.scrollLeft += isReverse ? -move : move;
        }
        lastTime = isPaused ? null : timestamp;
        requestAnimationFrame(step);
    }

    // Pause on hover/touch so the user can browse
    container.addEventListener('mouseenter', () => isPaused = true);
    container.addEventListener('mouseleave', () => isPaused = false);

    container.addEventListener('touchstart', () => isPaused = true, { passive: true });
    container.addEventListener('touchend', () => {
        // Wait 1s for momentum scroll to settle before resuming auto-scroll
        setTimeout(() => isPaused = false, 1000);
    });

    if (document.readyState === 'complete') {
        init();
    } else {
        window.addEventListener('load', init);
    }

    requestAnimationFrame(step);
});
