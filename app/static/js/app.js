/**
 * Inter-Office Memo Management System - Frontend SPA Engine
 * CSE226 Foundations of Vibe Coding (North South University)
 */

const API_BASE = '/api/v1';

// Global Application State
window.appState = {
    token: localStorage.getItem('memo_token') || '',
    user: JSON.parse(localStorage.getItem('memo_user') || 'null'),
    organization: JSON.parse(localStorage.getItem('memo_org') || 'null'),
    currentView: 'dashboard',
    selectedMemoId: null,
    selectedVersion: null,
    inboxMemos: [],
    sentMemos: [],
    draftMemos: [],
    completedMemos: [],
    searchResults: [],
    notifications: [],
    unreadCount: 0,
    departments: [],
    categories: [],
    templates: [],
    orgUsers: [],
    delegations: [],
    auditLogs: [],
    reportsData: null,
    quillEditor: null,
    demoAccounts: [],
    charts: {}
};

// API Helper
async function apiCall(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(appState.token ? { 'Authorization': `Bearer ${appState.token}` } : {}),
        ...options.headers
    };

    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401 && !endpoint.startsWith('/auth/login') && !endpoint.startsWith('/demo')) {
            logout();
            throw new Error('Session expired. Please log in again.');
        }

        if (!response.ok) {
            const errData = await response.json().catch(() => ({ detail: 'An unexpected error occurred' }));
            throw new Error(errData.detail || `Request failed with status ${response.status}`);
        }

        if (response.headers.get('content-type')?.includes('application/pdf')) {
            return response.blob();
        }

        return await response.json();
    } catch (err) {
        console.error(`API Error on ${endpoint}:`, err);
        throw err;
    }
}

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const bgColors = {
        success: 'bg-emerald-600 text-white',
        error: 'bg-rose-600 text-white',
        warning: 'bg-amber-600 text-white',
        info: 'bg-slate-800 text-white'
    };

    toast.className = `flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all duration-300 transform translate-y-2 opacity-0 ${bgColors[type] || bgColors.info}`;
    toast.innerHTML = `<span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
    loadDemoAccounts();
    if (appState.token && appState.user) {
        setupApp();
    } else {
        showView('login');
    }

    // Set up real-time notification polling
    setInterval(() => {
        if (appState.token && appState.user) {
            fetchUnreadCount();
        }
    }, 12000);
});

async function setupApp() {
    updateHeaderUI();
    showView('dashboard');
    await loadInitialData();
}

async function loadDemoAccounts() {
    try {
        const data = await apiCall('/demo/accounts');
        appState.demoAccounts = data;
        renderDemoSwitcher(data);
    } catch (e) {
        console.warn('Could not load demo accounts:', e);
    }
}

function renderDemoSwitcher(demoData) {
    const container = document.getElementById('demo-switcher-dropdown');
    if (!container) return;

    let html = '';
    demoData.forEach(org => {
        html += `<div class="px-3 py-1.5 text-xs font-bold text-slate-400 uppercase tracking-wider bg-slate-100 dark:bg-slate-800">${org.org_name} (${org.org_code})</div>`;
        org.users.forEach(u => {
            const isCurrent = appState.user && appState.user.id === u.id;
            html += `
                <button onclick="quickLogin(${u.id})" class="w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-indigo-50 dark:hover:bg-slate-700 transition ${isCurrent ? 'bg-indigo-50/80 font-bold text-indigo-700' : 'text-slate-700 dark:text-slate-200'}">
                    <div>
                        <div class="font-semibold">${u.full_name}</div>
                        <div class="text-[11px] text-slate-500">${u.designation || u.department} • <span class="capitalize text-indigo-600">${u.role}</span></div>
                    </div>
                    ${isCurrent ? '<span class="text-xs bg-indigo-600 text-white px-1.5 py-0.5 rounded">Active</span>' : ''}
                </button>
            `;
        });
    });
    container.innerHTML = html;
}

async function quickLogin(userId) {
    try {
        const res = await apiCall(`/demo/quick-login/${userId}`, { method: 'POST' });
        setSession(res.access_token, res.user, res.organization);
        showToast(`Logged in as ${res.user.full_name} (${res.organization.name})`, 'success');
        setupApp();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function setSession(token, user, organization) {
    appState.token = token;
    appState.user = user;
    appState.organization = organization;
    localStorage.setItem('memo_token', token);
    localStorage.setItem('memo_user', JSON.stringify(user));
    localStorage.setItem('memo_org', JSON.stringify(organization));
}

function logout() {
    apiCall('/auth/logout', { method: 'POST' }).catch(() => {});
    appState.token = '';
    appState.user = null;
    appState.organization = null;
    localStorage.removeItem('memo_token');
    localStorage.removeItem('memo_user');
    localStorage.removeItem('memo_org');
    showToast('Logged out successfully', 'info');
    showView('login');
}

async function loadInitialData() {
    try {
        const data = await apiCall('/memos/bootstrap');
        appState.departments = data.departments || [];
        appState.categories = data.categories || [];
        appState.templates = data.templates || [];
        appState.orgUsers = data.org_users || [];
        appState.delegations = data.delegations || [];
        appState.inboxMemos = data.inbox || [];
        appState.sentMemos = data.sent || [];
        appState.completedMemos = data.completed || [];
        appState.reportsData = data.statistics || null;
        appState.unreadCount = data.unread_notifications || 0;

        // Update notification count badge
        const notifBadge = document.getElementById('notif-badge');
        if (notifBadge) {
            notifBadge.textContent = appState.unreadCount;
            notifBadge.classList.toggle('hidden', appState.unreadCount === 0);
        }

        // Fast render current dashboard
        if (appState.currentView === 'dashboard') {
            updateDashboardDOM();
        }
    } catch (e) {
        console.warn('Initial bootstrap error, falling back:', e);
    }
}

function updateHeaderUI() {
    if (!appState.user || !appState.organization) return;
    
    document.getElementById('org-name-display').textContent = appState.organization.name;
    document.getElementById('org-code-badge').textContent = appState.organization.code.toUpperCase();
    document.getElementById('user-name-display').textContent = appState.user.full_name;
    document.getElementById('user-designation-display').textContent = `${appState.user.designation || 'Staff'} • ${appState.user.role.toUpperCase()}`;
    
    // Show/hide admin-only navigation links
    const adminNavs = document.querySelectorAll('.admin-only-nav');
    adminNavs.forEach(el => {
        el.style.display = appState.user.role === 'admin' ? 'flex' : 'none';
    });

    renderDemoSwitcher(appState.demoAccounts);
}

// Navigation & View Switching
function showView(viewName, memoId = null) {
    appState.currentView = viewName;
    if (memoId) appState.selectedMemoId = memoId;

    // Toggle main containers
    const authContainer = document.getElementById('auth-container');
    const mainContainer = document.getElementById('main-app-container');

    if (viewName === 'login' || viewName === 'register' || viewName === 'forgot-password') {
        document.body.classList.remove('bg-slate-100');
        document.body.classList.add('bg-slate-950');
        authContainer.classList.remove('hidden');
        mainContainer.classList.add('hidden');
        document.getElementById('login-view').classList.toggle('hidden', viewName !== 'login');
        document.getElementById('register-view').classList.toggle('hidden', viewName !== 'register');
        const forgotView = document.getElementById('forgot-password-view');
        if (forgotView) forgotView.classList.toggle('hidden', viewName !== 'forgot-password');

        // Update auth top tabs
        const tabs = [
            { id: 'tab-login-btn', view: 'login' },
            { id: 'tab-register-btn', view: 'register' },
            { id: 'tab-forgot-btn', view: 'forgot-password' }
        ];
        tabs.forEach(t => {
            const btn = document.getElementById(t.id);
            if (btn) {
                if (t.view === viewName) {
                    btn.className = 'px-3 py-1.5 rounded-xl text-xs font-bold transition bg-indigo-600 text-white shadow-sm';
                } else {
                    btn.className = 'px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition';
                }
            }
        });

        if (window.lucide) lucide.createIcons();
        return;
    }

    document.body.classList.remove('bg-slate-950');
    document.body.classList.add('bg-slate-100');
    authContainer.classList.add('hidden');
    mainContainer.classList.remove('hidden');

    // Update active state in sidebar nav items
    document.querySelectorAll('.nav-link').forEach(link => {
        const target = link.getAttribute('data-view');
        if (target === viewName) {
            link.classList.add('bg-indigo-700', 'text-white');
            link.classList.remove('text-indigo-100', 'hover:bg-indigo-800');
        } else {
            link.classList.remove('bg-indigo-700', 'text-white');
            link.classList.add('text-indigo-100', 'hover:bg-indigo-800');
        }
    });

    // Hide all view panels
    document.querySelectorAll('.view-panel').forEach(p => p.classList.add('hidden'));

    // Route view rendering
    switch (viewName) {
        case 'dashboard':
            renderDashboardView();
            break;
        case 'inbox':
            renderInboxView();
            break;
        case 'sent':
            renderSentView();
            break;
        case 'drafts':
            renderDraftsView();
            break;
        case 'completed':
            renderCompletedView();
            break;
        case 'create-memo':
            renderCreateMemoView();
            break;
        case 'memo-detail':
            renderMemoDetailView(memoId || appState.selectedMemoId);
            break;
        case 'search':
            renderSearchView();
            break;
        case 'delegations':
            renderDelegationsView();
            break;
        case 'admin':
            renderAdminView();
            break;
        case 'reports':
            renderReportsView();
            break;
        case 'audit':
            renderAuditView();
            break;
        case 'profile':
            renderProfileView();
            break;
    }
}

function updateDashboardDOM() {
    const stats = appState.reportsData || { urgent_memos: 0, memos_by_status: {} };
    const inbox = appState.inboxMemos || [];
    const sent = appState.sentMemos || [];
    const completed = appState.completedMemos || [];

    const elInbox = document.getElementById('stat-inbox-count');
    const elSent = document.getElementById('stat-sent-count');
    const elCompleted = document.getElementById('stat-completed-count');
    const elUrgent = document.getElementById('stat-urgent-count');

    if (elInbox) elInbox.textContent = inbox.length;
    if (elSent) elSent.textContent = sent.length;
    if (elCompleted) elCompleted.textContent = completed.length;
    if (elUrgent) elUrgent.textContent = stats.urgent_memos || 0;

    // Render Action Required preview list
    const inboxList = document.getElementById('dash-inbox-list');
    if (inboxList) {
        if (inbox.length === 0) {
            inboxList.innerHTML = `<div class="p-6 text-center text-slate-500 text-sm">No pending memos requiring your action right now. All caught up! 🎉</div>`;
        } else {
            inboxList.innerHTML = inbox.slice(0, 5).map(m => createMemoCardHTML(m, 'action')).join('');
        }
    }

    // Render Recent Activity / Sent preview
    const sentList = document.getElementById('dash-sent-list');
    if (sentList) {
        if (sent.length === 0) {
            sentList.innerHTML = `<div class="p-6 text-center text-slate-500 text-sm">You haven't submitted any memos yet.</div>`;
        } else {
            sentList.innerHTML = sent.slice(0, 5).map(m => createMemoCardHTML(m, 'sent')).join('');
        }
    }

    if (window.lucide) lucide.createIcons();
}

// -------------------------------------------------------------
// 1. DASHBOARD VIEW
// -------------------------------------------------------------
async function renderDashboardView() {
    const container = document.getElementById('dashboard-view');
    container.classList.remove('hidden');

    // Instant zero-lag render from cache
    updateDashboardDOM();

    // If initial bootstrap not completed yet, fetch
    if (!appState.reportsData) {
        await loadInitialData();
    }
}

// -------------------------------------------------------------
// 2. INBOX VIEW
// -------------------------------------------------------------
async function renderInboxView() {
    const container = document.getElementById('inbox-view');
    container.classList.remove('hidden');

    const priorityFilter = document.getElementById('inbox-filter-priority')?.value || '';
    const sortBy = document.getElementById('inbox-sort-by')?.value || 'date_desc';
    const list = document.getElementById('inbox-memos-list');

    // Instant optimistic render from cache
    if (appState.inboxMemos && appState.inboxMemos.length > 0 && !priorityFilter) {
        list.innerHTML = appState.inboxMemos.map(m => createMemoCardHTML(m, 'action')).join('');
        if (window.lucide) lucide.createIcons();
    } else if (!list.innerHTML) {
        list.innerHTML = `<div class="p-8 text-center text-slate-400 animate-pulse"><div class="h-4 bg-slate-200 rounded w-1/2 mx-auto mb-2"></div><div class="h-3 bg-slate-200 rounded w-1/3 mx-auto"></div></div>`;
    }

    try {
        const memos = await apiCall(`/memos/inbox?priority=${priorityFilter}&sort_by=${sortBy}`);
        appState.inboxMemos = memos;
        if (memos.length === 0) {
            list.innerHTML = `<div class="bg-white rounded-xl p-12 text-center text-slate-500 border border-slate-200">
                <i data-lucide="inbox" class="w-12 h-12 mx-auto text-slate-300 mb-3"></i>
                <h3 class="text-base font-semibold text-slate-700">Inbox is empty</h3>
                <p class="text-sm mt-1">There are no memos awaiting your action at this time.</p>
            </div>`;
        } else {
            list.innerHTML = memos.map(m => createMemoCardHTML(m, 'action')).join('');
        }
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// -------------------------------------------------------------
// 3. SENT / MY MEMOS VIEW
// -------------------------------------------------------------
async function renderSentView() {
    const container = document.getElementById('sent-view');
    container.classList.remove('hidden');
    const list = document.getElementById('sent-memos-list');

    // Instant optimistic render from cache
    if (appState.sentMemos && appState.sentMemos.length > 0) {
        list.innerHTML = appState.sentMemos.map(m => createMemoCardHTML(m, 'sent')).join('');
        if (window.lucide) lucide.createIcons();
    } else if (!list.innerHTML) {
        list.innerHTML = `<div class="p-8 text-center text-slate-400 animate-pulse"><div class="h-4 bg-slate-200 rounded w-1/2 mx-auto mb-2"></div><div class="h-3 bg-slate-200 rounded w-1/3 mx-auto"></div></div>`;
    }

    try {
        const memos = await apiCall('/memos/sent');
        appState.sentMemos = memos;
        if (memos.length === 0) {
            list.innerHTML = `<div class="bg-white rounded-xl p-12 text-center text-slate-500 border border-slate-200">
                <i data-lucide="send" class="w-12 h-12 mx-auto text-slate-300 mb-3"></i>
                <h3 class="text-base font-semibold text-slate-700">No sent memos</h3>
                <p class="text-sm mt-1">Memos you submit into workflows will appear here.</p>
            </div>`;
        } else {
            list.innerHTML = memos.map(m => createMemoCardHTML(m, 'sent')).join('');
        }
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// -------------------------------------------------------------
// 4. DRAFTS VIEW
// -------------------------------------------------------------
async function renderDraftsView() {
    const container = document.getElementById('drafts-view');
    container.classList.remove('hidden');
    const list = document.getElementById('drafts-memos-list');

    if (appState.draftMemos && appState.draftMemos.length > 0) {
        list.innerHTML = appState.draftMemos.map(m => createMemoCardHTML(m, 'draft')).join('');
        if (window.lucide) lucide.createIcons();
    } else if (!list.innerHTML) {
        list.innerHTML = `<div class="p-8 text-center text-slate-400 animate-pulse"><div class="h-4 bg-slate-200 rounded w-1/2 mx-auto mb-2"></div><div class="h-3 bg-slate-200 rounded w-1/3 mx-auto"></div></div>`;
    }

    try {
        const memos = await apiCall('/memos/drafts');
        appState.draftMemos = memos;
        if (memos.length === 0) {
            list.innerHTML = `<div class="bg-white rounded-xl p-12 text-center text-slate-500 border border-slate-200">
                <i data-lucide="file-edit" class="w-12 h-12 mx-auto text-slate-300 mb-3"></i>
                <h3 class="text-base font-semibold text-slate-700">No saved drafts</h3>
                <p class="text-sm mt-1">Memos you save without submitting will be listed here.</p>
            </div>`;
        } else {
            list.innerHTML = memos.map(m => createMemoCardHTML(m, 'draft')).join('');
        }
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// -------------------------------------------------------------
// 5. COMPLETED ARCHIVE VIEW
// -------------------------------------------------------------
async function renderCompletedView() {
    const container = document.getElementById('completed-view');
    container.classList.remove('hidden');

    try {
        const memos = await apiCall('/memos/completed');
        appState.completedMemos = memos;
        const list = document.getElementById('completed-memos-list');
        if (memos.length === 0) {
            list.innerHTML = `<div class="bg-white rounded-xl p-12 text-center text-slate-500 border border-slate-200">
                <i data-lucide="archive" class="w-12 h-12 mx-auto text-slate-300 mb-3"></i>
                <h3 class="text-base font-semibold text-slate-700">No completed memos</h3>
                <p class="text-sm mt-1">Finalized approved or rejected memos will be archived here.</p>
            </div>`;
        } else {
            list.innerHTML = memos.map(m => createMemoCardHTML(m, 'completed')).join('');
        }
        lucide.createIcons();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// -------------------------------------------------------------
// 6. CREATE MEMO VIEW
// -------------------------------------------------------------
function renderCreateMemoView() {
    const container = document.getElementById('create-memo-view');
    container.classList.remove('hidden');

    // Populate category dropdown
    const catSelect = document.getElementById('memo-category-select');
    catSelect.innerHTML = '<option value="">Select Category</option>' + appState.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');

    // Populate department dropdown
    const deptSelect = document.getElementById('memo-department-select');
    deptSelect.innerHTML = '<option value="">Select Department</option>' + appState.departments.map(d => `<option value="${d.id}" ${appState.user.department_id === d.id ? 'selected' : ''}>${d.name}</option>`).join('');

    // Populate template dropdown
    const tmplSelect = document.getElementById('memo-template-select');
    tmplSelect.innerHTML = '<option value="">Custom Sequential Workflow</option>' + appState.templates.map(t => `<option value="${t.id}">${t.name}</option>`).join('');

    // Initialize Quill Rich Text Editor
    if (!appState.quillEditor) {
        appState.quillEditor = new Quill('#memo-editor-container', {
            theme: 'snow',
            placeholder: 'Type the memorandum body with full rich-text formatting...',
            modules: {
                toolbar: [
                    [{ 'header': [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    ['blockquote', 'code-block'],
                    ['clean']
                ]
            }
        });
    } else {
        appState.quillEditor.setText('');
    }

    // Initialize default workflow step sequence (Step 1 Approver)
    initWorkflowBuilder();
    lucide.createIcons();
}

function initWorkflowBuilder(templateSteps = null) {
    const container = document.getElementById('workflow-steps-container');
    container.innerHTML = '';

    if (templateSteps && templateSteps.length > 0) {
        // Skip author step if in template definition
        const approverSteps = templateSteps.filter(s => s.step_type !== 'author');
        approverSteps.forEach((s, idx) => {
            addWorkflowStepRow(idx + 1, s.role_name, s.step_type, s.default_user_id);
        });
    } else {
        // Add 2 default steps
        addWorkflowStepRow(1, 'Department Head', 'approval');
        addWorkflowStepRow(2, 'Finance Manager', 'approval');
    }
}

function addWorkflowStepRow(index, defaultRole = '', defaultType = 'approval', defaultUserId = null) {
    const container = document.getElementById('workflow-steps-container');
    const stepCount = container.children.length + 1;

    const row = document.createElement('div');
    row.className = 'workflow-step-row flex items-center gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg';
    row.setAttribute('data-step-index', stepCount);

    const userOptions = appState.orgUsers.map(u => 
        `<option value="${u.id}" ${defaultUserId === u.id ? 'selected' : ''}>${u.full_name} (${u.designation || u.role})</option>`
    ).join('');

    row.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center text-xs flex-shrink-0">
            ${stepCount}
        </div>
        <div class="flex-1 grid grid-cols-1 md:grid-cols-3 gap-2">
            <div>
                <label class="block text-[11px] font-semibold text-slate-500 uppercase">Role / Position</label>
                <input type="text" class="step-role-input w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500" value="${defaultRole || 'Approver'}" placeholder="e.g. Department Head">
            </div>
            <div>
                <label class="block text-[11px] font-semibold text-slate-500 uppercase">Step Type</label>
                <select class="step-type-select w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500">
                    <option value="approval" ${defaultType === 'approval' ? 'selected' : ''}>Approval</option>
                    <option value="review" ${defaultType === 'review' ? 'selected' : ''}>Review / Endorsement</option>
                    <option value="final_approval" ${defaultType === 'final_approval' ? 'selected' : ''}>Final Executive Sanction</option>
                </select>
            </div>
            <div>
                <label class="block text-[11px] font-semibold text-slate-500 uppercase">Assigned User</label>
                <select class="step-user-select w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500">
                    <option value="">Select Assignee</option>
                    ${userOptions}
                </select>
            </div>
        </div>
        <button type="button" onclick="this.closest('.workflow-step-row').remove(); renumberWorkflowSteps();" class="text-slate-400 hover:text-rose-600 p-1">
            <i data-lucide="trash-2" class="w-4 h-4"></i>
        </button>
    `;

    container.appendChild(row);
    renumberWorkflowSteps();
    lucide.createIcons();
}

function renumberWorkflowSteps() {
    const rows = document.querySelectorAll('.workflow-step-row');
    rows.forEach((r, idx) => {
        r.setAttribute('data-step-index', idx + 1);
        r.querySelector('.w-8').textContent = idx + 1;
    });
}

function handleTemplateSelectChange(templateId) {
    if (!templateId) return;
    const tmpl = appState.templates.find(t => t.id == templateId);
    if (!tmpl) return;
    try {
        const steps = JSON.parse(tmpl.steps_json);
        initWorkflowBuilder(steps);
    } catch (e) {
        console.error('Invalid template steps json', e);
    }
}

async function submitMemoForm(isDraft = false) {
    const title = document.getElementById('memo-title-input').value.trim();
    const body = appState.quillEditor ? appState.quillEditor.root.innerHTML : '';
    const categoryId = document.getElementById('memo-category-select').value || null;
    const departmentId = document.getElementById('memo-department-select').value || null;
    const priority = document.getElementById('memo-priority-select').value || 'Normal';

    if (!title) {
        showToast('Please enter a memo subject/title', 'warning');
        return;
    }

    if (!body || body === '<p><br></p>') {
        showToast('Please enter memo content', 'warning');
        return;
    }

    // Collect workflow steps
    const stepRows = document.querySelectorAll('.workflow-step-row');
    const workflowSteps = [];
    for (let r of stepRows) {
        const role = r.querySelector('.step-role-input').value.trim();
        const type = r.querySelector('.step-type-select').value;
        const userId = r.querySelector('.step-user-select').value;

        if (!userId && !isDraft) {
            showToast(`Please assign a user for Step #${r.getAttribute('data-step-index')} (${role})`, 'warning');
            return;
        }

        if (userId) {
            workflowSteps.push({
                role_name: role,
                step_type: type,
                assigned_user_id: parseInt(userId)
            });
        }
    }

    if (workflowSteps.length === 0 && !isDraft) {
        showToast('Please define at least one sequential approval step', 'warning');
        return;
    }

    try {
        const memo = await apiCall('/memos', {
            method: 'POST',
            body: JSON.stringify({
                title,
                body,
                category_id: categoryId ? parseInt(categoryId) : null,
                department_id: departmentId ? parseInt(departmentId) : null,
                priority,
                is_draft: isDraft,
                workflow_steps: workflowSteps
            })
        });

        // Upload attachments if any selected
        const fileInput = document.getElementById('memo-file-attachments');
        if (fileInput && fileInput.files.length > 0) {
            for (let f of fileInput.files) {
                const formData = new FormData();
                formData.append('file', f);
                await apiCall(`/memos/${memo.id}/attachments`, {
                    method: 'POST',
                    body: formData
                });
            }
        }

        showToast(isDraft ? 'Memo saved as draft!' : 'Memo successfully submitted to workflow!', 'success');
        showView('memo-detail', memo.id);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// -------------------------------------------------------------
// 7. MEMO DETAIL & WORKFLOW TIMELINE VIEW
// -------------------------------------------------------------
async function renderMemoDetailView(memoId) {
    const container = document.getElementById('memo-detail-view');
    container.classList.remove('hidden');

    try {
        const memo = await apiCall(`/memos/${memoId}`);
        appState.selectedMemoId = memo.id;

        // Render Header & Badges
        document.getElementById('detail-memo-number').textContent = memo.memo_number;
        document.getElementById('detail-memo-title').textContent = memo.title;
        
        const statusBadge = document.getElementById('detail-memo-status');
        statusBadge.textContent = memo.status;
        statusBadge.className = `px-3 py-1 text-xs font-bold rounded-full ${getStatusBadgeClass(memo.status)}`;

        const priorityBadge = document.getElementById('detail-memo-priority');
        priorityBadge.textContent = memo.priority;
        priorityBadge.className = `px-2.5 py-0.5 text-xs font-semibold rounded ${getPriorityBadgeClass(memo.priority)}`;

        document.getElementById('detail-memo-author').textContent = `${memo.author.full_name} (${memo.author.designation || 'Staff'})`;
        document.getElementById('detail-memo-dept').textContent = memo.department ? memo.department.name : 'General';
        document.getElementById('detail-memo-category').textContent = memo.category ? memo.category.name : 'Uncategorized';
        document.getElementById('detail-memo-date').textContent = new Date(memo.created_at).toLocaleString();

        // Render Rich Content Body
        document.getElementById('detail-memo-body').innerHTML = memo.body;

        // Render Sequential Stepper Visualizer
        renderWorkflowStepper(memo);

        // Render Action Buttons for Current User
        renderWorkflowActionBar(memo);

        // Render Attachments
        renderAttachmentsList(memo);

        // Render Versions Snapshot Tab
        renderVersionsList(memo);

        // Render Discussion & Comments
        renderCommentsList(memo);

        lucide.createIcons();
    } catch (e) {
        showToast(e.message, 'error');
        showView('dashboard');
    }
}

function renderWorkflowStepper(memo) {
    const stepperContainer = document.getElementById('detail-workflow-stepper');
    if (!stepperContainer) return;

    if (!memo.workflow_steps || memo.workflow_steps.length === 0) {
        stepperContainer.innerHTML = '<div class="text-xs text-slate-400">No workflow steps defined.</div>';
        return;
    }

    const steps = memo.workflow_steps;
    let html = '<div class="flex flex-col md:flex-row items-start md:items-center gap-2 overflow-x-auto py-2">';

    steps.forEach((step, idx) => {
        const isCompleted = step.status === 'completed';
        const isCurrent = step.is_current;
        const isRejected = step.status === 'rejected';
        const isChangesReq = step.status === 'changes_requested';

        let iconBg = 'bg-slate-200 text-slate-500 border-slate-300';
        let iconContent = idx;

        if (isCompleted) {
            iconBg = 'bg-emerald-600 text-white border-emerald-600';
            iconContent = '<i data-lucide="check" class="w-4 h-4"></i>';
        } else if (isRejected) {
            iconBg = 'bg-rose-600 text-white border-rose-600';
            iconContent = '<i data-lucide="x" class="w-4 h-4"></i>';
        } else if (isChangesReq) {
            iconBg = 'bg-amber-600 text-white border-amber-600';
            iconContent = '<i data-lucide="alert-circle" class="w-4 h-4"></i>';
        } else if (isCurrent) {
            iconBg = 'bg-amber-500 text-white border-amber-500 step-current-pulse';
            iconContent = '<i data-lucide="clock" class="w-4 h-4"></i>';
        }

        const actionText = step.action_taken ? `(${step.action_taken})` : (isCurrent ? '(Action Pending)' : '');
        const delegateNote = step.on_behalf_of_user ? `<div class="text-[10px] text-indigo-600 font-semibold">via ${step.action_by_user?.full_name} (Delegate)</div>` : '';

        html += `
            <div class="flex items-center gap-2 flex-shrink-0">
                <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs border ${iconBg}">
                        ${iconContent}
                    </div>
                    <div class="text-xs">
                        <div class="font-bold text-slate-800">${step.role_name}</div>
                        <div class="text-slate-500 text-[11px]">${step.assigned_user?.full_name || 'Unassigned'} ${actionText}</div>
                        ${delegateNote}
                    </div>
                </div>
                ${idx < steps.length - 1 ? '<div class="hidden md:block w-8 h-0.5 bg-slate-300 mx-1"></div>' : ''}
            </div>
        `;
    });

    html += '</div>';
    stepperContainer.innerHTML = html;
}

function renderWorkflowActionBar(memo) {
    const actionContainer = document.getElementById('detail-action-container');
    const resubmitContainer = document.getElementById('detail-resubmit-container');
    actionContainer.innerHTML = '';
    resubmitContainer.classList.add('hidden');

    const currentUserId = appState.user.id;
    const isAuthor = memo.author_id === currentUserId;

    // Check if changes requested and user is author -> Show Resubmit Panel
    if (memo.status === 'Changes Requested' && isAuthor) {
        resubmitContainer.classList.remove('hidden');
        document.getElementById('resubmit-title').value = memo.title;
        document.getElementById('resubmit-body').value = memo.body.replace(/<[^>]*>/g, '');
        return;
    }

    // Check if it is currently this user's turn (or delegated turn)
    const activeStep = memo.workflow_steps?.find(s => s.is_current && s.step_index === memo.current_step_index);
    if (!activeStep) return;

    const isAssignee = activeStep.assigned_user_id === currentUserId;
    // Check delegation
    const isDelegate = appState.delegations.some(d => d.delegator_id === activeStep.assigned_user_id && d.delegatee_id === currentUserId && d.is_active);

    if (isAssignee || isDelegate || appState.user.role === 'admin') {
        const delegateLabel = isDelegate ? `<span class="text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded">Acting on behalf of ${activeStep.assigned_user?.full_name}</span>` : (appState.user.role === 'admin' && !isAssignee ? `<span class="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded font-bold">Admin Authority Override</span>` : '');
        
        actionContainer.innerHTML = `
            <div class="p-5 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-2xl mb-6 shadow-sm">
                <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <div class="flex items-center gap-2">
                            <h4 class="font-black text-amber-950 text-sm">Action Required on this Memo</h4>
                            ${delegateLabel}
                        </div>
                        <p class="text-xs text-amber-800 mt-0.5 font-medium">As <b>${activeStep.role_name}</b>, please review the contents and choose a workflow decision below.</p>
                    </div>
                    <div class="flex items-center gap-2 flex-wrap">
                        <button onclick="openActionModal('approve', ${memo.id})" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition">
                            <i data-lucide="check-circle" class="w-4 h-4"></i> Approve Step
                        </button>
                        <button onclick="openActionModal('request_changes', ${memo.id})" class="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition">
                            <i data-lucide="edit-3" class="w-4 h-4"></i> Request Changes
                        </button>
                        <button onclick="openActionModal('reject', ${memo.id})" class="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition">
                            <i data-lucide="x-circle" class="w-4 h-4"></i> Reject Memo
                        </button>
                    </div>
                </div>
            </div>
        `;
    } else {
        const assignedName = activeStep.assigned_user?.full_name || 'Assigned Reviewer';
        actionContainer.innerHTML = `
            <div class="p-4 bg-slate-50 border border-slate-200 rounded-2xl mb-6 flex items-center justify-between gap-4">
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-amber-100 text-amber-800 rounded-xl">
                        <i data-lucide="clock" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <div class="text-xs font-bold text-slate-800">Sequential Workflow in Progress</div>
                        <div class="text-[11px] text-slate-500">Currently awaiting action from <b>${assignedName}</b> (${activeStep.role_name}).</div>
                    </div>
                </div>
                <span class="px-2.5 py-1 text-xs font-bold bg-amber-50 text-amber-800 rounded-lg border border-amber-200">Pending Turn</span>
            </div>
        `;
    }
}

function openActionModal(actionType, memoId) {
    const modal = document.getElementById('workflow-action-modal');
    modal.classList.remove('hidden');
    modal.setAttribute('data-action', actionType);
    modal.setAttribute('data-memo-id', memoId);

    const titleEl = document.getElementById('action-modal-title');
    const commentEl = document.getElementById('action-modal-comment');
    const reqNote = document.getElementById('action-modal-required-note');
    const submitBtn = document.getElementById('action-modal-submit-btn');

    commentEl.value = '';

    if (actionType === 'approve') {
        titleEl.textContent = 'Approve Memo Step';
        reqNote.classList.add('hidden');
        submitBtn.className = 'px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg';
        submitBtn.textContent = 'Confirm Approval';
    } else if (actionType === 'request_changes') {
        titleEl.textContent = 'Request Changes / Revisions';
        reqNote.classList.remove('hidden');
        reqNote.textContent = 'Feedback comment is mandatory explaining required changes.';
        submitBtn.className = 'px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-lg';
        submitBtn.textContent = 'Send Change Request';
    } else if (actionType === 'reject') {
        titleEl.textContent = 'Reject Memo';
        reqNote.classList.remove('hidden');
        reqNote.textContent = 'A rejection reason is required and will terminate the workflow.';
        submitBtn.className = 'px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-lg';
        submitBtn.textContent = 'Confirm Rejection';
    }
}

function closeActionModal() {
    document.getElementById('workflow-action-modal').classList.add('hidden');
}

async function submitWorkflowAction() {
    const modal = document.getElementById('workflow-action-modal');
    const action = modal.getAttribute('data-action');
    const memoId = modal.getAttribute('data-memo-id');
    const comment = document.getElementById('action-modal-comment').value.trim();

    if ((action === 'reject' || action === 'request_changes') && !comment) {
        showToast('Comment/reason is required for this action', 'warning');
        return;
    }

    try {
        await apiCall(`/workflow/${memoId}/action`, {
            method: 'POST',
            body: JSON.stringify({ action, comment })
        });
        showToast(`Action '${action}' executed successfully!`, 'success');
        closeActionModal();
        renderMemoDetailView(memoId);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function submitResubmission(memoId) {
    const title = document.getElementById('resubmit-title').value.trim();
    const body = document.getElementById('resubmit-body').value.trim();
    const summary = document.getElementById('resubmit-summary').value.trim();

    if (!title || !body) {
        showToast('Title and content cannot be blank', 'warning');
        return;
    }

    try {
        await apiCall(`/memos/${memoId}/resubmit`, {
            method: 'POST',
            body: JSON.stringify({
                title,
                body: `<p>${body.replace(/\n/g, '<br>')}</p>`,
                summary_of_changes: summary || 'Revised and resubmitted'
            })
        });
        showToast('Memo updated and resubmitted! Version snapshot recorded.', 'success');
        renderMemoDetailView(memoId);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function renderAttachmentsList(memo) {
    const list = document.getElementById('detail-attachments-list');
    if (!list) return;

    if (!memo.attachments || memo.attachments.length === 0) {
        list.innerHTML = '<div class="text-xs text-slate-400 py-2">No attachments uploaded.</div>';
        return;
    }

    list.innerHTML = memo.attachments.map(att => `
        <div class="flex items-center justify-between p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs">
            <div class="flex items-center gap-2 truncate">
                <i data-lucide="paperclip" class="w-4 h-4 text-slate-400 flex-shrink-0"></i>
                <span class="font-medium text-slate-700 truncate">${att.original_name}</span>
                <span class="text-[10px] text-slate-400">(${(att.file_size / 1024).toFixed(1)} KB)</span>
            </div>
            <div class="flex items-center gap-2">
                <a href="${API_BASE}/memos/${memo.id}/attachments/${att.id}?token=${appState.token}" target="_blank" class="p-1 text-indigo-600 hover:text-indigo-800" title="Download">
                    <i data-lucide="download" class="w-4 h-4"></i>
                </a>
            </div>
        </div>
    `).join('');
}

async function uploadDetailAttachment(memoId, fileInput) {
    if (!fileInput.files || fileInput.files.length === 0) return;
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
        await apiCall(`/memos/${memoId}/attachments`, {
            method: 'POST',
            body: formData
        });
        showToast('Attachment uploaded successfully!', 'success');
        renderMemoDetailView(memoId);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function renderVersionsList(memo) {
    const container = document.getElementById('detail-versions-container');
    if (!container) return;

    if (!memo.versions || memo.versions.length === 0) {
        container.innerHTML = '<div class="text-xs text-slate-400 py-2">Initial submission version only.</div>';
        return;
    }

    container.innerHTML = memo.versions.map(v => `
        <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs mb-2">
            <div class="flex items-center justify-between">
                <span class="font-bold text-indigo-700">Version ${v.version_number}</span>
                <span class="text-[11px] text-slate-400">${new Date(v.created_at).toLocaleString()}</span>
            </div>
            <div class="text-slate-700 font-semibold mt-1">${v.title}</div>
            <div class="text-slate-500 text-[11px] mt-0.5">${v.summary_of_changes || 'Snapshot created'}</div>
        </div>
    `).join('');
}

function renderCommentsList(memo) {
    const list = document.getElementById('detail-comments-list');
    if (!list) return;

    if (!memo.comments || memo.comments.length === 0) {
        list.innerHTML = '<div class="text-xs text-slate-400 py-2">No comments yet in this discussion.</div>';
        return;
    }

    list.innerHTML = memo.comments.map(c => {
        let badgeColor = 'bg-slate-100 text-slate-700';
        if (c.comment_type === 'approval') badgeColor = 'bg-emerald-100 text-emerald-800';
        if (c.comment_type === 'rejection') badgeColor = 'bg-rose-100 text-rose-800';
        if (c.comment_type === 'change_request') badgeColor = 'bg-amber-100 text-amber-800';

        return `
            <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs mb-2">
                <div class="flex items-center justify-between mb-1">
                    <div class="flex items-center gap-2">
                        <span class="font-bold text-slate-800">${c.author?.full_name || 'User'}</span>
                        <span class="text-[10px] px-2 py-0.5 rounded uppercase font-semibold ${badgeColor}">${c.comment_type.replace('_', ' ')}</span>
                    </div>
                    <span class="text-[11px] text-slate-400">${new Date(c.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                </div>
                <p class="text-slate-700">${c.text}</p>
            </div>
        `;
    }).join('');
}

async function addDetailComment(memoId) {
    const input = document.getElementById('detail-new-comment');
    const text = input.value.trim();
    if (!text) return;

    try {
        await apiCall(`/memos/${memoId}/comments`, {
            method: 'POST',
            body: JSON.stringify({ comment_type: 'general', text })
        });
        input.value = '';
        renderMemoDetailView(memoId);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function exportMemoPDF(memoId) {
    window.open(`${API_BASE}/memos/${memoId}/pdf?token=${appState.token}`, '_blank');
}

// -------------------------------------------------------------
// 8. SEARCH & ADVANCED FILTERING VIEW
// -------------------------------------------------------------
async function renderSearchView() {
    const container = document.getElementById('search-view');
    container.classList.remove('hidden');

    // Populate search filter dropdowns
    const deptSelect = document.getElementById('search-filter-dept');
    deptSelect.innerHTML = '<option value="">All Departments</option>' + appState.departments.map(d => `<option value="${d.id}">${d.name}</option>`).join('');

    const catSelect = document.getElementById('search-filter-cat');
    catSelect.innerHTML = '<option value="">All Categories</option>' + appState.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');

    executeSearch();
}

async function executeSearch() {
    const q = document.getElementById('search-input-query')?.value || '';
    const status = document.getElementById('search-filter-status')?.value || '';
    const priority = document.getElementById('search-filter-priority')?.value || '';
    const deptId = document.getElementById('search-filter-dept')?.value || '';
    const catId = document.getElementById('search-filter-cat')?.value || '';
    const dateFrom = document.getElementById('search-date-from')?.value || '';
    const dateTo = document.getElementById('search-date-to')?.value || '';

    const params = new URLSearchParams();
    if (q) params.append('q', q);
    if (status && status !== 'All') params.append('status', status);
    if (priority && priority !== 'All') params.append('priority', priority);
    if (deptId) params.append('department_id', deptId);
    if (catId) params.append('category_id', catId);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);

    try {
        const results = await apiCall(`/memos/all?${params.toString()}`);
        appState.searchResults = results;
        const list = document.getElementById('search-results-list');
        document.getElementById('search-count-label').textContent = `${results.length} memos found`;

        if (results.length === 0) {
            list.innerHTML = `<div class="bg-white rounded-xl p-12 text-center text-slate-500 border border-slate-200">
                <i data-lucide="search-x" class="w-12 h-12 mx-auto text-slate-300 mb-3"></i>
                <h3 class="text-base font-semibold text-slate-700">No matching memos</h3>
                <p class="text-sm mt-1">Try adjusting your keyword or filter criteria.</p>
            </div>`;
        } else {
            list.innerHTML = results.map(m => createMemoCardHTML(m, 'search')).join('');
        }
        lucide.createIcons();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// -------------------------------------------------------------
// 9. WORKFLOW DELEGATION VIEW
// -------------------------------------------------------------
async function renderDelegationsView() {
    const container = document.getElementById('delegations-view');
    container.classList.remove('hidden');

    // Populate delegate user select
    const userSelect = document.getElementById('delegation-user-select');
    const eligibleUsers = appState.orgUsers.filter(u => u.id !== appState.user.id);
    userSelect.innerHTML = '<option value="">Select Colleague</option>' + eligibleUsers.map(u => `<option value="${u.id}">${u.full_name} (${u.designation || u.role})</option>`).join('');

    try {
        const delegations = await apiCall('/delegations');
        appState.delegations = delegations;
        const list = document.getElementById('delegations-list');

        if (delegations.length === 0) {
            list.innerHTML = `<div class="p-8 text-center text-slate-500 text-sm">No active or historical delegations found.</div>`;
        } else {
            list.innerHTML = delegations.map(d => {
                const isDelegator = d.delegator_id === appState.user.id;
                const statusBadge = d.is_active ? '<span class="px-2 py-0.5 text-[10px] font-bold bg-emerald-100 text-emerald-800 rounded">Active</span>' : '<span class="px-2 py-0.5 text-[10px] font-bold bg-slate-100 text-slate-600 rounded">Inactive</span>';
                
                return `
                    <div class="p-4 bg-slate-50 border border-slate-200 rounded-xl mb-3 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                        <div>
                            <div class="flex items-center gap-2">
                                <span class="font-bold text-slate-800 text-sm">${isDelegator ? `Delegated to: ${d.delegatee?.full_name}` : `Delegated from: ${d.delegator?.full_name}`}</span>
                                ${statusBadge}
                            </div>
                            <div class="text-xs text-slate-500 mt-1">
                                Period: <b>${new Date(d.start_date).toLocaleDateString()}</b> to <b>${new Date(d.end_date).toLocaleDateString()}</b>
                            </div>
                            ${d.reason ? `<div class="text-xs text-slate-600 mt-1 italic">Reason: "${d.reason}"</div>` : ''}
                        </div>
                        ${isDelegator && d.is_active ? `
                            <button onclick="toggleDelegationStatus(${d.id}, false)" class="px-3 py-1.5 bg-rose-50 text-rose-700 hover:bg-rose-100 text-xs font-bold rounded-lg border border-rose-200">
                                Revoke Delegation
                            </button>
                        ` : ''}
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function createDelegationSubmit() {
    const delegateeId = document.getElementById('delegation-user-select').value;
    const startDate = document.getElementById('delegation-start-date').value;
    const endDate = document.getElementById('delegation-end-date').value;
    const reason = document.getElementById('delegation-reason').value.trim();

    if (!delegateeId || !startDate || !endDate) {
        showToast('Please select colleague and specify date range', 'warning');
        return;
    }

    try {
        await apiCall('/delegations', {
            method: 'POST',
            body: JSON.stringify({
                delegatee_id: parseInt(delegateeId),
                start_date: new Date(startDate).toISOString(),
                end_date: new Date(endDate).toISOString(),
                reason
            })
        });
        showToast('Delegation created successfully!', 'success');
        renderDelegationsView();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function toggleDelegationStatus(delegationId, isActive) {
    try {
        await apiCall(`/delegations/${delegationId}`, {
            method: 'PUT',
            body: JSON.stringify({ is_active: isActive })
        });
        showToast('Delegation updated', 'info');
        renderDelegationsView();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// -------------------------------------------------------------
// 10. ADMIN CONSOLE VIEW
// -------------------------------------------------------------
async function renderAdminView() {
    const container = document.getElementById('admin-view');
    container.classList.remove('hidden');

    if (appState.user.role !== 'admin') {
        showToast('Admin privileges required', 'error');
        showView('dashboard');
        return;
    }

    await Promise.all([
        renderAdminDepartments(),
        renderAdminUsers(),
        renderAdminCategories(),
        renderAdminTemplates()
    ]);
}

async function renderAdminDepartments() {
    const depts = await apiCall('/admin/departments');
    appState.departments = depts;
    const list = document.getElementById('admin-dept-list');
    list.innerHTML = depts.map(d => `
        <div class="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs">
            <div>
                <div class="font-bold text-slate-800">${d.name} ${d.is_active ? '' : '<span class="text-rose-500 font-normal">(Inactive)</span>'}</div>
                <div class="text-slate-500">${d.description || 'No description'} • <b>${d.user_count}</b> users</div>
            </div>
            <button onclick="toggleDeptActive(${d.id}, ${!d.is_active})" class="px-2.5 py-1 text-[11px] font-semibold rounded border ${d.is_active ? 'border-slate-300 text-slate-600 hover:bg-slate-100' : 'border-emerald-300 text-emerald-700 bg-emerald-50'}">
                ${d.is_active ? 'Deactivate' : 'Activate'}
            </button>
        </div>
    `).join('');
}

async function addDepartmentSubmit() {
    const name = document.getElementById('new-dept-name').value.trim();
    const desc = document.getElementById('new-dept-desc').value.trim();
    if (!name) return;

    try {
        await apiCall('/admin/departments', {
            method: 'POST',
            body: JSON.stringify({ name, description: desc })
        });
        document.getElementById('new-dept-name').value = '';
        document.getElementById('new-dept-desc').value = '';
        showToast('Department added!', 'success');
        renderAdminDepartments();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function toggleDeptActive(deptId, newStatus) {
    try {
        await apiCall(`/admin/departments/${deptId}`, {
            method: 'PUT',
            body: JSON.stringify({ is_active: newStatus })
        });
        renderAdminDepartments();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function renderAdminUsers() {
    const users = await apiCall('/admin/users');
    appState.orgUsers = users;
    const list = document.getElementById('admin-user-list');

    // Populate user dept select
    const deptSelect = document.getElementById('new-user-dept');
    deptSelect.innerHTML = '<option value="">Select Department</option>' + appState.departments.map(d => `<option value="${d.id}">${d.name}</option>`).join('');

    list.innerHTML = users.map(u => `
        <div class="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs">
            <div>
                <div class="font-bold text-slate-800">${u.full_name} <span class="capitalize font-semibold text-indigo-600">(${u.role})</span></div>
                <div class="text-slate-500">${u.email} • ${u.designation || 'No title'} • ${u.is_active ? '<span class="text-emerald-600">Active</span>' : '<span class="text-rose-600">Inactive</span>'}</div>
            </div>
            <button onclick="toggleUserActive(${u.id}, ${!u.is_active})" class="px-2.5 py-1 text-[11px] font-semibold rounded border ${u.is_active ? 'border-slate-300 text-slate-600 hover:bg-slate-100' : 'border-emerald-300 text-emerald-700 bg-emerald-50'}">
                ${u.is_active ? 'Deactivate' : 'Activate'}
            </button>
        </div>
    `).join('');
}

async function addUserSubmit() {
    const email = document.getElementById('new-user-email').value.trim();
    const full_name = document.getElementById('new-user-name').value.trim();
    const designation = document.getElementById('new-user-designation').value.trim();
    const department_id = document.getElementById('new-user-dept').value || null;
    const role = document.getElementById('new-user-role').value;
    const password = document.getElementById('new-user-password').value;

    if (!email || !full_name || !password) {
        showToast('Please fill all required user fields', 'warning');
        return;
    }

    try {
        await apiCall('/admin/users', {
            method: 'POST',
            body: JSON.stringify({
                email, full_name, designation,
                department_id: department_id ? parseInt(department_id) : null,
                role, password, is_active: true
            })
        });
        showToast('User created successfully!', 'success');
        document.getElementById('new-user-email').value = '';
        document.getElementById('new-user-name').value = '';
        document.getElementById('new-user-designation').value = '';
        document.getElementById('new-user-password').value = '';
        renderAdminUsers();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function toggleUserActive(userId, newStatus) {
    try {
        await apiCall(`/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify({ is_active: newStatus })
        });
        renderAdminUsers();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function renderAdminCategories() {
    const cats = await apiCall('/admin/categories');
    appState.categories = cats;
    const list = document.getElementById('admin-cat-list');
    list.innerHTML = cats.map(c => `
        <div class="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs">
            <div>
                <div class="font-bold text-slate-800">${c.name}</div>
                <div class="text-slate-500">${c.description || 'No description'}</div>
            </div>
            <span class="px-2 py-0.5 text-[10px] bg-indigo-50 text-indigo-700 rounded font-semibold">Category</span>
        </div>
    `).join('');
}

async function addCategorySubmit() {
    const name = document.getElementById('new-cat-name').value.trim();
    const desc = document.getElementById('new-cat-desc').value.trim();
    if (!name) return;

    try {
        await apiCall('/admin/categories', {
            method: 'POST',
            body: JSON.stringify({ name, description: desc })
        });
        document.getElementById('new-cat-name').value = '';
        document.getElementById('new-cat-desc').value = '';
        showToast('Category created!', 'success');
        renderAdminCategories();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function renderAdminTemplates() {
    const tmpls = await apiCall('/admin/templates');
    appState.templates = tmpls;
    const list = document.getElementById('admin-tmpl-list');
    list.innerHTML = tmpls.map(t => {
        let stepCount = 0;
        try { stepCount = JSON.parse(t.steps_json).length; } catch (e) {}
        return `
            <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs mb-2">
                <div class="font-bold text-slate-800">${t.name} <span class="text-indigo-600 font-normal">(${stepCount} steps)</span></div>
                <div class="text-slate-500 text-[11px]">${t.description || 'No description'}</div>
            </div>
        `;
    }).join('');
}

// -------------------------------------------------------------
// 11. REPORTS & ANALYTICS VIEW
// -------------------------------------------------------------
async function renderReportsView() {
    const container = document.getElementById('reports-view');
    container.classList.remove('hidden');

    try {
        const stats = await apiCall('/reports/statistics');
        appState.reportsData = stats;

        document.getElementById('rep-total-memos').textContent = stats.total_memos;
        document.getElementById('rep-pending-approvals').textContent = stats.pending_approvals;
        document.getElementById('rep-avg-hours').textContent = `${stats.average_completion_hours} hrs`;
        document.getElementById('rep-changes-req').textContent = stats.changes_requested;
        document.getElementById('rep-rejections').textContent = stats.rejected_memos;

        renderStatusPieChart('rep-status-chart', stats.memos_by_status);
        renderBarChart('rep-dept-chart', stats.memos_by_department.map(d => d.department), stats.memos_by_department.map(d => d.count), 'Memos by Department');
        renderBarChart('rep-cat-chart', stats.memos_by_category.map(c => c.category), stats.memos_by_category.map(c => c.count), 'Memos by Category', '#8b5cf6');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// -------------------------------------------------------------
// 12. AUDIT LOG VIEW
// -------------------------------------------------------------
async function renderAuditView() {
    const container = document.getElementById('audit-view');
    container.classList.remove('hidden');

    if (appState.user.role !== 'admin') {
        showToast('Admin privileges required', 'error');
        showView('dashboard');
        return;
    }

    try {
        const logs = await apiCall('/audit?limit=100');
        appState.auditLogs = logs;
        const list = document.getElementById('audit-logs-list');

        if (logs.length === 0) {
            list.innerHTML = `<div class="p-8 text-center text-slate-500 text-sm">No audit logs recorded yet.</div>`;
        } else {
            list.innerHTML = logs.map(l => `
                <tr class="border-b border-slate-200 hover:bg-slate-50 text-xs">
                    <td class="px-4 py-3 font-mono text-slate-400 whitespace-nowrap">${new Date(l.created_at).toLocaleString()}</td>
                    <td class="px-4 py-3 font-bold text-slate-800 whitespace-nowrap">${l.user ? l.user.full_name : 'System'}</td>
                    <td class="px-4 py-3"><span class="px-2 py-0.5 rounded font-bold text-[10px] bg-indigo-100 text-indigo-800">${l.event_type}</span></td>
                    <td class="px-4 py-3 text-slate-500">${l.object_type} #${l.object_id || ''}</td>
                    <td class="px-4 py-3 text-slate-700">${l.description}</td>
                </tr>
            `).join('');
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// -------------------------------------------------------------
// 13. NOTIFICATIONS ENGINE
// -------------------------------------------------------------
async function fetchUnreadCount() {
    try {
        const res = await apiCall('/notifications/unread-count');
        appState.unreadCount = res.unread_count;
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.textContent = res.unread_count;
            badge.style.display = res.unread_count > 0 ? 'inline-flex' : 'none';
        }
    } catch (e) {}
}

async function toggleNotificationsDropdown() {
    const dropdown = document.getElementById('notifications-dropdown');
    const isHidden = dropdown.classList.contains('hidden');
    
    if (isHidden) {
        dropdown.classList.remove('hidden');
        try {
            const notifs = await apiCall('/notifications');
            appState.notifications = notifs;
            const list = document.getElementById('notifications-items-list');

            if (notifs.length === 0) {
                list.innerHTML = '<div class="p-4 text-center text-xs text-slate-400">No notifications.</div>';
            } else {
                list.innerHTML = notifs.map(n => `
                    <div onclick="handleNotificationClick(${n.id}, ${n.memo_id})" class="p-3 border-b border-slate-100 hover:bg-slate-50 cursor-pointer ${n.is_read ? 'opacity-70' : 'bg-indigo-50/40 font-semibold'} text-xs">
                        <div class="flex items-center justify-between">
                            <span class="text-indigo-900">${n.title}</span>
                            <span class="text-[10px] text-slate-400 font-normal">${new Date(n.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
                        </div>
                        <p class="text-slate-600 text-[11px] mt-0.5 font-normal">${n.message}</p>
                    </div>
                `).join('');
            }
        } catch (e) {}
    } else {
        dropdown.classList.add('hidden');
    }
}

async function handleNotificationClick(notifId, memoId) {
    try {
        await apiCall(`/notifications/${notifId}/read`, { method: 'PUT' });
        fetchUnreadCount();
        document.getElementById('notifications-dropdown').classList.add('hidden');
        if (memoId) {
            showView('memo-detail', memoId);
        }
    } catch (e) {}
}

async function markAllNotificationsRead() {
    try {
        await apiCall('/notifications/mark-all-read', { method: 'POST' });
        fetchUnreadCount();
        toggleNotificationsDropdown();
    } catch (e) {}
}

// -------------------------------------------------------------
// UI HELPERS & CHART UTILITIES
// -------------------------------------------------------------
function createMemoCardHTML(memo, type) {
    const isUrgent = memo.priority === 'Urgent';
    const authorName = memo.author?.full_name || 'Author';
    const deptName = memo.department?.name || 'General';

    return `
        <div onclick="showView('memo-detail', ${memo.id})" class="p-4 bg-white border border-slate-200 hover:border-indigo-300 hover:shadow-md rounded-xl cursor-pointer transition flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-3">
            <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                    <span class="font-mono text-xs font-bold text-indigo-700">${memo.memo_number}</span>
                    <span class="px-2 py-0.5 text-[10px] font-bold rounded-full ${getStatusBadgeClass(memo.status)}">${memo.status}</span>
                    <span class="px-2 py-0.5 text-[10px] font-semibold rounded ${getPriorityBadgeClass(memo.priority)}">${memo.priority}</span>
                </div>
                <h4 class="font-bold text-slate-800 text-sm hover:text-indigo-600">${memo.title}</h4>
                <div class="text-xs text-slate-500 mt-1 flex items-center gap-3">
                    <span>From: <b>${authorName}</b></span>
                    <span>Dept: <b>${deptName}</b></span>
                    <span>Submitted: <b>${new Date(memo.created_at).toLocaleDateString()}</b></span>
                </div>
            </div>
            <div class="flex items-center gap-3 flex-shrink-0">
                ${memo.current_assignee ? `
                    <div class="text-right text-xs">
                        <div class="text-[10px] text-slate-400 uppercase font-semibold">Current Turn</div>
                        <div class="font-bold text-amber-700">${memo.current_assignee.full_name}</div>
                    </div>
                ` : ''}
                <div class="w-8 h-8 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center hover:bg-indigo-600 hover:text-white transition">
                    <i data-lucide="chevron-right" class="w-4 h-4"></i>
                </div>
            </div>
        </div>
    `;
}

function getStatusBadgeClass(status) {
    switch (status) {
        case 'Approved': return 'bg-emerald-100 text-emerald-800';
        case 'Rejected': return 'bg-rose-100 text-rose-800';
        case 'Pending Approval': return 'bg-amber-100 text-amber-800';
        case 'Pending Review': return 'bg-blue-100 text-blue-800';
        case 'Changes Requested': return 'bg-purple-100 text-purple-800';
        case 'Draft': return 'bg-slate-100 text-slate-700';
        default: return 'bg-slate-100 text-slate-800';
    }
}

function getPriorityBadgeClass(priority) {
    switch (priority) {
        case 'Urgent': return 'bg-rose-50 text-rose-700 border border-rose-200';
        case 'High': return 'bg-amber-50 text-amber-700 border border-amber-200';
        default: return 'bg-slate-100 text-slate-600';
    }
}

function renderStatusPieChart(canvasId, statusData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;

    if (appState.charts[canvasId]) {
        appState.charts[canvasId].destroy();
    }

    const labels = statusData.map(s => s.status);
    const counts = statusData.map(s => s.count);

    appState.charts[canvasId] = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: counts,
                backgroundColor: ['#10b981', '#f59e0b', '#3b82f6', '#8b5cf6', '#ef4444', '#64748b']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
            }
        }
    });
}

function renderBarChart(canvasId, labels, data, label, color = '#3b82f6') {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;

    if (appState.charts[canvasId]) {
        appState.charts[canvasId].destroy();
    }

    appState.charts[canvasId] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label,
                data,
                backgroundColor: color,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 } }
            }
        }
    });
}
