const modal = document.getElementById('film_modal');
if (modal) {
    const closeBtn = document.getElementById('film_modal_close');
    const modalPoster = document.getElementById('film_modal_poster');
    const modalTitle = document.getElementById('film_modal_title');
    const modalDetailLink = document.getElementById('film_modal_detail_link');
    const modalLists = document.getElementById('film_modal_lists');
    const placeholder = modal.dataset.placeholder;
    const TMDB_BASE = 'https://image.tmdb.org/t/p/';

    function getCsrf() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    function openModal(filmId, title, posterPath, detailUrl) {
        modalTitle.textContent = title;
        modalPoster.src = posterPath ? `${TMDB_BASE}w200${posterPath}` : placeholder;
        modalDetailLink.href = detailUrl;
        modalLists.innerHTML = '<p>Loading...</p>';
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        fetch(`/film-lists/?film_id=${filmId}`)
            .then(res => res.json())
            .then(data => renderLists(data, filmId));
    }

    function renderLists(data, filmId) {
        const all = [...(data.my_lists || []), ...(data.guest_lists || [])];
        if (all.length === 0) {
            modalLists.innerHTML = '<p class="film_modal_no_lists">No lists yet.</p>';
            return;
        }

        modalLists.innerHTML = all.map(lst => `
            <div class="film_modal_list_item">
                <a href="/lists/${lst.sqid}/" class="link film_modal_list_name">${lst.title}</a>
                <button class="film_modal_toggle_btn ${lst.contains_film ? 'remove_button' : 'add_button'}"
                        data-list-id="${lst.id}"
                        data-film-id="${filmId}"
                        data-in-list="${lst.contains_film}">
                    ${lst.contains_film ? 'Remove' : 'Add'}
                </button>
            </div>
        `).join('');
    }

    modalLists.addEventListener('click', (e) => {
        const btn = e.target.closest('.film_modal_toggle_btn');
        if (!btn) return;

        const listId = btn.dataset.listId;
        const filmId = btn.dataset.filmId;
        const inList = btn.dataset.inList === 'true';

        btn.disabled = true;
        btn.textContent = '...';

        const url = inList ? '/remove-film-ajax/' : '/add-film-by-id/';
        const body = new URLSearchParams({ list_id: listId, film_id: filmId });

        fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body,
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const nowInList = !inList;
                btn.dataset.inList = nowInList;
                btn.className = `film_modal_toggle_btn ${nowInList ? 'remove_button' : 'add_button'}`;
                btn.textContent = nowInList ? 'Remove' : 'Add';
            }
            btn.disabled = false;
        })
        .catch(() => {
            btn.disabled = false;
            btn.textContent = inList ? 'Remove' : 'Add';
        });
    });

    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }

    closeBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    document.addEventListener('click', (e) => {
        const link = e.target.closest('.poster_link');
        if (!link) return;
        if (link.dataset.mediaType === 'person') return;

        e.preventDefault();
        openModal(
            link.dataset.filmId,
            link.dataset.filmTitle,
            link.dataset.posterPath,
            link.href
        );
    });
}
