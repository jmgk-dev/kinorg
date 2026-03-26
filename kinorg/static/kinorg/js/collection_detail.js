const filmGrid = document.getElementById('film_grid');
const loadMoreBtn = document.getElementById('load_more_btn');

if (loadMoreBtn && filmGrid) {
    const baseUrl = filmGrid.dataset.baseUrl;
    const placeholderUrl = filmGrid.dataset.placeholderUrl;
    const filmUrlTemplate = filmGrid.dataset.filmUrl;
    const filmsUrl = filmGrid.dataset.filmsUrl;
    const isRanked = filmGrid.dataset.isRanked === 'true';

    loadMoreBtn.addEventListener('click', () => {
        const offset = loadMoreBtn.dataset.offset;
        const sort = loadMoreBtn.dataset.sort;

        loadMoreBtn.disabled = true;
        loadMoreBtn.textContent = 'Loading...';

        fetch(`${filmsUrl}?offset=${offset}&sort=${encodeURIComponent(sort)}`)
            .then(res => res.json())
            .then(data => {
                data.films.forEach(film => {
                    const filmUrl = filmUrlTemplate.replace('/0', '/' + film.id);
                    const posterSrc = film.poster_path && film.poster_path !== 'None'
                        ? `${baseUrl}w200${film.poster_path}`
                        : placeholderUrl;
                    const rankBadge = (isRanked && film.rank)
                        ? `<span class="rank_badge">${film.rank}</span>`
                        : '';
                    const li = document.createElement('li');
                    li.className = 'results_item collection_result_item';
                    li.innerHTML = `<a class="poster_link" href="${filmUrl}"
                        data-film-id="${film.id}"
                        data-film-title="${film.title.replace(/"/g, '&quot;')}"
                        data-poster-path="${film.poster_path}"
                        data-media-type="movie">
                        <img class="poster" src="${posterSrc}" alt="${film.title.replace(/"/g, '&quot;')}">
                        ${rankBadge}
                    </a>`;
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
