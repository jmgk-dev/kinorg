const SPEED = 30; // pixels per second

document.querySelectorAll('.carousel_container').forEach(container => {
    const inner = container.querySelector('.carousel_inner');
    const isReverse = inner.classList.contains('carousel_reverse');
    let isPaused = false;
    let lastTime = null;

    function getHalfWidth() {
        return inner.scrollWidth / 2;
    }

    function init() {
        // Reverse carousels start at the midpoint so they can scroll left
        container.scrollLeft = isReverse ? getHalfWidth() : 0;
    }

    // Seamless wrap: when scroll reaches the end of the first copy, jump back
    container.addEventListener('scroll', () => {
        const half = getHalfWidth();
        if (!isReverse && container.scrollLeft >= half) {
            container.scrollLeft -= half;
        } else if (isReverse && container.scrollLeft <= 0) {
            container.scrollLeft = half;
        }
    }, { passive: true });

    function step(timestamp) {
        if (!isPaused && lastTime !== null) {
            const delta = timestamp - lastTime;
            const move = SPEED * delta / 1000;
            container.scrollLeft += isReverse ? -move : move;
        }
        lastTime = isPaused ? null : timestamp;
        requestAnimationFrame(step);
    }

    container.addEventListener('mouseenter', () => isPaused = true);
    container.addEventListener('mouseleave', () => isPaused = false);

    container.addEventListener('touchstart', () => isPaused = true, { passive: true });
    container.addEventListener('touchend', () => {
        // Wait for momentum scroll to settle before resuming
        setTimeout(() => isPaused = false, 1000);
    });

    if (document.readyState === 'complete') {
        init();
    } else {
        window.addEventListener('load', init);
    }

    requestAnimationFrame(step);
});
