// Live search page — fetches results from /film-autocomplete/ as the user types,
// renders film and person results with posters, metadata, and links.
// Shows collection browse links when search is empty, hides them during search.

const input = document.getElementById('live_search_input');
const resultsList = document.getElementById('live_search_results');
const collectionsBrowse = document.getElementById('collections_browse');
const genreChipsWrap = document.getElementById('genre_chips_wrap');
const baseUrl = resultsList.dataset.baseUrl;        // TMDB image base URL
const placeholderUrl = resultsList.dataset.placeholderUrl; // fallback poster image

function showCollections() {
    if (collectionsBrowse) collectionsBrowse.style.display = '';
    if (genreChipsWrap) genreChipsWrap.style.display = '';
}

function hideCollections() {
    if (collectionsBrowse) collectionsBrowse.style.display = 'none';
    if (genreChipsWrap) genreChipsWrap.style.display = 'none';
}

let debounceTimer;
let activeFilter = 'all';   // 'all', 'films', or 'people'
let currentController = null; // AbortController for in-flight requests

// Filter buttons (All / Films / People) — re-run search when filter changes
document.querySelectorAll('.filter_btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter_btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeFilter = btn.dataset.filter;
        if (input.value.trim().length >= 2) {
            runSearch(input.value.trim());
        }
    });
});

// Fetch search results after a 300ms debounce, cancelling any in-flight request
function runSearch(query) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        if (currentController) currentController.abort();
        currentController = new AbortController();
        fetch(`/film-autocomplete/?q=${encodeURIComponent(query)}&filter=${activeFilter}`, { signal: currentController.signal })
            .then(res => res.json())
            .then(data => {
                resultsList.innerHTML = '';
                data.results.forEach(result => {
                    const poster = result.poster_path
                        ? `${baseUrl}w92${result.poster_path}`
                        : result.profile_path
                            ? `${baseUrl}w92${result.profile_path}`
                            : placeholderUrl;

                    const href = result.media_type === 'person'
                        ? `/person-credits/${result.id}`
                        : `/film-detail/${result.id}`;

                    const isFilm = result.media_type === 'movie';
                    const posterAttr = isFilm
                        ? `class="poster_link" data-film-id="${result.id}" data-film-title="${result.title.replace(/"/g, '&quot;')}" data-poster-path="${result.poster_path}" data-media-type="movie"`
                        : '';

                    let meta = '';
                    if (isFilm) {
                        const parts = [result.year, result.country].filter(Boolean);
                        if (parts.length) meta = `<p class="search_result_meta">${parts.join(' · ')}</p>`;
                    } else {
                        if (result.known_for_department) {
                            meta += `<p class="search_result_meta">${result.known_for_department}</p>`;
                        }
                        if (result.known_for_titles && result.known_for_titles.length) {
                            meta += `<p class="search_result_known_for">${result.known_for_titles.join(', ')}</p>`;
                        }
                    }

                    const li = document.createElement('li');
                    li.className = 'search_result_item';
                    li.innerHTML = `
                        <a href="${href}" ${posterAttr}>
                            <img class="search_result_poster" src="${poster}">
                            <div class="search_result_info">
                                <p><b>${result.title}</b></p>
                                ${meta}
                            </div>
                        </a>
                    `;
                    resultsList.appendChild(li);
                });
            })
            .catch(err => { if (err.name !== 'AbortError') console.error(err); });
    }, 300);
}

// Trigger search on each keystroke (debounced), clear results if query is too short
input.addEventListener('input', () => {
    const query = input.value.trim();
    if (query.length < 2) {
        clearTimeout(debounceTimer);
        if (currentController) { currentController.abort(); currentController = null; }
        resultsList.innerHTML = '';
        showCollections();
        return;
    }
    hideCollections();
    runSearch(query);
});

// If the page loads with a pre-filled query (e.g. from URL params), run search immediately
if (input.value.trim().length >= 2) {
    hideCollections();
    runSearch(input.value.trim());
}
