// Film detail page JS — action tiles (watchlist/watched/like/list), inline star rating,
// review modal, videos modal, and review flagging.

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
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.text())
    .then(html => {
        document.getElementById(targetId).outerHTML = html;
    })
    .catch(() => {
        button.innerText = originalText;
        button.classList.remove('btn-loading');
        alert('Something went wrong. Please try again.');
    });
}

function openReviewModal() {
    // Sync current star value from inline strip into hidden form input
    const starsEl = document.getElementById('action_stars');
    const starsInput = document.getElementById('modal_stars_input');
    if (starsEl && starsInput) {
        starsInput.value = starsEl.dataset.currentStars || '';
    }
    document.getElementById('review-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeReviewModal() {
    document.getElementById('review-modal').style.display = 'none';
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

window.onclick = function (event) {
    const reviewModal = document.getElementById('review-modal');
    const videosModal = document.getElementById('videos-modal');
    if (event.target === reviewModal) closeReviewModal();
    if (event.target === videosModal) closeVideosModal();
};

document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    const reviewModal = document.getElementById('review-modal');
    const videosModal = document.getElementById('videos-modal');
    if (reviewModal && reviewModal.style.display !== 'none') closeReviewModal();
    if (videosModal && videosModal.style.display !== 'none') closeVideosModal();
});

document.addEventListener('DOMContentLoaded', function () {

    // Tab switching
    document.querySelectorAll('.tab_btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.tab_btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab_panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        });
    });

    // "See more" cards at end of cast/crew scroll
    document.querySelectorAll('.see_more_card').forEach(function (card) {
        card.addEventListener('click', function () {
            document.getElementById(card.dataset.target).classList.add('show-all');
        });
    });

    // Overflow indicator for cast/similar lists
    document.querySelectorAll('.cast_list, .similar_list').forEach(function (list) {
        if (list.scrollWidth > list.clientWidth) {
            list.classList.add('has-overflow');
        }
    });

    // ===== WATCHLIST TILE =====
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
                    const badge = document.getElementById('watchlist_poster_badge');
                    if (badge) badge.style.display = data.in_watchlist ? '' : 'none';
                }
            })
            .catch(() => {});
        });
    }

    // ===== WATCHED TILE =====
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
                    if (!data.watched) {
                        // Clear stars when unwatching
                        setInlineStars(0);
                    }
                }
            })
            .catch(() => {});
        });
    }

    // ===== LIKE TILE =====
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
                }
            })
            .catch(() => {});
        });
    }

    // ===== INLINE STAR RATING =====
    const starsEl = document.getElementById('action_stars');

    function setInlineStars(value) {
        if (!starsEl) return;
        starsEl.dataset.currentStars = value;
        starsEl.querySelectorAll('.action_star').forEach(s => {
            s.classList.toggle('filled', parseInt(s.dataset.value) <= value);
        });
    }

    if (starsEl) {
        const stars = starsEl.querySelectorAll('.action_star');

        stars.forEach(star => {
            star.addEventListener('mouseenter', function () {
                const val = parseInt(star.dataset.value);
                stars.forEach(s => s.classList.toggle('hover', parseInt(s.dataset.value) <= val));
            });
            star.addEventListener('mouseleave', function () {
                stars.forEach(s => s.classList.remove('hover'));
            });
            star.addEventListener('click', function () {
                const val = parseInt(star.dataset.value);
                const current = parseInt(starsEl.dataset.currentStars) || 0;
                const newVal = val === current ? 0 : val;
                const tmdbId = document.getElementById('action_strip_data').dataset.tmdbId;
                const data = document.getElementById('action_strip_data').dataset;
                const formData = new FormData();
                formData.append('stars', newVal || '');
                formData.append('title', data.title);
                formData.append('poster_path', data.posterPath);
                formData.append('release_date', data.releaseDate || '');
                fetch(`/set-stars/${tmdbId}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCsrf() },
                    body: formData,
                })
                .then(r => r.json())
                .then(result => {
                    setInlineStars(result.stars || 0);
                })
                .catch(() => {});
            });
        });
    }

    // ===== REMOVE REVIEW =====
    const removeReviewBtn = document.getElementById('remove_review_btn');
    if (removeReviewBtn) {
        removeReviewBtn.addEventListener('click', function () {
            const formData = new FormData();
            formData.append('id', removeReviewBtn.dataset.filmId);
            fetch(removeReviewBtn.dataset.url, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
                body: formData,
            })
            .then(() => window.location.reload())
            .catch(() => window.location.reload());
        });
    }

    // ===== REVIEW PRIVACY TOGGLE =====
    const privateCheckbox = document.querySelector('.review_private_checkbox');
    if (privateCheckbox) {
        const privateLabel = privateCheckbox.closest('.review_private_label');
        const reviewVisibleInput = document.getElementById('review_visible_input');

        function updatePrivateLabel(isPrivate) {
            if (privateLabel) privateLabel.classList.toggle('review_private--on', isPrivate);
            if (reviewVisibleInput) reviewVisibleInput.value = isPrivate ? 'false' : 'true';
        }

        updatePrivateLabel(privateCheckbox.checked);

        privateCheckbox.addEventListener('change', function () {
            const filmId = privateCheckbox.dataset.filmId;
            const formData = new FormData();
            formData.append('film_id', filmId);
            formData.append('review_visible', privateCheckbox.checked ? 'false' : 'true');
            fetch('/review-private/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
                body: formData,
            })
            .then(r => r.json())
            .then(data => {
                if (data.review_visible !== undefined) {
                    privateCheckbox.checked = !data.review_visible;
                    updatePrivateLabel(!data.review_visible);
                }
            })
            .catch(() => {});
        });
    }

    // ===== FLAG REVIEW BUTTONS =====
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
            })
            .catch(() => {});
        });
    });

    // ===== SIMILAR FILMS POLLING =====
    const similarList = document.getElementById('similar-films-list');
    if (similarList && similarList.dataset.pending) {
        const filmId = similarList.dataset.pending;
        const placeholder = similarList.dataset.placeholder;
        const TMDB_BASE = 'https://image.tmdb.org/t/p/w185';
        let attempts = 0;

        const poll = setInterval(() => {
            if (++attempts > 20) {
                clearInterval(poll);
                similarList.outerHTML = '<p>No similar films found.</p>';
                return;
            }
            fetch(`/film-detail/${filmId}/similar/`)
                .then(r => r.json())
                .then(data => {
                    if (!data.ready) return;
                    clearInterval(poll);
                    if (!data.films.length) {
                        similarList.outerHTML = '<p>No similar films found.</p>';
                        return;
                    }
                    similarList.innerHTML = data.films.map(f => `
                        <li class="similar_item">
                            <a href="/film-detail/${f.id}">
                                <img class="cast_photo"
                                     src="${f.poster_path ? TMDB_BASE + f.poster_path : placeholder}"
                                     alt="${f.title}">
                            </a>
                            <p><a href="/film-detail/${f.id}">${f.title}</a></p>
                        </li>
                    `).join('');
                })
                .catch(() => {});
        }, 2000);
    }

    // ===== LIST STATUS TILE — live update via filmListChanged =====
    const filmId = document.getElementById('action_strip_data')?.dataset.tmdbId;
    if (filmId) {
        document.addEventListener('filmListChanged', function (e) {
            if (String(e.detail.filmId) !== String(filmId)) return;
            fetch(`/film-lists/?film_id=${filmId}`)
                .then(r => r.json())
                .then(data => {
                    const all = [...(data.my_lists || []), ...(data.guest_lists || [])];
                    const count = all.filter(l => l.contains_film).length;
                    const tile = document.getElementById('list_status_tile');
                    if (!tile) return;
                    const sd = document.getElementById('action_strip_data');
                    const openModal = `openFilmModal('${filmId}','${(sd.dataset.title || '').replace(/'/g,"\\'")}','${sd.dataset.posterPath}',window.location.pathname,'','',true)`;

                    if (count === 0) {
                        tile.classList.remove('active');
                        tile.querySelector('.action_tile_label').textContent = 'Add to list';
                    } else {
                        tile.classList.add('active');
                        tile.querySelector('.action_tile_label').textContent = `${count} list${count === 1 ? '' : 's'}`;
                    }
                    tile.setAttribute('onclick', openModal);
                })
                .catch(() => {});
        });
    }

});
