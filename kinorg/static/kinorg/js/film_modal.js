const modal = document.getElementById('film_modal');
if (modal) {
    const closeBtn = document.getElementById('film_modal_close');
    const modalPoster = document.getElementById('film_modal_poster');
    const modalTitle = document.getElementById('film_modal_title');
    const modalDetailLink = document.getElementById('film_modal_detail_link');
    const modalLists = document.getElementById('film_modal_lists');
    const modalMeta = document.getElementById('film_modal_meta');
    const placeholder = modal.dataset.placeholder;
    const TMDB_BASE = 'https://image.tmdb.org/t/p/';

    function getCsrf() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    let currentFilmId = null;
    let currentPosterPath = null;
    let currentTitle = null;

    function openModal(filmId, title, posterPath, detailUrl, year, director) {
        currentFilmId = filmId;
        currentPosterPath = posterPath;
        currentTitle = title;
        modalTitle.textContent = title;
        modalPoster.src = posterPath ? `${TMDB_BASE}w200${posterPath}` : placeholder;
        modalDetailLink.href = detailUrl;
        modalLists.innerHTML = '';
        const metaParts = [];
        if (year) metaParts.push(year);
        if (director) metaParts.push(director);
        modalMeta.innerHTML = metaParts.map(p => `<span>${p}</span>`).join('');

        fetch(`/film-lists/?film_id=${filmId}`)
            .then(res => res.json())
            .then(data => {
                renderLists(data, filmId);
                modal.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            });
    }

    function renderLists(data, filmId) {
        const all = [...(data.my_lists || []), ...(data.guest_lists || [])];
        if (all.length === 0) {
            modalLists.innerHTML = '<p class="film_modal_no_lists">No lists yet.</p>';
            return;
        }

        modalLists.innerHTML = all.map(lst => `
            <div class="film_modal_list_item">
                <a href="/lists/${lst.sqid}/" class="btn film_modal_list_name">${lst.title}</a>
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
        btn.textContent = '';
        btn.classList.add('btn-loading');

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
                document.dispatchEvent(new CustomEvent('filmListChanged', {
                    detail: { filmId, listId, nowInList, posterPath: currentPosterPath, title: currentTitle }
                }));
            } else {
                btn.classList.remove('btn-loading');
                btn.textContent = inList ? 'Remove' : 'Add';
            }
            btn.disabled = false;
        })
        .catch(() => {
            btn.disabled = false;
            btn.classList.remove('btn-loading');
            btn.textContent = inList ? 'Remove' : 'Add';
        });
    });

    // ===== INLINE CREATE LIST =====
    const newListBtn = document.getElementById('film_modal_new_list_btn');
    const createForm = document.getElementById('film_modal_create_form');
    const titleInput = document.getElementById('film_modal_list_title');
    const createSubmit = document.getElementById('film_modal_create_submit');
    const createError = document.getElementById('film_modal_create_error');

    newListBtn.addEventListener('click', () => {
        newListBtn.style.display = 'none';
        createForm.style.display = 'flex';
        titleInput.value = '';
        createError.textContent = '';
        titleInput.focus();
    });

    createSubmit.addEventListener('click', () => {
        const title = titleInput.value.trim();
        if (!title) return;
        createSubmit.disabled = true;
        const body = new URLSearchParams({ title });
        fetch('/create-list-ajax/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body,
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                createForm.style.display = 'none';
                newListBtn.style.display = '';
                const newItem = document.createElement('div');
                newItem.className = 'film_modal_list_item';
                newItem.innerHTML = `
                    <a href="/lists/${data.sqid}/" class="btn film_modal_list_name">${data.title}</a>
                    <button class="film_modal_toggle_btn add_button"
                            data-list-id="${data.id}"
                            data-film-id="${currentFilmId}"
                            data-in-list="false">Add</button>`;
                modalLists.prepend(newItem);
            } else {
                createError.textContent = data.error || 'Could not create list.';
            }
            createSubmit.disabled = false;
        })
        .catch(() => {
            createError.textContent = 'Something went wrong.';
            createSubmit.disabled = false;
        });
    });

    titleInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') createSubmit.click();
    });

    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = '';
        createForm.style.display = 'none';
        newListBtn.style.display = '';
        createError.textContent = '';
    }

    closeBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    window.addEventListener('pageshow', (e) => {
        if (e.persisted) closeModal();
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
            link.href,
            link.dataset.year,
            link.dataset.director
        );
    });
}
