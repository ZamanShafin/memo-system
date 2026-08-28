/**
 * Inter-Office Memo Management System - Frontend SPA Engine
 * CSE226 Foundations of Vibe Coding (North South University)
 */

const API_BASE = '/api/v1';

const DEFAULT_DEMO_ACCOUNTS = [
    {
        org_name: "Acme Corporation",
        org_code: "ACME",
        users: [
            { id: 1, full_name: "Sarah Jenkins", email: "admin@acmecorp.com", designation: "Chief Operating Officer", role: "admin", department: "Executive Operations" },
            { id: 5, full_name: "Eleanor Vance", email: "ceo@acmecorp.com", designation: "Chief Executive Officer (CEO)", role: "user", department: "Executive Operations" },
            { id: 3, full_name: "Rachel Green", email: "finance.mgr@acmecorp.com", designation: "Chief Financial Manager", role: "user", department: "Finance & Accounts" },
            { id: 4, full_name: "Marcus Sterling", email: "director@acmecorp.com", designation: "Director of Operations", role: "user", department: "Operations" },
            { id: 2, full_name: "David Vance", email: "head.eng@acmecorp.com", designation: "VP of Engineering", role: "user", department: "Engineering & IT" },
            { id: 6, full_name: "Alex Morgan", email: "alex.morgan@acmecorp.com", designation: "Senior Software Engineer / Team Lead", role: "user", department: "Engineering & IT" },
            { id: 7, full_name: "Jessica Taylor", email: "jessica.taylor@acmecorp.com", designation: "Lead Product Designer", role: "user", department: "Product Strategy" }
        ]
    },
    {
        org_name: "Nexus Global Group",
        org_code: "NEXUS",
        users: [
            { id: 8, full_name: "Jonathan Hayes", email: "admin@nexusgroup.com", designation: "Managing Director", role: "admin", department: "Corporate Strategy" },
            { id: 9, full_name: "Victoria Price", email: "lead.analyst@nexusgroup.com", designation: "Principal Financial Analyst", role: "user", department: "Financial Advisory" }
        ]
    }
];

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
    demoAccounts: DEFAULT_DEMO_ACCOUNTS,
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

function clearUserDataAndDOM() {
    // 1. Purge all cached user-specific data from appState
    appState.inboxMemos = [];
    appState.sentMemos = [];
    appState.draftMemos = [];
    appState.completedMemos = [];
    appState.searchResults = [];
    appState.notifications = [];
    appState.unreadCount = 0;
    appState.auditLogs = [];
    appState.reportsData = null;
    appState.selectedMemoId = null;
    appState.selectedVersion = null;

    // 2. Clear all list containers and UI elements across all views immediately
    const containerIds = [
        'dash-inbox-list',
        'dash-sent-list',
        'inbox-memos-list',
        'sent-memos-list',
        'draft-memos-list',
        'completed-memos-list',
        'search-results-container',
        'admin-users-table-container',
        'admin-depts-table-container',
        'admin-cats-table-container',
        'admin-tmpls-table-container',
        'audit-logs-list',
        'notifications-list',
        'delegations-list-container'
    ];

    containerIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = '';
    });

    // 3. Clear metric labels & KPI counters
    const countIds = [
        'stat-inbox-count',
        'stat-sent-count',
        'stat-completed-count',
        'stat-urgent-count',
        'search-count-label',
        'notif-badge',
        'rep-total-memos',
        'rep-pending-approvals',
        'rep-avg-hours',
        'rep-changes-req',
        'rep-rejections'
    ];
    countIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            if (id === 'notif-badge') el.classList.add('hidden');
            else el.textContent = '—';
        }
    });

    // 4. Destroy existing Chart instances
    Object.keys(appState.charts).forEach(key => {
        try {
            if (appState.charts[key]) appState.charts[key].destroy();
        } catch (e) {}
    });
    appState.charts = {};

    // 5. Hide any open modals & dropdowns
    const modals = [
        'workflow-action-modal',
        'manage-steps-modal',
        'new-delegation-modal',
        'dept-modal',
        'user-modal',
        'cat-modal',
        'notifications-dropdown',
        'demo-switcher-menu'
    ];
    modals.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });
}

function showAppLoader(title = 'Syncing Enterprise Workspace', subtitle = 'Pre-loading departments, inboxes, and sequential workflows...') {
    const loader = document.getElementById('app-loader-screen');
    if (!loader) return;
    const titleEl = document.getElementById('app-loader-title');
    const subtitleEl = document.getElementById('app-loader-subtitle');
    if (titleEl) titleEl.textContent = title;
    if (subtitleEl) subtitleEl.textContent = subtitle;
    loader.classList.remove('hidden', 'opacity-0');
    loader.style.display = 'flex';
    if (window.lucide) lucide.createIcons();
}

function hideAppLoader() {
    const loader = document.getElementById('app-loader-screen');
    if (!loader) return;
    loader.classList.add('opacity-0');
    setTimeout(() => {
        loader.classList.add('hidden');
        loader.style.display = 'none';
    }, 250);
}

async function setupApp(showLoading = true) {
    if (showLoading) {
        showAppLoader(`Connecting to ${appState.organization?.name || 'Workspace'}`, 'Pre-loading departments, inboxes, and sequential workflows...');
    }
    
    // Immediately switch to dashboard before exposing view to eliminate previous view residue
    showView('dashboard');
    updateHeaderUI();
    
    // Fetch fresh user-scoped data bundle
    await loadInitialData();

    // Fast render current dashboard
    updateDashboardDOM();

    if (showLoading) {
        setTimeout(hideAppLoader, 200);
    }
    if (window.lucide) lucide.createIcons();
}

function toggleDemoSwitcherMenu(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const menu = document.getElementById('demo-switcher-menu');
    if (!menu) return;
    const isHidden = menu.classList.contains('hidden');
    
    // Close other dropdowns
    const notifMenu = document.getElementById('notifications-dropdown');
    if (notifMenu) notifMenu.classList.add('hidden');

    if (isHidden) {
        renderDemoSwitcher(appState.demoAccounts);
        menu.classList.remove('hidden');
    } else {
        menu.classList.add('hidden');
    }
}

// Global click-away listener for dropdowns
document.addEventListener('click', (e) => {
    const demoMenu = document.getElementById('demo-switcher-menu');
    const demoBtn = document.getElementById('btn-demo-switcher');
    if (demoMenu && !demoMenu.classList.contains('hidden')) {
        if (!demoMenu.contains(e.target) && (!demoBtn || !demoBtn.contains(e.target))) {
            demoMenu.classList.add('hidden');
        }
    }
    const notifMenu = document.getElementById('notifications-dropdown');
    const notifBtn = document.getElementById('btn-notifications-bell');
    if (notifMenu && !notifMenu.classList.contains('hidden')) {
        if (!notifMenu.contains(e.target) && (!notifBtn || !notifBtn.contains(e.target))) {
            notifMenu.classList.add('hidden');
        }
    }
});

async function loadDemoAccounts() {
    try {
        const data = await apiCall('/demo/accounts');
        if (data && data.length > 0) {
            appState.demoAccounts = data;
            sessionStorage.setItem('memo_demo_accounts', JSON.stringify(data));
            renderDemoSwitcher(data);
        }
    } catch (e) {
        // Fallback to DEFAULT_DEMO_ACCOUNTS
        renderDemoSwitcher(DEFAULT_DEMO_ACCOUNTS);
    }
}

function renderDemoSwitcher(demoData) {
    const container = document.getElementById('demo-switcher-dropdown');
    if (!container) return;
    container.classList.remove('hidden');

    const accounts = (demoData && demoData.length > 0) ? demoData : (appState.demoAccounts || DEFAULT_DEMO_ACCOUNTS);

    let html = '';
    accounts.forEach(org => {
        html += `<div class="px-3 py-1.5 text-xs font-bold text-slate-400 uppercase tracking-wider bg-slate-100 dark:bg-slate-800">${org.org_name} (${org.org_code})</div>`;
        (org.users || []).forEach(u => {
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
    // 0. Close the demo switcher popup immediately
    const demoMenu = document.getElementById('demo-switcher-menu');
    if (demoMenu) demoMenu.classList.add('hidden');

    // 1. Cover screen immediately with synchronous solid loader
    showAppLoader('Switching Demo Persona...', 'Purging workspace and authenticating role...');
    
    // 2. Wipe all User A's data from client memory and DOM immediately
    clearUserDataAndDOM();

    try {
        const res = await apiCall(`/demo/quick-login/${userId}`, { method: 'POST' });
        setSession(res.access_token, res.user, res.organization);
        showToast(`Switched persona to ${res.user.full_name} (${res.organization.name})`, 'success');
        await setupApp(true);
    } catch (e) {
        hideAppLoader();
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
    clearUserDataAndDOM();
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
    const submitBtn = isDraft ? document.getElementById('btn-save-draft') : document.getElementById('btn-submit-workflow');
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

    let origHtml = '';
    if (submitBtn) {
        origHtml = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-1 mr-1.5 h-4 w-4 text-current inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> ${isDraft ? 'Saving Draft...' : 'Submitting to Workflow...'}</span>`;
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
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = origHtml;
        }
    }
}

// -------------------------------------------------------------
// 7. MEMO DETAIL & WORKFLOW TIMELINE VIEW
// -------------------------------------------------------------
function populateMemoDOM(memo) {
    if (!memo) return;
    appState.selectedMemoId = memo.id;

    // Render Header & Badges
    document.getElementById('detail-memo-number').textContent = memo.memo_number || '';
    document.getElementById('detail-memo-title').textContent = memo.title || '';
    
    const statusBadge = document.getElementById('detail-memo-status');
    statusBadge.textContent = memo.status || '';
    statusBadge.className = `px-3 py-1 text-xs font-bold rounded-full ${getStatusBadgeClass(memo.status)}`;

    const priorityBadge = document.getElementById('detail-memo-priority');
    priorityBadge.textContent = memo.priority || 'Normal';
    priorityBadge.className = `px-2.5 py-0.5 text-xs font-semibold rounded ${getPriorityBadgeClass(memo.priority)}`;

    document.getElementById('detail-memo-author').textContent = `${memo.author?.full_name || 'Staff'} (${memo.author?.designation || 'Staff'})`;
    document.getElementById('detail-memo-dept').textContent = memo.department ? memo.department.name : 'General';
    document.getElementById('detail-memo-category').textContent = memo.category ? memo.category.name : 'Uncategorized';
    document.getElementById('detail-memo-date').textContent = new Date(memo.created_at || Date.now()).toLocaleString();

    // Render Rich Content Body
    document.getElementById('detail-memo-body').innerHTML = memo.body || '';

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

    if (window.lucide) lucide.createIcons();
}

async function renderMemoDetailView(memoId) {
    const container = document.getElementById('memo-detail-view');
    container.classList.remove('hidden');

    // 1. Instant render from memory cache (0ms!)
    const allKnownMemos = [
        ...(appState.inboxMemos || []),
        ...(appState.sentMemos || []),
        ...(appState.completedMemos || []),
        ...(appState.draftMemos || [])
    ];
    const cachedMemo = allKnownMemos.find(m => m.id == memoId);
    if (cachedMemo) {
        populateMemoDOM(cachedMemo);
    }

    // 2. Background sync
    try {
        const memo = await apiCall(`/memos/${memoId}`);
        populateMemoDOM(memo);
    } catch (e) {
        if (!cachedMemo) {
            showToast(e.message, 'error');
            showView('dashboard');
        }
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

    // Check if memo is Draft and user is author or admin -> Show Submit to Workflow banner
    if (memo.status === 'Draft' && (isAuthor || appState.user.role === 'admin')) {
        actionContainer.innerHTML = `
            <div class="p-5 bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200 rounded-2xl mb-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                    <h4 class="font-black text-indigo-950 text-sm">Draft Memorandum</h4>
                    <p class="text-xs text-indigo-800 mt-0.5 font-medium">This memo is currently saved as a draft. Click below to initiate sequential workflow review.</p>
                </div>
                <button id="btn-submit-draft-workflow" onclick="submitDraftToWorkflow(${memo.id})" class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition shrink-0">
                    <i data-lucide="send" class="w-4 h-4"></i> Submit to Workflow
                </button>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
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
                        <p class="text-xs text-amber-800 mt-0.5 font-medium">As <b>${activeStep.role_name}</b>, choose an action below or dynamically route to colleagues.</p>
                    </div>
                    <div class="flex items-center gap-2 flex-wrap">
                        <button onclick="openActionModal('approve', ${memo.id})" class="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition">
                            <i data-lucide="check-circle" class="w-4 h-4"></i> Approve Step
                        </button>
                        <button onclick="openActionModal('approve_insert', ${memo.id})" class="px-3.5 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition">
                            <i data-lucide="user-plus" class="w-4 h-4"></i> Approve & Add Reviewer
                        </button>
                        <button onclick="openActionModal('reassign', ${memo.id})" class="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition">
                            <i data-lucide="corner-up-right" class="w-4 h-4"></i> Decline & Reroute
                        </button>
                        <button onclick="openActionModal('request_changes', ${memo.id})" class="px-3.5 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition">
                            <i data-lucide="edit-3" class="w-4 h-4"></i> Request Changes
                        </button>
                        <button onclick="openActionModal('reject', ${memo.id})" class="px-3.5 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition">
                            <i data-lucide="x-circle" class="w-4 h-4"></i> Reject
                        </button>
                        <button onclick="openManageStepsModal(${memo.id})" class="px-3 py-2 bg-slate-700 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition">
                            <i data-lucide="git-merge" class="w-4 h-4"></i> Modify Steps
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
    const descEl = document.getElementById('action-modal-desc');
    const commentEl = document.getElementById('action-modal-comment');
    const submitBtn = document.getElementById('action-modal-submit-btn');
    const reassignBox = document.getElementById('action-modal-reassign-container');
    const insertBox = document.getElementById('action-modal-insert-container');
    const reassignSelect = document.getElementById('action-modal-reassign-user');
    const insertSelect = document.getElementById('action-modal-insert-user');

    commentEl.value = '';
    reassignBox.classList.add('hidden');
    insertBox.classList.add('hidden');

    // Populate user selects
    const userOptions = (appState.orgUsers || [])
        .filter(u => u.id !== appState.user.id)
        .map(u => `<option value="${u.id}">${u.full_name} (${u.designation || u.role})</option>`)
        .join('');

    if (actionType === 'approve') {
        titleEl.textContent = 'Approve Memo Step';
        descEl.textContent = 'Sign off and advance this memo to the next designated step in sequence.';
        submitBtn.className = 'px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl';
        submitBtn.textContent = 'Confirm Approval';
    } else if (actionType === 'approve_insert') {
        titleEl.textContent = 'Approve & Insert Intermediate Reviewer';
        descEl.textContent = 'Endorse this memo and route to a colleague for additional review before downstream steps.';
        insertBox.classList.remove('hidden');
        insertSelect.innerHTML = userOptions;
        document.getElementById('action-modal-insert-role').value = 'Specialist Sign-off';
        submitBtn.className = 'px-5 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-xl';
        submitBtn.textContent = 'Approve & Route to Colleague';
    } else if (actionType === 'reassign') {
        titleEl.textContent = 'Decline & Reroute Step to Colleague';
        descEl.textContent = 'Decline taking action and reassign this exact review step to another person.';
        reassignBox.classList.remove('hidden');
        reassignSelect.innerHTML = userOptions;
        submitBtn.className = 'px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl';
        submitBtn.textContent = 'Confirm Reassignment';
    } else if (actionType === 'request_changes') {
        titleEl.textContent = 'Request Changes / Revisions';
        descEl.textContent = 'Send memo back to the author with required revision instructions.';
        submitBtn.className = 'px-5 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl';
        submitBtn.textContent = 'Send Change Request';
    } else if (actionType === 'reject') {
        titleEl.textContent = 'Reject Memo';
        descEl.textContent = 'Provide a mandatory reason and terminate this memo workflow.';
        submitBtn.className = 'px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl';
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
    const submitBtn = document.getElementById('action-modal-submit-btn');

    if ((action === 'reject' || action === 'request_changes') && !comment) {
        showToast('Comment/reason is required for this action', 'warning');
        return;
    }

    const payload = { action, comment };

    if (action === 'reassign') {
        const targetUserId = parseInt(document.getElementById('action-modal-reassign-user').value);
        if (!targetUserId) {
            showToast('Please select a colleague to reroute this memo to', 'warning');
            return;
        }
        payload.reassign_to_user_id = targetUserId;
    } else if (action === 'approve_insert') {
        const targetUserId = parseInt(document.getElementById('action-modal-insert-user').value);
        const roleName = document.getElementById('action-modal-insert-role').value.trim() || 'Specialist Review';
        const stepType = document.getElementById('action-modal-insert-type').value || 'approval';
        if (!targetUserId) {
            showToast('Please select an intermediate reviewer', 'warning');
            return;
        }
        payload.insert_step = {
            assigned_user_id: targetUserId,
            role_name: roleName,
            step_type: stepType
        };
    }

    const origText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-1 mr-1 h-3.5 w-3.5 text-white inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Processing...</span>`;

    try {
        await apiCall(`/workflow/${memoId}/action`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        showToast(`Workflow action executed successfully!`, 'success');
        closeActionModal();

        // Immediately update cached inboxes
        if (appState.inboxMemos) {
            appState.inboxMemos = appState.inboxMemos.filter(m => m.id != memoId);
        }
        
        // Re-render detail view directly
        renderMemoDetailView(memoId);
        
        // Refresh background cache
        loadInitialData();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origText;
    }
}

// -------------------------------------------------------------
// DYNAMIC WORKFLOW STEPS MODIFIER
// -------------------------------------------------------------
let currentEditingDownstreamSteps = [];

async function openManageStepsModal(memoId) {
    const modal = document.getElementById('manage-steps-modal');
    modal.classList.remove('hidden');
    modal.setAttribute('data-memo-id', memoId);

    // Fetch live memo
    try {
        const memo = await apiCall(`/memos/${memoId}`);
        const downstream = (memo.workflow_steps || []).filter(s => s.step_index > memo.current_step_index);
        currentEditingDownstreamSteps = downstream.map(s => ({
            role_name: s.role_name,
            step_type: s.step_type,
            assigned_user_id: s.assigned_user_id
        }));
        renderManageStepsList();
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function closeManageStepsModal() {
    document.getElementById('manage-steps-modal').classList.add('hidden');
}

function renderManageStepsList() {
    const container = document.getElementById('manage-steps-list');
    if (!container) return;

    if (currentEditingDownstreamSteps.length === 0) {
        container.innerHTML = `<div class="p-4 bg-slate-50 border border-slate-200 rounded-xl text-center text-xs text-slate-500">No upcoming downstream steps. Once this step is approved, the memo will reach final completion.</div>`;
        return;
    }

    const userOptions = (appState.orgUsers || []).map(u => `<option value="${u.id}">${u.full_name} (${u.designation || u.role})</option>`).join('');

    container.innerHTML = currentEditingDownstreamSteps.map((step, idx) => `
        <div class="p-3 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-between gap-3 text-xs">
            <div class="flex items-center gap-2 flex-1">
                <span class="w-6 h-6 rounded-full bg-indigo-100 text-indigo-800 font-bold flex items-center justify-center text-[10px] shrink-0">${idx + 1}</span>
                <input type="text" value="${step.role_name}" onchange="currentEditingDownstreamSteps[${idx}].role_name = this.value" placeholder="Role Name" class="px-2.5 py-1.5 text-xs border border-slate-300 rounded-lg w-1/3">
                <select onchange="currentEditingDownstreamSteps[${idx}].assigned_user_id = parseInt(this.value)" class="px-2 py-1.5 text-xs border border-slate-300 rounded-lg flex-1 bg-white">
                    ${(appState.orgUsers || []).map(u => `<option value="${u.id}" ${u.id === step.assigned_user_id ? 'selected' : ''}>${u.full_name}</option>`).join('')}
                </select>
                <select onchange="currentEditingDownstreamSteps[${idx}].step_type = this.value" class="px-2 py-1.5 text-xs border border-slate-300 rounded-lg bg-white w-24">
                    <option value="approval" ${step.step_type === 'approval' ? 'selected' : ''}>Approval</option>
                    <option value="review" ${step.step_type === 'review' ? 'selected' : ''}>Review</option>
                </select>
            </div>
            <button onclick="removeDynamicStepRow(${idx})" class="p-1.5 text-rose-500 hover:bg-rose-50 rounded-lg transition" title="Remove Step">
                <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
        </div>
    `).join('');
    if (window.lucide) lucide.createIcons();
}

function addDynamicStepRow() {
    const defaultUser = appState.orgUsers && appState.orgUsers.length > 0 ? appState.orgUsers[0].id : 1;
    currentEditingDownstreamSteps.push({
        role_name: 'Additional Reviewer',
        step_type: 'approval',
        assigned_user_id: defaultUser
    });
    renderManageStepsList();
}

function removeDynamicStepRow(idx) {
    currentEditingDownstreamSteps.splice(idx, 1);
    renderManageStepsList();
}

async function saveManagedSteps() {
    const modal = document.getElementById('manage-steps-modal');
    const memoId = modal.getAttribute('data-memo-id');

    try {
        await apiCall(`/workflow/${memoId}/steps`, {
            method: 'PUT',
            body: JSON.stringify({ steps: currentEditingDownstreamSteps })
        });
        showToast('Workflow steps updated successfully!', 'success');
        closeManageStepsModal();
        renderMemoDetailView(memoId);
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function submitDraftToWorkflow(memoId) {
    const btn = document.getElementById('btn-submit-draft-workflow');
    let origHtml = '';
    if (btn) {
        origHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-1 mr-1.5 h-3.5 w-3.5 text-white inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Submitting to Workflow...</span>`;
    }
    try {
        await apiCall(`/memos/${memoId}/submit`, { method: 'POST' });
        showToast('Memo successfully submitted to workflow!', 'success');
        renderMemoDetailView(memoId);
        loadInitialData();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    }
}

async function submitResubmission(memoId) {
    const title = document.getElementById('resubmit-title').value.trim();
    const body = document.getElementById('resubmit-body').value.trim();
    const summary = document.getElementById('resubmit-summary').value.trim();
    const btn = document.getElementById('btn-submit-resubmit');

    if (!title || !body) {
        showToast('Title and content cannot be blank', 'warning');
        return;
    }

    let origHtml = '';
    if (btn) {
        origHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-1 mr-1.5 h-3.5 w-3.5 text-white inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Submitting Revisions...</span>`;
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
        loadInitialData();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
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
    const btn = document.getElementById('btn-post-comment');
    const text = input.value.trim();
    if (!text) {
        showToast('Please type a comment first', 'warning');
        return;
    }

    let origHtml = '';
    if (btn) {
        origHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-1 mr-1.5 h-3.5 w-3.5 text-white inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Posting...</span>`;
    }

    try {
        await apiCall(`/memos/${memoId}/comments`, {
            method: 'POST',
            body: JSON.stringify({ comment_type: 'general', text })
        });
        input.value = '';
        renderMemoDetailView(memoId);
        showToast('Comment posted successfully!', 'success');
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
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
    const catSelect = document.getElementById('search-category');
    if (catSelect) {
        catSelect.innerHTML = '<option value="">All Categories</option>' + (appState.categories || []).map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    }

    executeMemoSearch();
}

async function executeMemoSearch() {
    const q = document.getElementById('search-query')?.value.trim() || '';
    const status = document.getElementById('search-status')?.value || '';
    const priority = document.getElementById('search-priority')?.value || '';
    const catId = document.getElementById('search-category')?.value || '';
    const btn = document.getElementById('btn-search-apply');

    const params = new URLSearchParams();
    if (q) params.append('q', q);
    if (status && status !== 'All') params.append('status', status);
    if (priority && priority !== 'All') params.append('priority', priority);
    if (catId) params.append('category_id', catId);

    const list = document.getElementById('search-results-container');
    const countLabel = document.getElementById('search-count-label');
    if (!list) return;

    let origHtml = '';
    if (btn) {
        origHtml = btn.innerHTML;
        btn.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-1 mr-1 h-3.5 w-3.5 text-white inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Filtering...</span>`;
    }

    try {
        const results = await apiCall(`/memos/all?${params.toString()}`);
        appState.searchResults = results;
        if (countLabel) countLabel.textContent = `${results.length} memos found`;

        if (results.length === 0) {
            list.innerHTML = `
                <div class="bg-white rounded-3xl p-12 text-center text-slate-500 border border-slate-200">
                    <div class="p-3 bg-slate-100 rounded-2xl w-fit mx-auto mb-3 text-slate-400">
                        <i data-lucide="search-x" class="w-8 h-8"></i>
                    </div>
                    <h3 class="text-sm font-bold text-slate-800">No matching memos found</h3>
                    <p class="text-xs text-slate-400 mt-1 max-w-md mx-auto">No memos matched your query. Note: In compliance with governance rules, users only see memos they authored or are part of in the sequential workflow.</p>
                </div>
            `;
        } else {
            list.innerHTML = results.map(m => createMemoCardHTML(m, 'search')).join('');
        }
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (btn) {
            btn.innerHTML = origHtml;
        }
    }
}

// -------------------------------------------------------------
// 9. DELEGATIONS VIEW
// -------------------------------------------------------------
async function renderDelegationsView() {
    const container = document.getElementById('delegations-view');
    container.classList.remove('hidden');

    const userSelect = document.getElementById('del-delegatee-select') || document.getElementById('delegation-user-select');
    if (userSelect) {
        if (!appState.orgUsers || appState.orgUsers.length === 0) {
            try {
                appState.orgUsers = await apiCall('/admin/users');
            } catch (e) {
                // If standard user, fetch org members
                try {
                    const depts = await apiCall('/admin/departments');
                    appState.departments = depts;
                } catch (err) {}
            }
        }
        const eligibleUsers = (appState.orgUsers || []).filter(u => u.id !== appState.user.id && u.is_active);
        userSelect.innerHTML = '<option value="">Select Colleague</option>' + eligibleUsers.map(u => `<option value="${u.id}">${u.full_name} (${u.designation || u.role})</option>`).join('');
    }

    try {
        const delegations = await apiCall('/delegations');
        appState.delegations = delegations;
        const list = document.getElementById('delegations-list-container') || document.getElementById('delegations-list');
        if (!list) return;

        if (delegations.length === 0) {
            list.innerHTML = `<div class="p-8 bg-white border border-slate-200 rounded-3xl text-center text-slate-500 text-xs">No active or historical delegation rules found. Click "+ New Delegation Rule" to designate a colleague.</div>`;
        } else {
            list.innerHTML = delegations.map(d => {
                const isDelegator = d.delegator_id === appState.user.id;
                const statusBadge = d.is_active ? '<span class="px-2.5 py-0.5 text-[10px] font-bold bg-emerald-100 text-emerald-800 rounded-full">Active</span>' : '<span class="px-2.5 py-0.5 text-[10px] font-bold bg-slate-100 text-slate-600 rounded-full">Inactive</span>';
                
                return `
                    <div class="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm mb-3 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                        <div>
                            <div class="flex items-center gap-2">
                                <span class="font-bold text-slate-800 text-sm">${isDelegator ? `Delegated to: <b class="text-indigo-600">${d.delegatee?.full_name}</b>` : `Delegated from: <b class="text-indigo-600">${d.delegator?.full_name}</b>`}</span>
                                ${statusBadge}
                            </div>
                            <div class="text-xs text-slate-500 mt-1">
                                Effective Period: <b>${new Date(d.start_date).toLocaleDateString()}</b> to <b>${new Date(d.end_date).toLocaleDateString()}</b>
                            </div>
                            ${d.reason ? `<div class="text-xs text-slate-600 mt-1 bg-slate-50 px-2 py-1 rounded-md border border-slate-100 inline-block">Reason: "${d.reason}"</div>` : ''}
                        </div>
                        ${isDelegator ? `
                            <button onclick="toggleDelegationStatus(${d.id}, ${!d.is_active})" class="px-3.5 py-1.5 text-xs font-bold rounded-xl transition ${d.is_active ? 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'}">
                                ${d.is_active ? 'Revoke Delegation' : 'Reactivate'}
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

async function handleCreateDelegationForm(e) {
    if (e) e.preventDefault();
    const delegateeId = document.getElementById('del-delegatee-select')?.value || document.getElementById('delegation-user-select')?.value;
    const startDate = document.getElementById('del-start-date')?.value || document.getElementById('delegation-start-date')?.value;
    const endDate = document.getElementById('del-end-date')?.value || document.getElementById('delegation-end-date')?.value;
    const reason = (document.getElementById('del-reason')?.value || document.getElementById('delegation-reason')?.value || '').trim();

    if (!delegateeId || !startDate || !endDate) {
        showToast('Please select a colleague and specify start & end dates', 'warning');
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
        showToast('Delegation rule created successfully!', 'success');
        const modal = document.getElementById('new-delegation-modal');
        if (modal) modal.classList.add('hidden');
        renderDelegationsView();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function createDelegationSubmit() {
    return handleCreateDelegationForm(null);
}

async function toggleDelegationStatus(delegationId, isActive) {
    try {
        await apiCall(`/delegations/${delegationId}`, {
            method: 'PUT',
            body: JSON.stringify({ is_active: isActive })
        });
        showToast(`Delegation ${isActive ? 'reactivated' : 'revoked'}`, 'info');
        renderDelegationsView();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// -------------------------------------------------------------
// 10. ADMIN CONSOLE VIEW & DEPARTMENT MANAGEMENT
// -------------------------------------------------------------
function switchAdminTab(tabName) {
    const tabs = ['users', 'departments', 'categories', 'templates'];
    tabs.forEach(t => {
        const panel = document.getElementById(`admin-${t}-panel`);
        const btn = document.getElementById(`admin-tab-${t === 'departments' ? 'depts' : t === 'categories' ? 'cats' : t === 'templates' ? 'tmpls' : 'users'}-btn`);
        if (panel) {
            if (t === tabName) {
                panel.classList.remove('hidden');
            } else {
                panel.classList.add('hidden');
            }
        }
        if (btn) {
            if (t === tabName) {
                btn.className = 'p-4 bg-indigo-50 border-2 border-indigo-600 rounded-2xl font-black text-xs text-indigo-900 shadow-sm transition text-left';
            } else {
                btn.className = 'p-4 bg-white border border-slate-200 rounded-2xl font-bold text-xs text-slate-800 hover:border-indigo-500 transition text-left';
            }
        }
    });
}

async function renderAdminView() {
    const container = document.getElementById('admin-view');
    container.classList.remove('hidden');

    if (appState.user.role !== 'admin') {
        showToast('Admin privileges required', 'error');
        showView('dashboard');
        return;
    }

    switchAdminTab('users');
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
    const container = document.getElementById('admin-depts-table-container');
    if (!container) return;

    if (depts.length === 0) {
        container.innerHTML = `<div class="p-8 text-center text-slate-500 text-xs">No corporate departments defined yet. Click "+ Add Department" to create one.</div>`;
        return;
    }

    container.innerHTML = `
        <table class="w-full text-left text-xs border border-slate-200 rounded-2xl overflow-hidden">
            <thead class="bg-slate-50 text-slate-600 uppercase font-black text-[10px] border-b border-slate-200">
                <tr>
                    <th class="px-4 py-3">Department Name</th>
                    <th class="px-4 py-3">Description</th>
                    <th class="px-4 py-3">Assigned Staff</th>
                    <th class="px-4 py-3">Status</th>
                    <th class="px-4 py-3 text-right">Actions</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 bg-white">
                ${depts.map(d => `
                    <tr class="hover:bg-slate-50 transition">
                        <td class="px-4 py-3 font-bold text-slate-900">${d.name}</td>
                        <td class="px-4 py-3 text-slate-500 max-w-xs truncate">${d.description || '—'}</td>
                        <td class="px-4 py-3 font-semibold text-indigo-700">${d.user_count} members</td>
                        <td class="px-4 py-3">
                            <span class="px-2 py-0.5 text-[10px] font-bold rounded-md ${d.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}">
                                ${d.is_active ? 'Active' : 'Deactivated'}
                            </span>
                        </td>
                        <td class="px-4 py-3 text-right space-x-2">
                            <button onclick="showEditDeptModal(${d.id})" class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-lg text-[11px] transition">
                                Rename / Edit
                            </button>
                            <button onclick="toggleDeptActive(${d.id}, ${!d.is_active})" class="px-2.5 py-1 font-bold rounded-lg text-[11px] transition ${d.is_active ? 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'}">
                                ${d.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function showCreateDeptModal() {
    document.getElementById('dept-modal-id').value = '';
    document.getElementById('dept-modal-title').textContent = 'Add Corporate Department';
    document.getElementById('dept-modal-name').value = '';
    document.getElementById('dept-modal-desc').value = '';
    document.getElementById('dept-modal-status-row').classList.add('hidden');
    document.getElementById('dept-modal').classList.remove('hidden');
}

function showEditDeptModal(deptId) {
    const dept = appState.departments.find(d => d.id === deptId);
    if (!dept) return;
    document.getElementById('dept-modal-id').value = dept.id;
    document.getElementById('dept-modal-title').textContent = `Edit / Rename: ${dept.name}`;
    document.getElementById('dept-modal-name').value = dept.name;
    document.getElementById('dept-modal-desc').value = dept.description || '';
    document.getElementById('dept-modal-active').checked = dept.is_active;
    document.getElementById('dept-modal-status-row').classList.remove('hidden');
    document.getElementById('dept-modal').classList.remove('hidden');
}

function closeDeptModal() {
    document.getElementById('dept-modal').classList.add('hidden');
}

async function handleDeptFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('dept-modal-id').value;
    const name = document.getElementById('dept-modal-name').value.trim();
    const description = document.getElementById('dept-modal-desc').value.trim();
    const is_active = document.getElementById('dept-modal-active').checked;
    const btn = document.getElementById('btn-save-dept');

    if (!name) return;

    let origHtml = '';
    if (btn) {
        origHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-1 mr-1 h-3.5 w-3.5 text-white inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Saving...</span>`;
    }

    try {
        if (id) {
            await apiCall(`/admin/departments/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ name, description, is_active })
            });
            showToast('Department updated successfully!', 'success');
        } else {
            await apiCall('/admin/departments', {
                method: 'POST',
                body: JSON.stringify({ name, description })
            });
            showToast('Department created successfully!', 'success');
        }
        closeDeptModal();
        renderAdminDepartments();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    }
}

async function toggleDeptActive(deptId, newStatus) {
    try {
        await apiCall(`/admin/departments/${deptId}`, {
            method: 'PUT',
            body: JSON.stringify({ is_active: newStatus })
        });
        showToast(`Department ${newStatus ? 'activated' : 'deactivated'}`, 'info');
        renderAdminDepartments();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function renderAdminUsers() {
    const users = await apiCall('/admin/users');
    appState.orgUsers = users;
    const container = document.getElementById('admin-users-table-container');
    if (!container) return;

    // Populate user modal dept dropdown
    const deptSelect = document.getElementById('user-modal-dept');
    if (deptSelect) {
        deptSelect.innerHTML = '<option value="">No Department / General</option>' + (appState.departments || []).map(d => `<option value="${d.id}">${d.name}</option>`).join('');
    }

    if (users.length === 0) {
        container.innerHTML = `<div class="p-8 text-center text-slate-500 text-xs">No users found.</div>`;
        return;
    }

    container.innerHTML = `
        <table class="w-full text-left text-xs border border-slate-200 rounded-2xl overflow-hidden">
            <thead class="bg-slate-50 text-slate-600 uppercase font-black text-[10px] border-b border-slate-200">
                <tr>
                    <th class="px-4 py-3">Full Name & Email</th>
                    <th class="px-4 py-3">Designation</th>
                    <th class="px-4 py-3">Department</th>
                    <th class="px-4 py-3">Role</th>
                    <th class="px-4 py-3">Status</th>
                    <th class="px-4 py-3 text-right">Actions</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 bg-white">
                ${users.map(u => {
                    const dept = appState.departments.find(d => d.id === u.department_id);
                    return `
                        <tr class="hover:bg-slate-50 transition">
                            <td class="px-4 py-3">
                                <div class="font-bold text-slate-900">${u.full_name}</div>
                                <div class="text-slate-500 text-[11px]">${u.email}</div>
                            </td>
                            <td class="px-4 py-3 text-slate-700 font-medium">${u.designation || '—'}</td>
                            <td class="px-4 py-3">
                                <span class="px-2 py-0.5 text-[10px] font-semibold bg-indigo-50 text-indigo-700 rounded border border-indigo-100">
                                    ${dept ? dept.name : 'Unassigned'}
                                </span>
                            </td>
                            <td class="px-4 py-3">
                                <span class="uppercase text-[10px] font-black ${u.role === 'admin' ? 'text-amber-600' : 'text-slate-600'}">${u.role}</span>
                            </td>
                            <td class="px-4 py-3">
                                <span class="px-2 py-0.5 text-[10px] font-bold rounded-md ${u.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}">
                                    ${u.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </td>
                            <td class="px-4 py-3 text-right space-x-2">
                                <button onclick="showEditUserModal(${u.id})" class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-lg text-[11px] transition">
                                    Edit / Dept
                                </button>
                                <button onclick="toggleUserActive(${u.id}, ${!u.is_active})" class="px-2.5 py-1 font-bold rounded-lg text-[11px] transition ${u.is_active ? 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200' : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'}">
                                    ${u.is_active ? 'Deactivate' : 'Activate'}
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

function showCreateUserModal() {
    document.getElementById('user-modal-id').value = '';
    document.getElementById('user-modal-title').textContent = 'Add Organization User';
    document.getElementById('user-modal-name').value = '';
    document.getElementById('user-modal-email').value = '';
    document.getElementById('user-modal-designation').value = '';
    document.getElementById('user-modal-dept').value = '';
    document.getElementById('user-modal-role').value = 'user';
    document.getElementById('user-modal-pwd').value = '';
    document.getElementById('user-modal-pwd-label').textContent = 'Password *';
    document.getElementById('user-modal-pwd').required = true;
    document.getElementById('user-modal-status-row').classList.add('hidden');
    document.getElementById('user-modal').classList.remove('hidden');
}

function showEditUserModal(userId) {
    const user = appState.orgUsers.find(u => u.id === userId);
    if (!user) return;
    document.getElementById('user-modal-id').value = user.id;
    document.getElementById('user-modal-title').textContent = `Edit User: ${user.full_name}`;
    document.getElementById('user-modal-name').value = user.full_name;
    document.getElementById('user-modal-email').value = user.email;
    document.getElementById('user-modal-designation').value = user.designation || '';
    document.getElementById('user-modal-dept').value = user.department_id || '';
    document.getElementById('user-modal-role').value = user.role;
    document.getElementById('user-modal-pwd').value = '';
    document.getElementById('user-modal-pwd-label').textContent = 'New Password (leave blank to keep)';
    document.getElementById('user-modal-pwd').required = false;
    document.getElementById('user-modal-active').checked = user.is_active;
    document.getElementById('user-modal-status-row').classList.remove('hidden');
    document.getElementById('user-modal').classList.remove('hidden');
}

function closeUserModal() {
    document.getElementById('user-modal').classList.add('hidden');
}

async function handleUserFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('user-modal-id').value;
    const full_name = document.getElementById('user-modal-name').value.trim();
    const email = document.getElementById('user-modal-email').value.trim();
    const designation = document.getElementById('user-modal-designation').value.trim();
    const deptId = document.getElementById('user-modal-dept').value;
    const role = document.getElementById('user-modal-role').value;
    const password = document.getElementById('user-modal-pwd').value;
    const is_active = document.getElementById('user-modal-active').checked;
    const btn = document.getElementById('btn-save-user');

    if (!full_name || !email) return;

    let origHtml = '';
    if (btn) {
        origHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin -ml-1 mr-1 h-3.5 w-3.5 text-white inline" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Saving...</span>`;
    }

    try {
        if (id) {
            const payload = {
                full_name, email, designation, role, is_active,
                department_id: deptId ? parseInt(deptId) : null
            };
            if (password) payload.password = password;
            await apiCall(`/admin/users/${id}`, {
                method: 'PUT',
                body: JSON.stringify(payload)
            });
            showToast('User profile updated successfully!', 'success');
        } else {
            await apiCall('/admin/users', {
                method: 'POST',
                body: JSON.stringify({
                    full_name, email, designation, role, password, is_active: true,
                    department_id: deptId ? parseInt(deptId) : null
                })
            });
            showToast('User created successfully!', 'success');
        }
        closeUserModal();
        renderAdminUsers();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    }
}

async function toggleUserActive(userId, newStatus) {
    try {
        await apiCall(`/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify({ is_active: newStatus })
        });
        showToast(`User status updated to ${newStatus ? 'Active' : 'Inactive'}`, 'info');
        renderAdminUsers();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function renderAdminCategories() {
    const cats = await apiCall('/admin/categories');
    appState.categories = cats;
    const container = document.getElementById('admin-cats-table-container');
    if (!container) return;

    if (cats.length === 0) {
        container.innerHTML = `<div class="p-8 text-center text-slate-500 text-xs">No categories defined yet.</div>`;
        return;
    }

    container.innerHTML = `
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            ${cats.map(c => `
                <div class="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs flex items-start justify-between gap-3">
                    <div>
                        <div class="font-bold text-slate-900">${c.name}</div>
                        <div class="text-slate-500 text-[11px] mt-0.5">${c.description || 'No description provided.'}</div>
                    </div>
                    <span class="px-2 py-0.5 text-[10px] font-bold bg-indigo-50 text-indigo-700 rounded border border-indigo-100">Category</span>
                </div>
            `).join('')}
        </div>
    `;
}

function showCreateCatModal() {
    document.getElementById('cat-modal-name').value = '';
    document.getElementById('cat-modal-desc').value = '';
    document.getElementById('cat-modal').classList.remove('hidden');
}

async function handleCatFormSubmit(e) {
    e.preventDefault();
    const name = document.getElementById('cat-modal-name').value.trim();
    const desc = document.getElementById('cat-modal-desc').value.trim();
    if (!name) return;

    try {
        await apiCall('/admin/categories', {
            method: 'POST',
            body: JSON.stringify({ name, description: desc })
        });
        showToast('Category created successfully!', 'success');
        document.getElementById('cat-modal').classList.add('hidden');
        renderAdminCategories();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function renderAdminTemplates() {
    const tmpls = await apiCall('/admin/templates');
    appState.templates = tmpls;
    const container = document.getElementById('admin-tmpls-table-container');
    if (!container) return;

    if (tmpls.length === 0) {
        container.innerHTML = `<div class="p-8 text-center text-slate-500 text-xs">No reusable workflow templates created yet.</div>`;
        return;
    }

    container.innerHTML = tmpls.map(t => {
        let stepCount = 0;
        try { stepCount = JSON.parse(t.steps_json).length; } catch (e) {}
        return `
            <div class="p-4 bg-slate-50 border border-slate-200 rounded-2xl text-xs space-y-1">
                <div class="flex items-center justify-between">
                    <span class="font-bold text-slate-900 text-sm">${t.name}</span>
                    <span class="px-2.5 py-0.5 bg-indigo-100 text-indigo-800 rounded-full font-bold text-[10px]">${stepCount} Approval Steps</span>
                </div>
                <p class="text-slate-500 text-[11px]">${t.description || 'Pre-configured institutional approval chain.'}</p>
            </div>
        `;
    }).join('');
}

function showCreateTemplateModal() {
    showToast('Use New Memo form with "Save as Template" option or API endpoint to define templates.', 'info');
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

async function toggleNotificationsDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const dropdown = document.getElementById('notifications-dropdown');
    if (!dropdown) return;
    const isHidden = dropdown.classList.contains('hidden');
    
    // Close demo switcher if open
    const demoMenu = document.getElementById('demo-switcher-menu');
    if (demoMenu) demoMenu.classList.add('hidden');

    if (isHidden) {
        dropdown.classList.remove('hidden');
        try {
            const notifs = await apiCall('/notifications');
            appState.notifications = notifs;
            const list = document.getElementById('notifications-items-list');

            if (!list) return;
            if (notifs.length === 0) {
                list.innerHTML = '<div class="p-6 text-center text-xs text-slate-400">No notifications yet.</div>';
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
        const dd = document.getElementById('notifications-dropdown');
        if (dd) dd.classList.add('hidden');
        if (memoId) {
            showView('memo-detail', memoId);
        }
    } catch (e) {}
}

async function markAllNotificationsRead(e) {
    if (e) e.stopPropagation();
    try {
        await apiCall('/notifications/mark-all-read', { method: 'POST' });
        fetchUnreadCount();
        const notifs = await apiCall('/notifications');
        appState.notifications = notifs;
        const list = document.getElementById('notifications-items-list');
        if (list && notifs) {
            list.innerHTML = notifs.map(n => `
                <div onclick="handleNotificationClick(${n.id}, ${n.memo_id})" class="p-3 border-b border-slate-100 hover:bg-slate-50 cursor-pointer opacity-70 text-xs">
                    <div class="flex items-center justify-between">
                        <span class="text-indigo-900">${n.title}</span>
                        <span class="text-[10px] text-slate-400 font-normal">${new Date(n.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
                    </div>
                    <p class="text-slate-600 text-[11px] mt-0.5 font-normal">${n.message}</p>
                </div>
            `).join('');
        }
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
