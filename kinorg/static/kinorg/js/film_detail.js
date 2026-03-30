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

function openReviewModal() {
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

window.onclick = function(event) {
    const reviewModal = document.getElementById('review-modal');
    const videosModal = document.getElementById('videos-modal');
    if (event.target === reviewModal) closeReviewModal();
    if (event.target === videosModal) closeVideosModal();
};

// Review form: require at least stars OR text
const reviewForm = document.querySelector('#review-modal form');
if (reviewForm) {
    reviewForm.addEventListener('submit', function (e) {
        const stars = reviewForm.querySelector('input[name="stars"]:checked');
        const text = reviewForm.querySelector('textarea[name="mini_review"]').value.trim();
        const hasStars = stars && stars.value !== '';
        if (!hasStars && !text) {
            e.preventDefault();
            alert('Please add a star rating or write something.');
        }
    });
}

document.addEventListener('DOMContentLoaded', function () {

    // Tabs
    document.querySelectorAll('.tab_btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.tab_btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab_panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        });
    });

    // Like buttons (desktop + mobile kept in sync)
    const likeBtns = document.querySelectorAll('.like_btn');
    likeBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const tmdbId = btn.dataset.tmdbId;
            const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)[1];
            const formData = new FormData();
            formData.append('title', btn.dataset.title);
            formData.append('poster_path', btn.dataset.posterPath);
            fetch(`/like/${tmdbId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: formData,
            })
            .then(r => r.json())
            .then(data => {
                if (data.liked !== undefined) {
                    likeBtns.forEach(function (b) {
                        b.classList.toggle('liked', data.liked);
                        b.textContent = data.liked ? '♥' : '♡';
                        b.title = data.liked ? 'Unlike this film' : 'Like this film';
                    });
                }
            });
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

    // Watched buttons (desktop + mobile kept in sync)
    const watchedBtns = document.querySelectorAll('.watched_btn');
    watchedBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const tmdbId = btn.dataset.tmdbId;
            const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)[1];
            const formData = new FormData();
            formData.append('title', btn.dataset.title);
            formData.append('poster_path', btn.dataset.posterPath);
            formData.append('release_date', btn.dataset.releaseDate || '');
            fetch(`/watched/${tmdbId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: formData,
            })
            .then(r => r.json())
            .then(data => {
                if (data.watched !== undefined) {
                    watchedBtns.forEach(function (b) {
                        b.classList.toggle('is-watched', data.watched);
                        b.title = data.watched ? 'Unwatch' : 'Mark as watched';
                    });
                }
            });
        });
    });

    // Private/public toggle for reviews
    const privateBtn = document.querySelector('.review_private_btn');
    if (privateBtn) {
        privateBtn.addEventListener('click', function () {
            const filmId = privateBtn.dataset.filmId;
            const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)[1];
            const formData = new FormData();
            formData.append('film_id', filmId);
            fetch('/review-private/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: formData,
            })
            .then(r => r.json())
            .then(data => {
                if (data.review_visible !== undefined) {
                    privateBtn.dataset.visible = data.review_visible ? 'true' : 'false';
                    privateBtn.textContent = data.review_visible ? 'Make Private' : 'Make Public';
                    const note = document.querySelector('.review_private_note');
                    if (note) note.style.display = data.review_visible ? 'none' : 'block';
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
                headers: {
                    'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)[1],
                },
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
