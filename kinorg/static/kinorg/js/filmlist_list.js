const listsModal = document.getElementById('lists_invite_modal');
const listsHeading = document.getElementById('lists_invite_heading');
const listsListId = document.getElementById('lists_invite_list_id');
const listsMessage = document.getElementById('lists_invite_message');
const listsForm = document.getElementById('lists_invite_form');
const listsInput = document.getElementById('lists_invite_input');
const listsSelected = document.getElementById('lists_invite_selected');
const listsSelectedLabel = document.getElementById('lists_invite_selected_label');
const listsClear = document.getElementById('lists_invite_clear');
const listsAutocomplete = document.getElementById('lists_invite_autocomplete');
const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]').value;

let listsUserSelected = false;
let listsDebounce;

document.querySelectorAll('.btn-invite').forEach(btn => {
    btn.addEventListener('click', () => {
        listsListId.value = btn.dataset.listId;
        listsHeading.textContent = 'Invite to ' + btn.dataset.listTitle;
        listsMessage.textContent = '';
        listsMessage.className = 'invite_message';
        resetListsForm();
        listsModal.style.display = 'block';
    });
});

document.getElementById('lists_invite_close').addEventListener('click', () => {
    listsModal.style.display = 'none';
});

window.addEventListener('click', e => {
    if (e.target === listsModal) listsModal.style.display = 'none';
});

function resetListsForm() {
    listsUserSelected = false;
    listsInput.value = '';
    listsInput.style.display = '';
    listsSelected.style.display = 'none';
    listsSelectedLabel.textContent = '';
    listsAutocomplete.innerHTML = '';
}

function selectListsUser(username) {
    clearTimeout(listsDebounce);
    listsUserSelected = true;
    listsInput.value = username;
    listsInput.style.display = 'none';
    listsAutocomplete.innerHTML = '';
    listsSelectedLabel.textContent = username;
    listsSelected.style.display = 'flex';
}

listsClear.addEventListener('click', () => {
    resetListsForm();
    listsInput.focus();
});

listsInput.addEventListener('input', () => {
    clearTimeout(listsDebounce);
    if (listsUserSelected) return;
    const q = listsInput.value.trim();
    if (q.length < 2) { listsAutocomplete.innerHTML = ''; return; }
    listsDebounce = setTimeout(() => {
        fetch(`/user-autocomplete/?q=${encodeURIComponent(q)}&list_id=${listsListId.value}`)
            .then(r => r.json())
            .then(data => {
                if (listsUserSelected) return;
                listsAutocomplete.innerHTML = '';
                data.results.forEach(user => {
                    const li = document.createElement('li');
                    li.textContent = user.username;
                    li.className = 'autocomplete-item';
                    li.addEventListener('click', () => selectListsUser(user.username));
                    listsAutocomplete.appendChild(li);
                });
            });
    }, 300);
});

document.querySelectorAll('.archive_btn').forEach(btn => {
    btn.addEventListener('click', () => {
        fetch(btn.dataset.url, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
        })
        .then(r => r.json())
        .then(() => {
            window.location.reload();
        });
    });
});

listsForm.addEventListener('submit', e => {
    e.preventDefault();
    fetch(listsForm.action, {
        method: 'POST',
        body: new FormData(listsForm),
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(r => r.json())
    .then(data => {
        listsMessage.textContent = data.message;
        listsMessage.className = 'invite_message ' + (data.success ? 'invite_success' : 'invite_error');
        if (data.success) resetListsForm();
    });
});


// ===== MODAL LIVE UPDATE =====

document.addEventListener('filmListChanged', (e) => {
    const { filmId, listId, nowInList, posterPath, title } = e.detail;

    // Find the list_item for this list
    const inviteBtn = document.querySelector(`.btn-invite[data-list-id="${listId}"]`);
    if (!inviteBtn) return;
    const listItem = inviteBtn.closest('.list_item');
    if (!listItem) return;

    const stack = listItem.querySelector('.list_poster_stack');

    if (!nowInList) {
        if (!stack) return;
        const link = stack.querySelector(`.poster_link[data-film-id="${filmId}"]`);
        if (link) link.closest('.stack_item').remove();
    } else {
        if (!stack) return;
        if (!stack.querySelector(`.poster_link[data-film-id="${filmId}"]`)) {
            const li = document.createElement('li');
            li.className = 'stack_item';
            const src = posterPath
                ? `https://image.tmdb.org/t/p/w200${posterPath}`
                : listItem.querySelector('.poster')?.src || '';
            li.innerHTML = `<a class="poster_link" href="/film-detail/${filmId}/" data-film-id="${filmId}" data-film-title="${title.replace(/"/g, '&quot;')}" data-poster-path="${posterPath || ''}" data-media-type="movie"><img class="poster" src="${src}" alt="${title.replace(/"/g, '&quot;')}"></a>`;
            stack.prepend(li);
        }
    }
});
