const input = document.getElementById('live_search_input');
const resultsList = document.getElementById('live_search_results');
const baseUrl = resultsList.dataset.baseUrl;
const placeholderUrl = resultsList.dataset.placeholderUrl;

let debounceTimer;
let activeFilter = 'all';

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

function runSearch(query) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        fetch(`/film-autocomplete/?q=${encodeURIComponent(query)}&filter=${activeFilter}`)
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

                    const year = result.year ? `<p>${result.year}</p>` : '';

                    const li = document.createElement('li');
                    li.className = 'search_result_item';
                    li.innerHTML = `
                        <a href="${href}">
                            <img class="search_result_poster" src="${poster}">
                            <div class="search_result_info">
                                <p><b>${result.title}</b></p>
                                ${year}
                            </div>
                        </a>
                    `;
                    resultsList.appendChild(li);
                });
            });
    }, 300);
}

input.addEventListener('input', () => {
    const query = input.value.trim();
    if (query.length < 2) {
        resultsList.innerHTML = '';
        return;
    }
    runSearch(query);
});

if (input.value.trim().length >= 2) {
    runSearch(input.value.trim());
}
