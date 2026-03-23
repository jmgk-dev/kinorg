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

function ReadMore() {
    var dots = document.getElementById("dots");
    var moreText = document.getElementById("more");
    var btnText = document.getElementById("myBtn");

    if (dots.style.display === "none") {
        dots.style.display = "inline";
        btnText.innerHTML = "Read more";
        moreText.style.display = "none";
    } else {
        dots.style.display = "none";
        btnText.innerHTML = "Read less";
        moreText.style.display = "inline";
    }
}

function openReviewModal() {
    document.getElementById('review-modal').style.display = 'block';
}

function closeReviewModal() {
    document.getElementById('review-modal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('review-modal');
    if (event.target == modal) {
        closeReviewModal();
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const likeBtn = document.querySelector('.like_btn');
    if (likeBtn) {
        likeBtn.addEventListener('click', function () {
            const tmdbId = likeBtn.dataset.tmdbId;
            const title = likeBtn.dataset.title;
            const posterPath = likeBtn.dataset.posterPath;
            const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)[1];
            const formData = new FormData();
            formData.append('title', title);
            formData.append('poster_path', posterPath);
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
