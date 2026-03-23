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
    document.getElementById('review-modal').style.display = 'block';
}

function closeReviewModal() {
    document.getElementById('review-modal').style.display = 'none';
}

function openVideosModal() {
    document.getElementById('videos-modal').style.display = 'block';
}

function closeVideosModal() {
    document.getElementById('videos-modal').style.display = 'none';
}

window.onclick = function(event) {
    const reviewModal = document.getElementById('review-modal');
    const videosModal = document.getElementById('videos-modal');
    if (event.target === reviewModal) closeReviewModal();
    if (event.target === videosModal) closeVideosModal();
};

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

    // Like button
    const likeBtn = document.querySelector('.like_btn');
    if (likeBtn) {
        likeBtn.addEventListener('click', function () {
            const tmdbId = likeBtn.dataset.tmdbId;
            const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)[1];
            const formData = new FormData();
            formData.append('title', likeBtn.dataset.title);
            formData.append('poster_path', likeBtn.dataset.posterPath);
            fetch(`/like/${tmdbId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: formData,
            })
            .then(r => r.json())
            .then(data => {
                if (data.liked !== undefined) {
                    likeBtn.classList.toggle('liked', data.liked);
                    likeBtn.textContent = data.liked ? '♥' : '♡';
                    likeBtn.title = data.liked ? 'Unlike this film' : 'Like this film';
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
