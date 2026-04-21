// Film detail page JS — handles toggle buttons (add/remove from list),
// Log/Rate modal, Videos modal, activity row state, watchlist/watched/like toggles,
// review privacy toggle, and review flagging.

// Submit a form via AJAX and replace a target element with the response HTML (for add/remove buttons)
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

// Open/close the Log, Rate & Review modal
function openLogRateModal() {
    document.getElementById('log-rate-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeLogRateModal() {
    document.getElementById('log-rate-modal').style.display = 'none';
    document.body.style.overflow = '';
}

// Open/close the Videos (trailers) modal
function openVideosModal() {
    document.getElementById('videos-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeVideosModal() {
    document.getElementById('videos-modal').style.display = 'none';
    document.body.style.overflow = '';
}

// Close modals when clicking outside the modal content
window.onclick = function(event) {
    const logRateModal = document.getElementById('log-rate-modal');
    const videosModal = document.getElementById('videos-modal');
    if (event.target === logRateModal) closeLogRateModal();
    if (event.target === videosModal) closeVideosModal();
};

// Close modals on Escape key
document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    const logRateModal = document.getElementById('log-rate-modal');
    const videosModal = document.getElementById('videos-modal');
    if (logRateModal && logRateModal.style.display !== 'none') closeLogRateModal();
    if (videosModal && videosModal.style.display !== 'none') closeVideosModal();
});

// Update the activity row below the film header to reflect current state
// Shows "Log, Rate & Review" when no actions taken, or coloured pills for each action
function updateActivityRow() {
    const row = document.getElementById('activity_row');
    if (!row) return;
    const watched = row.dataset.watched === 'true';
    const liked = row.dataset.liked === 'true';
    const inWatchlist = row.dataset.inWatchlist === 'true';
    const stars = parseInt(row.dataset.stars) || 0;
    const reviewed = row.dataset.reviewed === 'true';

    const anyAction = watched || liked || stars || reviewed || inWatchlist;

    let html;
    if (!anyAction) {
        html = '<span>Log, Rate &amp; Review</span>';
    } else {
        const watchedLabel = watched
            ? '<span class="ar_watched ar_on">Watched</span>'
            : '<span class="ar_watched ar_off">Log</span>';
        const starsLabel = stars
            ? `<span class="ar_stars ar_on">${'★'.repeat(stars)}</span>`
            : '<span class="ar_stars ar_off">Rate</span>';
        const reviewedLabel = reviewed
            ? '<span class="ar_reviewed ar_on">Reviewed</span>'
            : '<span class="ar_reviewed ar_off">Review</span>';
        html = [watchedLabel, starsLabel, reviewedLabel].join('<span class="ar_sep"> · </span>');
    }

    const isLogged = anyAction || inWatchlist;

    [document.getElementById('log_rate_btn'), document.getElementById('log_rate_btn_desktop')]
        .forEach(btn => {
            if (!btn) return;
            btn.innerHTML = html;
            btn.classList.toggle('activity_row_btn--logged', isLogged);
        });
}

document.addEventListener('DOMContentLoaded', function () {

    updateActivityRow();


    // Tab switching (Cast, Crew, Reviews, Similar, Lists)
    document.querySelectorAll('.tab_btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.tab_btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab_panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        });
    });

    // "See more" cards at end of cast/crew scroll — click to reveal all items
    document.querySelectorAll('.see_more_card').forEach(function (card) {
        card.addEventListener('click', function () {
            const list = document.getElementById(card.dataset.target);
            list.classList.add('show-all');
        });
    });

    // Add overflow indicator (fade hint) when cast/similar lists are scrollable
    document.querySelectorAll('.cast_list, .similar_list').forEach(function (list) {
        if (list.scrollWidth > list.clientWidth) {
            list.classList.add('has-overflow');
        }
    });

    // Watchlist toggle button — POST to /watchlist/<id>/, update button state + badge + activity row
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
                    const badge = document.getElementById('watchlist_poster_badge');
                    if (badge) badge.style.display = data.in_watchlist ? '' : 'none';
                    updateActivityRow();
                }
            })
            .catch(() => {});
        });
    }

    // Watched toggle button — POST to /watched/<id>/, update button state + activity row
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
            })
            .catch(() => {});
        });
    }

    // Like toggle button — POST to /like/<id>/, update button state + activity row
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
            })
            .catch(() => {});
        });
    }

    // Remove review button — clears mini_review text only (keeps stars), then reloads page
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

    // Review privacy toggle — iOS-style switch that POSTs to /review-private/
    // Updates the hidden form input so the privacy state is included on form submit too
    const privateCheckbox = document.querySelector('.review_private_checkbox');
    if (privateCheckbox) {
        const privateLabel = privateCheckbox.closest('.review_private_label');

        const reviewVisibleInput = document.getElementById('review_visible_input');

        function updatePrivateLabel(isPrivate) {
            if (privateLabel) privateLabel.classList.toggle('review_private--on', isPrivate);
            if (reviewVisibleInput) reviewVisibleInput.value = isPrivate ? 'false' : 'true';
        }

        // Set initial state
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

    // Flag review buttons — toggle flag on other users' reviews (for moderation)
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

    // Poll for similar films when background task is still computing
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

    // ===== LIST STATUS BUTTON — live update =====
    // The header shows a button indicating how many of the user's lists contain this film.
    // When the film modal adds or removes the film from a list, 'filmListChanged' fires on
    // document (dispatched by film_modal.js). We re-fetch the user's lists and update both
    // the desktop and mobile buttons to reflect the new count without a page reload.
    // The 'hideTop' flag (7th arg to openFilmModal) hides the redundant poster/title section
    // in the modal since we're already on the film's detail page.
    const filmId = document.getElementById('activity_row')?.dataset.tmdbId;
    if (filmId) {
        document.addEventListener('filmListChanged', function (e) {
            // Ignore events for other films (the modal is global, shared across all posters)
            if (String(e.detail.filmId) !== String(filmId)) return;
            fetch(`/film-lists/?film_id=${filmId}`)
                .then(r => r.json())
                .then(data => {
                    const all = [...(data.my_lists || []), ...(data.guest_lists || [])];
                    const count = all.filter(l => l.contains_film).length;
                    const actRow = document.getElementById('activity_row');
                    const openModal = `openFilmModal('${filmId}','${(actRow.dataset.title || '').replace(/'/g,"\\'")}','${actRow.dataset.posterPath}',window.location.pathname,'','',true)`;

                    // Update both desktop and mobile variants of the button
                    ['list_status_btn_desktop', 'list_status_btn_mobile'].forEach(id => {
                        const btn = document.getElementById(id);
                        // Skip if not found or if it's the static <a> "Create a list" link
                        if (!btn || btn.tagName === 'A') return;
                        if (count === 0) {
                            btn.textContent = '+ Add to list';
                            btn.classList.remove('btn-list-status--in');
                        } else {
                            btn.textContent = `In ${count} of your lists`;
                            btn.classList.add('btn-list-status--in');
                        }
                        btn.setAttribute('onclick', openModal);
                    });
                })
                .catch(() => {});
        });
    }

});
