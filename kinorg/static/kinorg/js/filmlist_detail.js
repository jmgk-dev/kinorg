const autocompleteResults = document.getElementById('user_autocomplete_results');
const alreadyInvited = new Set(JSON.parse(autocompleteResults.dataset.invited || '[]'));

const inviteModal = document.getElementById('invite_modal');
const inviteOpenBtn = document.getElementById('invite_modal_btn');
const inviteCloseBtn = document.getElementById('invite_modal_close');
const inviteMessage = document.getElementById('invite_message');

if (inviteOpenBtn) {
    inviteOpenBtn.addEventListener('click', () => {
        inviteModal.style.display = 'block';
    });
}
if (inviteCloseBtn) {
    inviteCloseBtn.addEventListener('click', () => {
        inviteModal.style.display = 'none';
    });
}
window.addEventListener('click', (e) => {
    if (e.target === inviteModal) {
        inviteModal.style.display = 'none';
    }
});

const usernameInput = document.getElementById('invite_username_input');
const selectedUser = document.getElementById('selected_user');
const selectedUserLabel = document.getElementById('selected_user_label');
const clearSelected = document.getElementById('clear_selected');
const listId = document.querySelector('input[name="list_id"]').value;
const inviteForm = document.querySelector('#invite_modal form');
const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]').value;
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

// Event delegation for cancel/remove buttons inside the modal
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

if (inviteForm) {
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
