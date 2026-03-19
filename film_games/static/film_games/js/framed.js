const container = document.querySelector('.framed_container');
if (!container) throw new Error('Not on framed page');

const guessUrl = container.dataset.guessUrl;
const autocompleteUrl = container.dataset.autocompleteUrl;
const csrfToken = container.dataset.csrf;

const poster = document.getElementById('framed_poster');
const guessList = document.getElementById('framed_guesses');
const input = document.getElementById('framed_input');
const submitBtn = document.getElementById('framed_submit_btn');
const skipBtn = document.getElementById('framed_skip_btn');
const autocompleteResults = document.getElementById('framed_autocomplete_results');
const shareBtn = document.getElementById('framed_share_btn');
const attemptCount = document.querySelector('.framed_attempt_count');

let selectedFilm = null;
let debounceTimer;

// ── Autocomplete ──────────────────────────────────────────────────────────────

if (input) {
    input.addEventListener('input', () => {
        selectedFilm = null;
        submitBtn.disabled = true;
        clearTimeout(debounceTimer);

        const q = input.value.trim();
        if (q.length < 2) {
            autocompleteResults.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`${autocompleteUrl}?q=${encodeURIComponent(q)}`)
                .then(res => res.json())
                .then(data => {
                    autocompleteResults.innerHTML = '';
                    data.results.forEach(film => {
                        const li = document.createElement('li');
                        li.className = 'framed_autocomplete_item';
                        li.textContent = `${film.title} (${film.year})`;
                        li.addEventListener('click', () => {
                            selectedFilm = film;
                            input.value = `${film.title} (${film.year})`;
                            autocompleteResults.innerHTML = '';
                            submitBtn.disabled = false;
                        });
                        autocompleteResults.appendChild(li);
                    });
                });
        }, 250);
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.framed_autocomplete_wrap')) {
            autocompleteResults.innerHTML = '';
        }
    });
}

// ── Submit guess ──────────────────────────────────────────────────────────────

function postGuess(body) {
    if (submitBtn) submitBtn.disabled = true;
    if (skipBtn) skipBtn.disabled = true;

    fetch(guessUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(body),
    })
    .then(res => res.json())
    .then(data => {
        updatePoster(data.blur_filter);
        addGuessRow(body.skip ? { skip: true, title: 'Skipped' } : { correct: data.correct, title: selectedFilm?.title || '' });
        updateAttemptCount(data.attempts);

        if (data.game_over) {
            showGameOver(data);
        } else {
            resetInput();
            if (skipBtn) skipBtn.disabled = false;
        }
    });
}

if (submitBtn) {
    submitBtn.addEventListener('click', () => {
        if (!selectedFilm) return;
        postGuess({ tmdb_id: selectedFilm.tmdb_id });
    });
}

if (skipBtn) {
    skipBtn.addEventListener('click', () => {
        postGuess({ skip: true });
    });
}

// ── DOM helpers ───────────────────────────────────────────────────────────────

function updatePoster(blurFilter) {
    if (poster) poster.style.filter = blurFilter;
}

function addGuessRow(guess) {
    // Remove first empty placeholder
    const empty = guessList.querySelector('.guess_empty');
    if (empty) empty.remove();

    const li = document.createElement('li');
    if (guess.skip) {
        li.className = 'framed_guess_item guess_skip';
        li.textContent = '⬛ Skipped';
    } else if (guess.correct) {
        li.className = 'framed_guess_item guess_correct';
        li.textContent = `🟩 ${guess.title}`;
    } else {
        li.className = 'framed_guess_item guess_wrong';
        li.textContent = `🟥 ${guess.title}`;
    }
    guessList.insertBefore(li, guessList.querySelector('.guess_empty'));
}

function updateAttemptCount(attempts) {
    if (attemptCount) attemptCount.textContent = `${attempts}/6`;
}

function resetInput() {
    if (input) input.value = '';
    if (autocompleteResults) autocompleteResults.innerHTML = '';
    selectedFilm = null;
    if (submitBtn) submitBtn.disabled = true;
}

function showGameOver(data) {
    // Hide input area
    const inputArea = document.querySelector('.framed_input_area');
    if (inputArea) inputArea.remove();

    // Reveal poster fully
    if (poster) poster.style.filter = 'blur(0px)';

    // Show answer
    let answerEl = document.getElementById('framed_answer');
    if (!answerEl && data.answer) {
        answerEl = document.createElement('div');
        answerEl.className = 'framed_answer';
        const icon = data.solved ? '🎉' : '❌';
        answerEl.innerHTML = `<p class="framed_answer_title">${icon} <strong>${data.answer.title}</strong> (${data.answer.year})</p>`;
        document.querySelector('.framed_poster_wrap').after(answerEl);
    }

    // Show share button
    let actionsEl = document.querySelector('.framed_gameover_actions');
    if (!actionsEl) {
        actionsEl = document.createElement('div');
        actionsEl.className = 'framed_gameover_actions';

        const emojiStr = Array.from(guessList.querySelectorAll('li:not(.guess_empty)')).map(li => {
            if (li.classList.contains('guess_correct')) return '🟩';
            if (li.classList.contains('guess_skip')) return '⬛';
            return '🟥';
        }).join('');

        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.id = 'framed_share_btn';
        btn.textContent = 'Share';
        btn.dataset.solved = data.solved;
        btn.dataset.attempts = data.attempts;
        btn.dataset.guesses = emojiStr;
        btn.addEventListener('click', handleShare);
        actionsEl.appendChild(btn);
        container.appendChild(actionsEl);
    }
}

// ── Share ─────────────────────────────────────────────────────────────────────

function handleShare(e) {
    const btn = e.currentTarget;
    const solved = btn.dataset.solved === 'true';
    const attempts = btn.dataset.attempts;
    const guesses = btn.dataset.guesses;
    const result = solved ? `${attempts}/6` : 'X/6';
    const text = `Framed 🎬 ${result}\n${guesses}\n${window.location.origin}/game/framed/`;
    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Share', 2000);
    });
}

if (shareBtn) shareBtn.addEventListener('click', handleShare);
