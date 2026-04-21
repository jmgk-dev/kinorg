// Lists page JS — handles the invite modal (shared across all lists on the page),
// archive toggle buttons, and live poster updates when films are added/removed via the film modal.

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
// getCsrf() is provided by utils.js (loaded in base.html)

let listsUserSelected = false;
let listsDebounce;

// Render invited users section from per-list invitation data embedded in the button
function renderInvitedUsers(invitations) {
    const existing = listsModal.querySelector('.invited_users_section');
    if (existing) existing.remove();
    if (!invitations || invitations.length === 0) return;

    const section = document.createElement('div');
    section.className = 'invited_users_section';
    section.innerHTML = '<p><b>Invited users</b></p><ul class="invited_users_list"></ul>';
    const ul = section.querySelector('.invited_users_list');

    invitations.forEach(inv => {
        const li = document.createElement('li');
        li.className = 'invited_user_item';
        li.dataset.invitationId = inv.id;
        let statusHtml;
        if (inv.accepted) {
            statusHtml = `✓ Accepted <button class="remove_guest_btn" data-user-id="${inv.user_id}">Remove</button>`;
        } else if (inv.declined) {
            statusHtml = `✗ Declined`;
        } else {
            statusHtml = `Pending <button class="cancel_invite_btn" data-invitation-id="${inv.id}" data-username="${inv.username}">Cancel</button>`;
        }
        li.innerHTML = `<span>${inv.username}</span><span class="invited_user_status">${statusHtml}</span>`;
        ul.appendChild(li);
    });

    listsModal.querySelector('.modal-content').appendChild(section);
}

// Add a new "Pending" row after a successful invite
function addInvitedUserToList(username, invitationId) {
    let section = listsModal.querySelector('.invited_users_section');
    if (!section) {
        section = document.createElement('div');
        section.className = 'invited_users_section';
        section.innerHTML = '<p><b>Invited users</b></p><ul class="invited_users_list"></ul>';
        listsModal.querySelector('.modal-content').appendChild(section);
    }
    const li = document.createElement('li');
    li.className = 'invited_user_item';
    li.dataset.invitationId = invitationId;
    li.innerHTML = `<span>${username}</span><span class="invited_user_status">Pending <button class="cancel_invite_btn" data-invitation-id="${invitationId}" data-username="${username}">Cancel</button></span>`;
    section.querySelector('.invited_users_list').appendChild(li);
}

function removeInviteRow(li, username) {
    li.remove();
    const ul = listsModal.querySelector('.invited_users_list');
    if (ul && ul.children.length === 0) {
        listsModal.querySelector('.invited_users_section')?.remove();
    }
}

// Open invite modal for the clicked list — each list's invite button stores the list ID/title
document.querySelectorAll('.btn-invite').forEach(btn => {
    btn.addEventListener('click', () => {
        listsListId.value = btn.dataset.listId;
        listsHeading.textContent = 'Invite to ' + btn.dataset.listTitle;
        listsMessage.textContent = '';
        listsMessage.className = 'invite_message';
        resetListsForm();
        const invitations = JSON.parse(btn.dataset.invitations || '[]');
        renderInvitedUsers(invitations);
        listsModal.style.display = 'flex';
    });
});

document.getElementById('lists_invite_close').addEventListener('click', () => {
    listsModal.style.display = 'none';
});

window.addEventListener('click', e => {
    if (e.target === listsModal) listsModal.style.display = 'none';
});
document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && listsModal.style.display !== 'none') listsModal.style.display = 'none';
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

// Archive/unarchive toggle buttons — POST then reload page to move list between sections
document.querySelectorAll('.archive_btn:not(.rename_btn)').forEach(btn => {
    btn.addEventListener('click', () => {
        fetch(btn.dataset.url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf() },
        })
        .then(r => r.json())
        .then(() => {
            window.location.reload();
        })
        .catch(() => {
            window.location.reload();
        });
    });
});

// ===== RENAME MODAL =====
// Each list card has a Rename button that opens a modal pre-filled with the current title.
// On save, we POST to /rename-list/ and update the title in the DOM directly — no page reload
// needed. The rename button's data-list-title is also updated so re-opening the modal shows
// the latest name. currentListId and currentListItem track which card triggered the modal.
(function () {
    const modal = document.getElementById('rename_modal');
    const input = document.getElementById('rename_input');
    const submit = document.getElementById('rename_submit');
    const error = document.getElementById('rename_error');
    let currentListId = null;     // ID of the list being renamed
    let currentListItem = null;   // The .list_item element for that list card

    // Wire up each Rename button to open the modal for its list
    document.querySelectorAll('.rename_btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentListId = btn.dataset.listId;
            currentListItem = btn.closest('.list_item');
            input.value = btn.dataset.listTitle;
            error.style.display = 'none';
            modal.style.display = 'flex';
            setTimeout(() => { input.focus(); input.select(); }, 50);
        });
    });

    document.getElementById('rename_modal_close').addEventListener('click', close);
    modal.addEventListener('click', e => { if (e.target === modal) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && modal.style.display !== 'none') close(); });

    function close() {
        modal.style.display = 'none';
    }

    function doRename() {
        const title = input.value.trim();
        if (!title) return;
        submit.disabled = true;
        fetch('/rename-list/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body: new URLSearchParams({ list_id: currentListId, title }),
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Update the visible title and the button's stored title in the DOM
                const titleEl = currentListItem.querySelector('.list_item_title');
                if (titleEl) titleEl.textContent = data.title;
                const renameBtn = currentListItem.querySelector('.rename_btn');
                if (renameBtn) renameBtn.dataset.listTitle = data.title;
                close();
            } else {
                error.textContent = data.error || 'Could not rename list.';
                error.style.display = 'block';
            }
            submit.disabled = false;
        })
        .catch(() => {
            error.textContent = 'Something went wrong.';
            error.style.display = 'block';
            submit.disabled = false;
        });
    }

    submit.addEventListener('click', doRename);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doRename(); });
}());

// Cancel/remove invite buttons inside the modal (event delegation)
listsModal.addEventListener('click', e => {
    if (e.target.classList.contains('cancel_invite_btn')) {
        const invitationId = e.target.dataset.invitationId;
        const username = e.target.dataset.username;
        const li = e.target.closest('li');
        fetch('/cancel-invite/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body: new URLSearchParams({ invitation_id: invitationId }),
        })
        .then(r => r.json())
        .then(data => { if (data.success) removeInviteRow(li, username); });
    }

    if (e.target.classList.contains('remove_guest_btn')) {
        const userId = e.target.dataset.userId;
        const li = e.target.closest('li');
        fetch('/remove-guest/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body: new URLSearchParams({ user_id: userId, list_id: listsListId.value }),
        })
        .then(r => r.json())
        .then(data => { if (data.success) removeInviteRow(li, null); });
    }
});

// Submit invite form via AJAX — show success/error message, reset form on success
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
        if (data.success) {
            addInvitedUserToList(data.username, data.invitation_id);
            resetListsForm();
        }
    });
});


// ===== MODAL LIVE UPDATE — when a film is added/removed via the film modal,
// update the poster stack preview on the affected list card =====

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
