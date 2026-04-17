// Typeahead dropdowns used on pages with inline search fields (e.g. list detail page).
// Two independent typeaheads: one for film search, one for user invite search.

// ---- Film search typeahead — search TMDB and navigate to film detail on click ----

const filmInput = document.getElementById('film-search-input');
const filmDropdown = document.getElementById('film-search-dropdown');

let filmDebounce;

if (filmInput && filmDropdown) {

    filmInput.addEventListener('input', function () {
        clearTimeout(filmDebounce);
        const query = this.value.trim();

        if (query.length < 2) {
            filmDropdown.innerHTML = '';
            filmDropdown.hidden = true;
            return;
        }

        filmDebounce = setTimeout(() => {
            fetch(`/film-autocomplete/?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                filmDropdown.innerHTML = '';

                if (data.results.length === 0) {
                    filmDropdown.hidden = true;
                    return;
                }

                data.results.forEach(film => {
                    const item = document.createElement('div');
                    item.className = 'typeahead-item';
                    item.textContent = film.year ? `${film.title} (${film.year})` : film.title;
                    item.addEventListener('click', () => {
                        window.location.href = `/film-detail/${film.id}`;
                    });
                    filmDropdown.appendChild(item);
                });

                filmDropdown.hidden = false;
            })
            .catch(() => {
                filmDropdown.innerHTML = '';
                filmDropdown.hidden = true;
            });
        }, 300);
    });

    document.addEventListener('click', function (e) {
        if (!filmInput.contains(e.target) && !filmDropdown.contains(e.target)) {
            filmDropdown.hidden = true;
        }
    });
}


// ---- User invite typeahead — search usernames and fill the input on click ----

const userInput = document.getElementById('user-invite-input');
const userDropdown = document.getElementById('user-invite-dropdown');

let userDebounce;

if (userInput && userDropdown) {

    userInput.addEventListener('input', function () {
        clearTimeout(userDebounce);
        const query = this.value.trim();

        if (query.length < 2) {
            userDropdown.innerHTML = '';
            userDropdown.hidden = true;
            return;
        }

        userDebounce = setTimeout(() => {
            fetch(`/user-autocomplete/?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                userDropdown.innerHTML = '';

                if (data.results.length === 0) {
                    userDropdown.hidden = true;
                    return;
                }

                data.results.forEach(user => {
                    const item = document.createElement('div');
                    item.className = 'typeahead-item';
                    item.textContent = user.username;
                    item.addEventListener('click', () => {
                        userInput.value = user.username;
                        userDropdown.innerHTML = '';
                        userDropdown.hidden = true;
                    });
                    userDropdown.appendChild(item);
                });

                userDropdown.hidden = false;
            })
            .catch(() => {
                userDropdown.innerHTML = '';
                userDropdown.hidden = true;
            });
        }, 300);
    });

    document.addEventListener('click', function (e) {
        if (!userInput.contains(e.target) && !userDropdown.contains(e.target)) {
            userDropdown.hidden = true;
        }
    });
}