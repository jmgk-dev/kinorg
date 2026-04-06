// Shared JS for collection pages, PCC schedule, watchlist, and liked/watched pages.
// Handles the collection picker dropdown and load-more pagination.
// Supports ranked collections (with rank badges), PCC screenings (external links),
// and standard film grids.

// Collection picker dropdown — lets users switch between collections
const pickerBtn = document.getElementById('collection_picker_btn');
const pickerDropdown = document.getElementById('collection_picker_dropdown');

if (pickerBtn && pickerDropdown) {
    pickerBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const open = pickerDropdown.classList.toggle('open');
        pickerBtn.setAttribute('aria-expanded', open);
    });

    document.addEventListener('click', () => {
        pickerDropdown.classList.remove('open');
        pickerBtn.setAttribute('aria-expanded', 'false');
    });
}

// Load-more button — fetch next batch of 48 films and append poster cards to the grid
const filmGrid = document.getElementById('film_grid');
const loadMoreBtn = document.getElementById('load_more_btn');

if (loadMoreBtn && filmGrid) {
    const baseUrl = filmGrid.dataset.baseUrl;
    const placeholderUrl = filmGrid.dataset.placeholderUrl;
    const filmUrlTemplate = filmGrid.dataset.filmUrl;
    const filmsUrl = filmGrid.dataset.filmsUrl;
    const isRanked = filmGrid.dataset.isRanked === 'true';
    const isPcc = filmGrid.dataset.isPcc === 'true';

    loadMoreBtn.addEventListener('click', () => {
        const offset = loadMoreBtn.dataset.offset;
        const sort = loadMoreBtn.dataset.sort;
        const country = loadMoreBtn.dataset.country || '';
        const genre = loadMoreBtn.dataset.genre || '';
        const liked = loadMoreBtn.dataset.liked;
        const watched = loadMoreBtn.dataset.watched;

        loadMoreBtn.disabled = true;
        loadMoreBtn.textContent = 'Loading...';

        const params = new URLSearchParams({ offset, sort });
        if (country) params.set('country', country);
        if (genre) params.set('genre', genre);
        if (liked !== undefined) params.set('liked', liked);
        if (watched !== undefined) params.set('watched', watched);

        fetch(`${filmsUrl}?${params}`)
            .then(res => res.json())
            .then(data => {
                data.films.forEach(film => {
                    const posterSrc = film.poster_path && film.poster_path !== 'None'
                        ? `${baseUrl}w200${film.poster_path}`
                        : placeholderUrl;
                    const safeTitle = film.title.replace(/"/g, '&quot;');
                    const rankBadge = (isRanked && film.rank)
                        ? `<span class="rank_badge">${film.rank}</span>`
                        : '';

                    let anchor;
                    if (isPcc && !film.id) {
                        anchor = `<a href="${film.pcc_url}" target="_blank" rel="noopener" title="${safeTitle}">
                            <img class="poster" src="${posterSrc}" alt="${safeTitle}">
                        </a>`;
                    } else {
                        const filmUrl = filmUrlTemplate.replace('/0', '/' + film.id);
                        anchor = `<a class="poster_link" href="${filmUrl}"
                            data-film-id="${film.id}"
                            data-film-title="${safeTitle}"
                            data-poster-path="${film.poster_path}"
                            data-year="${film.year || ''}"
                            data-director="${(film.director || '').replace(/"/g, '&quot;')}"
                            data-media-type="movie">
                            <img class="poster" src="${posterSrc}" alt="${safeTitle}">
                            ${rankBadge}
                        </a>`;
                    }

                    const li = document.createElement('li');
                    li.className = 'results_item collection_result_item';
                    li.innerHTML = anchor;
                    filmGrid.appendChild(li);
                });

                loadMoreBtn.dataset.offset = data.next_offset;

                if (!data.has_more) {
                    loadMoreBtn.closest('.load_more_container').remove();
                } else {
                    loadMoreBtn.disabled = false;
                    loadMoreBtn.textContent = 'Load more';
                }
            });
    });
}
