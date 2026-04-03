const container = document.querySelector('.hl_container');
const pairUrl = container.dataset.pairUrl;
const answerUrl = container.dataset.answerUrl;
const baseUrl = container.dataset.baseUrl;
const placeholderUrl = container.dataset.placeholderUrl;
const csrfToken = container.dataset.csrf;

const cardA = document.getElementById('hl_card_a');
const cardB = document.getElementById('hl_card_b');
const posterA = document.getElementById('hl_poster_a');
const posterB = document.getElementById('hl_poster_b');
const titleA = document.getElementById('hl_title_a');
const titleB = document.getElementById('hl_title_b');
const yearA = document.getElementById('hl_year_a');
const yearB = document.getElementById('hl_year_b');
const scoreEl = document.getElementById('hl_score');
const resultEl = document.getElementById('hl_result');
const gameoverEl = document.getElementById('hl_gameover');
const finalScoreEl = document.getElementById('hl_final_score');
const shareBtn = document.getElementById('hl_share_btn');
const playAgainBtn = document.getElementById('hl_play_again_btn');

let currentFilmA = null;
let currentFilmB = null;
let score = 0;
let accepting = false;

function posterSrc(path) {
    return path && path !== 'None' ? `${baseUrl}w342${path}` : placeholderUrl;
}

function showPair(filmA, filmB) {
    currentFilmA = filmA;
    currentFilmB = filmB;
    accepting = true;

    posterA.src = posterSrc(filmA.poster_path);
    posterA.alt = filmA.title;
    titleA.textContent = filmA.title;
    yearA.textContent = '';

    posterB.src = posterSrc(filmB.poster_path);
    posterB.alt = filmB.title;
    titleB.textContent = filmB.title;
    yearB.textContent = '';

    cardA.classList.remove('correct', 'wrong');
    cardB.classList.remove('correct', 'wrong');
    resultEl.textContent = '';
    resultEl.className = 'hl_result';
}

function fetchPair() {
    // Clear highlights immediately, before the network response
    cardA.classList.remove('correct', 'wrong');
    cardB.classList.remove('correct', 'wrong');
    resultEl.textContent = '';
    resultEl.className = 'hl_result';

    fetch(pairUrl)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                resultEl.textContent = data.error;
                return;
            }
            showPair(data.film_a, data.film_b);
        });
}

function submitAnswer(chosenId) {
    if (!accepting) return;
    accepting = false;

    fetch(answerUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
            film_a_id: currentFilmA.tmdb_id,
            film_b_id: currentFilmB.tmdb_id,
            chosen_id: chosenId,
        }),
    })
    .then(res => res.json())
    .then(data => {
        yearA.textContent = data.film_a_year;
        yearB.textContent = data.film_b_year;

        const chosenCard = String(chosenId) === String(currentFilmA.tmdb_id) ? cardA : cardB;
        const otherCard = chosenCard === cardA ? cardB : cardA;

        if (data.correct) {
            chosenCard.classList.add('correct');
            score = data.score;
            scoreEl.textContent = score;
            resultEl.textContent = '✓ Correct!';
            resultEl.className = 'hl_result hl_correct';
            setTimeout(fetchPair, 1000);
        } else {
            chosenCard.classList.add('wrong');
            otherCard.classList.add('correct');
            score = data.score;
            resultEl.textContent = '✗ Wrong!';
            resultEl.className = 'hl_result hl_wrong';
            setTimeout(showGameOver, 1200);
        }
    });
}

function showGameOver() {
    document.getElementById('hl_cards').style.display = 'none';
    resultEl.style.display = 'none';
    finalScoreEl.textContent = score;
    gameoverEl.style.display = 'flex';
}

function startGame() {
    score = 0;
    scoreEl.textContent = 0;
    gameoverEl.style.display = 'none';
    document.getElementById('hl_cards').style.display = 'flex';
    resultEl.style.display = '';
    fetchPair();
}

cardA.addEventListener('click', () => submitAnswer(currentFilmA?.tmdb_id));
cardB.addEventListener('click', () => submitAnswer(currentFilmB?.tmdb_id));

playAgainBtn.addEventListener('click', startGame);

shareBtn.addEventListener('click', () => {
    const text = `I got ${score} in a row on Kinorg Higher or Lower! 🎬\n${window.location.origin}/game/higher-lower/`;
    navigator.clipboard.writeText(text).then(() => {
        shareBtn.textContent = 'Copied!';
        setTimeout(() => shareBtn.textContent = 'Share', 2000);
    });
});

startGame();
