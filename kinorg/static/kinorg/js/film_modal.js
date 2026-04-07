// Film modal — appears when clicking any poster. Shows film title/year/poster,
// the user's lists with add/remove buttons, and an inline create-list form.
// Dispatches 'filmListChanged' events so other pages can update in real time.

const modal = document.getElementById('film_modal');
if (modal) {
    const closeBtn = document.getElementById('film_modal_close');
    const modalPoster = document.getElementById('film_modal_poster');
    const modalTitle = document.getElementById('film_modal_title');
    const modalDetailLink = document.getElementById('film_modal_detail_link');
    const modalLists = document.getElementById('film_modal_lists');
    const modalListsWrap = document.getElementById('film_modal_lists_wrap');
    const modalMeta = document.getElementById('film_modal_meta');

    function updateScrollFade() {
        const atBottom = modalLists.scrollHeight - modalLists.scrollTop <= modalLists.clientHeight + 2;
        modalListsWrap.classList.toggle('scrolled-to-bottom', atBottom);
    }

    modalLists.addEventListener('scroll', updateScrollFade, { passive: true });
    const placeholder = modal.dataset.placeholder;
    const TMDB_BASE = 'https://image.tmdb.org/t/p/';

    function getCsrf() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    let currentFilmId = null;
    let currentPosterPath = null;
    let currentTitle = null;

    function skeletonHTML(n) {
        return Array.from({length: n}, () => `
            <div class="film_modal_skeleton_item">
                <div class="skeleton film_modal_skeleton_name"></div>
                <div class="skeleton film_modal_skeleton_btn"></div>
            </div>
        `).join('');
    }

    // Open modal: show immediately with skeleton placeholders, then populate lists when fetch resolves
    function openModal(filmId, title, posterPath, detailUrl, year) {
        currentFilmId = filmId;
        currentPosterPath = posterPath;
        currentTitle = title;
        modalTitle.textContent = title;
        modalPoster.src = posterPath ? `${TMDB_BASE}w200${posterPath}` : placeholder;
        modalDetailLink.href = detailUrl;
        modalMeta.innerHTML = year ? `<span>${year}</span>` : '';
        modalLists.innerHTML = skeletonHTML(3);

        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        fetch(`/film-lists/?film_id=${filmId}`)
            .then(res => res.json())
            .then(data => {
                renderLists(data, filmId);
                updateScrollFade();
            });
    }

    // Render the list of user's film lists with add/remove toggle buttons
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

    // Handle add/remove button clicks within the lists section (event delegation)
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

    // ===== INLINE CREATE LIST — create a new list without leaving the modal =====
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

    // Intercept clicks on any .poster_link to open the modal instead of navigating
    // (skips person links which should navigate directly to the credits page)
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
