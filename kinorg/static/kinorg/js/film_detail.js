function toggleFilm(button) {
    const form = button.closest('form');
    const url = button.getAttribute('data-url');
    const targetId = button.getAttribute('data-target');
    const formData = new FormData(form);

    const originalText = button.innerText;
    button.innerText = '';
    button.classList.add('btn-loading');

    fetch(url, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        const targetDiv = document.getElementById(targetId);
        targetDiv.outerHTML = html;
    })
    .catch(error => {
        console.error('Error:', error);
        button.innerText = originalText;
        button.classList.remove('btn-loading');
        alert('Something went wrong. Please try again.');
    });
}

function openLogRateModal() {
    document.getElementById('log-rate-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeLogRateModal() {
    document.getElementById('log-rate-modal').style.display = 'none';
    document.body.style.overflow = '';
}

function openVideosModal() {
    document.getElementById('videos-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeVideosModal() {
    document.getElementById('videos-modal').style.display = 'none';
    document.body.style.overflow = '';
}

window.onclick = function(event) {
    const logRateModal = document.getElementById('log-rate-modal');
    const videosModal = document.getElementById('videos-modal');
    if (event.target === logRateModal) closeLogRateModal();
    if (event.target === videosModal) closeVideosModal();
};

function getCsrf() {
    return document.cookie.match(/csrftoken=([^;]+)/)[1];
}

function updateActivityRow() {
    const row = document.getElementById('activity_row');
    if (!row) return;
    const watched = row.dataset.watched === 'true';
    const liked = row.dataset.liked === 'true';
    const inWatchlist = row.dataset.inWatchlist === 'true';
    const stars = parseInt(row.dataset.stars) || 0;
    const reviewed = row.dataset.reviewed === 'true';

    const parts = [];
    if (stars) parts.push('★'.repeat(stars));
    if (watched) parts.push('Watched');
    if (liked) parts.push('Liked');
    if (reviewed) parts.push('Reviewed');
    if (inWatchlist && !parts.length) parts.push('+ Watchlist');

    const label = parts.length ? parts.join(' · ') : 'Log, Rate & Review';
    const isLogged = parts.length > 0;

    [document.getElementById('log_rate_btn'), document.getElementById('log_rate_btn_desktop')]
        .forEach(btn => {
            if (!btn) return;
            btn.textContent = label;
            btn.classList.toggle('activity_row_btn--logged', isLogged);
        });
}

document.addEventListener('DOMContentLoaded', function () {

    updateActivityRow();

    // Tabs
    document.querySelectorAll('.tab_btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.tab_btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab_panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        });
    });

    // See more tiles for cast / crew
    document.querySelectorAll('.see_more_card').forEach(function (card) {
        card.addEventListener('click', function () {
            const list = document.getElementById(card.dataset.target);
            list.classList.add('show-all');
        });
    });

    // Overflow indicator for scrollable lists
    document.querySelectorAll('.cast_list, .similar_list').forEach(function (list) {
        if (list.scrollWidth > list.clientWidth) {
            list.classList.add('has-overflow');
        }
    });

    // Watchlist toggle
    const watchlistBtn = document.getElementById('watchlist_toggle_btn');
    if (watchlistBtn) {
        watchlistBtn.addEventListener('click', function () {
            const tmdbId = watchlistBtn.dataset.tmdbId;
            const formData = new FormData();
            formData.append('title', watchlistBtn.dataset.title);
            formData.append('poster_path', watchlistBtn.dataset.posterPath);
            formData.append('release_date', watchlistBtn.dataset.releaseDate || '');
            fetch(`/watchlist/${tmdbId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
                body: formData,
            })
            .then(r => r.json())
            .then(data => {
                if (data.in_watchlist !== undefined) {
                    watchlistBtn.classList.toggle('active', data.in_watchlist);
                    watchlistBtn.dataset.active = data.in_watchlist ? 'true' : 'false';
                    const row = document.getElementById('activity_row');
                    row.dataset.inWatchlist = data.in_watchlist ? 'true' : 'false';
                    updateActivityRow();
                }
            });
        });
    }

    // Watched toggle
    const watchedBtn = document.getElementById('watched_toggle_btn');
    if (watchedBtn) {
        watchedBtn.addEventListener('click', function () {
            const tmdbId = watchedBtn.dataset.tmdbId;
            const formData = new FormData();
            formData.append('title', watchedBtn.dataset.title);
            formData.append('poster_path', watchedBtn.dataset.posterPath);
            formData.append('release_date', watchedBtn.dataset.releaseDate || '');
            fetch(`/watched/${tmdbId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
                body: formData,
            })
            .then(r => r.json())
            .then(data => {
                if (data.watched !== undefined) {
                    watchedBtn.classList.toggle('active', data.watched);
                    watchedBtn.dataset.active = data.watched ? 'true' : 'false';
                    const row = document.getElementById('activity_row');
                    row.dataset.watched = data.watched ? 'true' : 'false';
                    if (!data.watched) row.dataset.stars = '';
                    updateActivityRow();
                }
            });
        });
    }

    // Like toggle
    const likedBtn = document.getElementById('liked_toggle_btn');
    if (likedBtn) {
        likedBtn.addEventListener('click', function () {
            const tmdbId = likedBtn.dataset.tmdbId;
            const formData = new FormData();
            formData.append('title', likedBtn.dataset.title);
            formData.append('poster_path', likedBtn.dataset.posterPath);
            fetch(`/like/${tmdbId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
                body: formData,
            })
            .then(r => r.json())
            .then(data => {
                if (data.liked !== undefined) {
                    likedBtn.classList.toggle('active', data.liked);
                    likedBtn.dataset.active = data.liked ? 'true' : 'false';
                    const row = document.getElementById('activity_row');
                    row.dataset.liked = data.liked ? 'true' : 'false';
                    updateActivityRow();
                }
            });
        });
    }

    // Remove review
    const removeReviewBtn = document.getElementById('remove_review_btn');
    if (removeReviewBtn) {
        removeReviewBtn.addEventListener('click', function () {
            const formData = new FormData();
            formData.append('id', removeReviewBtn.dataset.filmId);
            fetch(removeReviewBtn.dataset.url, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
                body: formData,
            }).then(() => window.location.reload());
        });
    }

    // Hide/show review toggle
    const privateBtn = document.querySelector('.review_private_btn');
    if (privateBtn) {
        privateBtn.addEventListener('click', function () {
            const filmId = privateBtn.dataset.filmId;
            const formData = new FormData();
            formData.append('film_id', filmId);
            fetch('/review-private/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
                body: formData,
            })
            .then(r => r.json())
            .then(data => {
                if (data.review_visible !== undefined) {
                    privateBtn.dataset.visible = data.review_visible ? 'true' : 'false';
                    privateBtn.textContent = data.review_visible ? 'Hide Review' : 'Review Hidden';
                    privateBtn.classList.toggle('review_hidden', !data.review_visible);
                }
            });
        });
    }

    // Flag buttons
    document.querySelectorAll('.flag_btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const reviewId = btn.dataset.reviewId;
            fetch(`/flag-review/${reviewId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
            })
            .then(r => r.json())
            .then(data => {
                if (data.flagged !== undefined) {
                    btn.classList.toggle('flagged', data.flagged);
                    btn.textContent = data.flagged ? '🚩 Flagged' : 'Flag';
                }
            });
        });
    });

});
