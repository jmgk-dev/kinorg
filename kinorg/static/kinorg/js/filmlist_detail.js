// ===== ADDED-BY BADGES =====

const BADGE_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#e91e63'];

function badgeColor(username) {
    let hash = 0;
    for (let i = 0; i < username.length; i++) {
        hash = username.charCodeAt(i) + ((hash << 5) - hash);
    }
    return BADGE_COLORS[Math.abs(hash) % BADGE_COLORS.length];
}

function addBadge(li) {
    const addedBy = li.dataset.addedBy;
    if (!addedBy) return;
    const link = li.querySelector('.poster_link');
    if (!link) return;
    const badge = document.createElement('span');
    badge.className = 'added_by_badge';
    badge.textContent = addedBy[0].toUpperCase();
    badge.style.background = badgeColor(addedBy);
    link.appendChild(badge);
}

const filmGrid = document.getElementById('film_grid');
const isShared = filmGrid && filmGrid.dataset.isShared === 'true';

if (isShared && filmGrid) {
    filmGrid.querySelectorAll('li[data-added-by]').forEach(addBadge);
}


// ===== LOAD MORE =====

const loadMoreBtn = document.getElementById('load_more_btn');

if (loadMoreBtn && filmGrid) {
    const baseUrl = filmGrid.dataset.baseUrl;
    const placeholderUrl = filmGrid.dataset.placeholderUrl;
    const filmUrlTemplate = filmGrid.dataset.filmUrl;
    const additionsUrl = filmGrid.dataset.additionsUrl;

    loadMoreBtn.addEventListener('click', () => {
        const offset = loadMoreBtn.dataset.offset;
        const sort = loadMoreBtn.dataset.sort;
        const country = loadMoreBtn.dataset.country;
        const genre = loadMoreBtn.dataset.genre;
        const addedBy = loadMoreBtn.dataset.addedBy || '';

        loadMoreBtn.disabled = true;
        loadMoreBtn.textContent = 'Loading...';

        const params = new URLSearchParams({ offset, sort });
        if (country) params.set('country', country);
        if (genre) params.set('genre', genre);
        if (addedBy) params.set('added_by', addedBy);

        fetch(`${additionsUrl}?${params}`)
            .then(res => res.json())
            .then(data => {
                data.films.forEach(film => {
                    const filmUrl = filmUrlTemplate.replace('/0', '/' + film.id);
                    const posterSrc = film.poster_path && film.poster_path !== 'None'
                        ? `${baseUrl}w200${film.poster_path}`
                        : placeholderUrl;
                    const li = document.createElement('li');
                    li.className = 'results_item';
                    li.dataset.addedBy = film.added_by || '';
                    li.innerHTML = `<a class="poster_link" href="${filmUrl}"
                        data-film-id="${film.id}"
                        data-film-title="${film.title}"
                        data-poster-path="${film.poster_path}"
                        data-year="${film.year || ''}"
                        data-director="${(film.director || '').replace(/"/g, '&quot;')}"
                        data-media-type="movie">
                        <img class="poster" src="${posterSrc}" alt="${film.title}">
                    </a>`;
                    filmGrid.appendChild(li);
                    if (isShared) addBadge(li);
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


// ===== ARCHIVE TOGGLE =====

const archiveBtn = document.querySelector('.archive_btn');
if (archiveBtn) {
    archiveBtn.addEventListener('click', () => {
        const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)[1];
        fetch(archiveBtn.dataset.url, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
        })
        .then(r => r.json())
        .then(data => {
            archiveBtn.textContent = data.archived ? 'Unarchive' : 'Archive';
            archiveBtn.dataset.archived = data.archived ? 'true' : 'false';
        });
    });
}


// ===== LIST PICKER =====

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


// ===== INVITE MODAL =====

const autocompleteResults = document.getElementById('user_autocomplete_results');
const alreadyInvited = new Set(JSON.parse(autocompleteResults ? autocompleteResults.dataset.invited || '[]' : '[]'));

const inviteModal = document.getElementById('invite_modal');
const inviteOpenBtn = document.getElementById('invite_modal_btn');
const inviteCloseBtn = document.getElementById('invite_modal_close');
const inviteMessage = document.getElementById('invite_message');

if (inviteOpenBtn) {
    inviteOpenBtn.addEventListener('click', () => {
        inviteModal.style.display = 'block';
    });
    if (new URLSearchParams(window.location.search).get('invite') === '1') {
        inviteModal.style.display = 'block';
    }
}
const openedViaInviteLink = new URLSearchParams(window.location.search).get('invite') === '1';

if (inviteCloseBtn) {
    inviteCloseBtn.addEventListener('click', () => {
        inviteModal.style.display = 'none';
        if (openedViaInviteLink) history.back();
    });
}
window.addEventListener('click', (e) => {
    if (e.target === inviteModal) {
        inviteModal.style.display = 'none';
        if (openedViaInviteLink) history.back();
    }
});

const usernameInput = document.getElementById('invite_username_input');
const selectedUser = document.getElementById('selected_user');
const selectedUserLabel = document.getElementById('selected_user_label');
const clearSelected = document.getElementById('clear_selected');
const listIdInput = document.querySelector('input[name="list_id"]');
const listId = listIdInput ? listIdInput.value : null;
const inviteForm = document.querySelector('#invite_modal form');
const csrfTokenEl = document.querySelector('[name="csrfmiddlewaretoken"]');
const csrfToken = csrfTokenEl ? csrfTokenEl.value : null;
let debounceTimer;
let userSelected = false;

function selectUser(username) {
    clearTimeout(debounceTimer);
    userSelected = true;
    usernameInput.value = username;
    usernameInput.style.display = 'none';
    autocompleteResults.innerHTML = '';
    selectedUserLabel.textContent = username;
    selectedUser.style.display = 'flex';
}

function resetForm() {
    userSelected = false;
    usernameInput.value = '';
    usernameInput.style.display = '';
    selectedUser.style.display = 'none';
    selectedUserLabel.textContent = '';
    autocompleteResults.innerHTML = '';
}

function addInvitedUserToList(username, invitationId) {
    let section = document.querySelector('.invited_users_section');

    if (!section) {
        section = document.createElement('div');
        section.className = 'invited_users_section';
        section.innerHTML = '<p><b>Invited users</b></p><ul class="invited_users_list"></ul>';
        inviteForm.parentElement.appendChild(section);
    }

    const li = document.createElement('li');
    li.className = 'invited_user_item';
    li.dataset.invitationId = invitationId;
    li.innerHTML = `
        <span>${username}</span>
        <span class="invited_user_status">
            Pending
            <button class="cancel_invite_btn" data-invitation-id="${invitationId}" data-username="${username}">Cancel</button>
        </span>`;
    section.querySelector('.invited_users_list').appendChild(li);
}

function removeInviteRow(li, username) {
    li.remove();
    if (username) alreadyInvited.delete(username);
    const list = document.querySelector('.invited_users_list');
    if (list && list.children.length === 0) {
        document.querySelector('.invited_users_section').remove();
    }
}

if (inviteForm) {
    inviteForm.parentElement.addEventListener('click', (e) => {
        if (e.target.classList.contains('cancel_invite_btn')) {
            const invitationId = e.target.dataset.invitationId;
            const username = e.target.dataset.username;
            const li = e.target.closest('li');

            fetch('/cancel-invite/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: new URLSearchParams({ invitation_id: invitationId }),
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) removeInviteRow(li, username);
            });
        }

        if (e.target.classList.contains('remove_guest_btn')) {
            const userId = e.target.dataset.userId;
            const li = e.target.closest('li');

            fetch('/remove-guest/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: new URLSearchParams({ user_id: userId, list_id: listId }),
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) removeInviteRow(li, null);
            });
        }
    });

    inviteForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const formData = new FormData(inviteForm);

        fetch(inviteForm.action, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(res => res.json())
        .then(data => {
            inviteMessage.textContent = data.message;
            inviteMessage.className = 'invite_message ' + (data.success ? 'invite_success' : 'invite_error');

            if (data.success) {
                alreadyInvited.add(data.username);
                addInvitedUserToList(data.username, data.invitation_id);
                resetForm();
            }
        });
    });
}

if (clearSelected) {
    clearSelected.addEventListener('click', () => {
        resetForm();
        usernameInput.focus();
    });
}

if (usernameInput) {
    usernameInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);

        if (userSelected) return;

        const query = usernameInput.value.trim();

        if (query.length < 2) {
            autocompleteResults.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/user-autocomplete/?q=${encodeURIComponent(query)}&list_id=${listId}`)
                .then(res => res.json())
                .then(data => {
                    if (userSelected) return;
                    autocompleteResults.innerHTML = '';
                    data.results.forEach(user => {
                        const isInvited = alreadyInvited.has(user.username);
                        const li = document.createElement('li');
                        li.textContent = user.username + (isInvited ? ' (already invited)' : '');
                        li.className = 'autocomplete-item' + (isInvited ? ' is-invited' : '');
                        if (!isInvited) {
                            li.addEventListener('click', () => selectUser(user.username));
                        }
                        autocompleteResults.appendChild(li);
                    });
                });
        }, 300);
    });
}
