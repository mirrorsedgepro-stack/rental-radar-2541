// Radar Realty Australia Engine - Rent & Buy Nationwide
// Supports Cookie-Isolated Workspaces, Australia-Wide Search, and Interactive "Show Don't Tell" Tour

let allListings = [];
let activeListing = null;
let leafletMap = null;
let markersGroup = null;
let currentTab = 'grid';
let userToken = '';

const filters = {
    mode: 'rent',           // 'rent' or 'sale'
    state: 'all',          // 'all', 'NSW', 'VIC', 'QLD', etc.
    suburb: 'all',
    max_price: 550,
    min_price: 0,
    min_beds: 0,
    min_baths: 0,
    min_cars: 0,
    prop_type: 'all',
    query: '',
    sort_by: 'price_asc',
    only_inspections: false,
    only_favorites: false,
    only_pets: false,
    only_pool: false,
    only_aircon: false
};

// ==========================================
// 1. INITIALIZE APP & USER COOKIE WORKSPACE
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    initUserCookie();
    initIcons();
    initPriceSelector();
    initEventListeners();
    initCalculators();
    initTourEngine();
    fetchStats();
    fetchListings();
});

function initIcons() {
    if (window.lucide) {
        lucide.createIcons();
    }
}

// User cookie session isolation: Every visitor gets a unique token stored in cookies and localStorage
function initUserCookie() {
    userToken = getCookie('radar_user_token') || localStorage.getItem('radar_user_token');
    if (!userToken) {
        userToken = 'usr_' + Date.now().toString(36) + '_' + Math.random().toString(36).substring(2, 8);
    }
    // Set cookie with 1 year expiration
    setCookie('radar_user_token', userToken, 365);
    localStorage.setItem('radar_user_token', userToken);

    const displayEl = document.getElementById('user-token-display');
    if (displayEl) displayEl.textContent = userToken;
}

function setCookie(name, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/;SameSite=Lax`;
}

function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
}

// ==========================================
// 2. DYNAMIC PRICE SELECTOR (RENT VS SALE)
// ==========================================
function initPriceSelector() {
    const sel = document.getElementById('filter-price-select');
    const label = document.getElementById('label-price');
    const valDisp = document.getElementById('price-display-val');
    if (!sel) return;

    sel.innerHTML = '';

    if (filters.mode === 'rent') {
        if (label) label.textContent = 'Max Rent';
        const rentOptions = [
            { label: 'Any Rent', val: 0 },
            { label: '< $450/wk (Bargain)', val: 450 },
            { label: '< $550/wk (2541 Cap)', val: 550 },
            { label: '< $700/wk', val: 700 },
            { label: '< $900/wk', val: 900 },
            { label: '< $1,200/wk (Executive)', val: 1200 },
            { label: '< $1,800/wk (Luxury)', val: 1800 }
        ];
        rentOptions.forEach(opt => {
            const el = document.createElement('option');
            el.value = opt.val;
            el.textContent = opt.label;
            if (opt.val === filters.max_price) el.selected = true;
            sel.appendChild(el);
        });
        if (valDisp) valDisp.textContent = filters.max_price ? `$${filters.max_price}/wk` : 'Any';
    } else {
        if (label) label.textContent = 'Max Purchase Price';
        const saleOptions = [
            { label: 'Any Price', val: 0 },
            { label: '< $600,000 (Entry Level)', val: 600000 },
            { label: '< $800,000 (Affordable)', val: 800000 },
            { label: '< $1,000,000 (Under $1M)', val: 1000000 },
            { label: '< $1,400,000', val: 1400000 },
            { label: '< $1,800,000', val: 1800000 },
            { label: '< $2,500,000 (Prestige)', val: 2500000 }
        ];
        saleOptions.forEach(opt => {
            const el = document.createElement('option');
            el.value = opt.val;
            el.textContent = opt.label;
            if (opt.val === filters.max_price) el.selected = true;
            sel.appendChild(el);
        });
        if (valDisp) valDisp.textContent = filters.max_price ? `$${(filters.max_price / 1000).toFixed(0)}k` : 'Any';
    }
}

// ==========================================
// 3. EVENT LISTENERS
// ==========================================
function initEventListeners() {
    // Mode Switch: For Rent vs For Sale
    document.querySelectorAll('.mode-switch-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetMode = btn.getAttribute('data-mode');
            setMode(targetMode);
        });
    });

    // View Navigation Tabs (Desktop & Mobile)
    document.querySelectorAll('.view-tab, .mobile-nav-btn').forEach(tab => {
        tab.addEventListener('click', () => {
            const view = tab.getAttribute('data-view');
            switchView(view);
        });
    });

    // Search query input with debounce
    let searchTimer;
    const searchInput = document.getElementById('filter-query');
    const clearBtn = document.getElementById('btn-clear-search');

    searchInput?.addEventListener('input', (e) => {
        clearTimeout(searchTimer);
        if (clearBtn) {
            clearBtn.classList.toggle('hidden', e.target.value.length === 0);
        }
        searchTimer = setTimeout(() => {
            filters.query = e.target.value.trim();
            fetchListings();
        }, 300);
    });

    clearBtn?.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        clearBtn.classList.add('hidden');
        filters.query = '';
        fetchListings();
    });

    // Location quick pills
    document.querySelectorAll('.loc-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.loc-pill').forEach(p => {
                p.classList.remove('bg-blue-600', 'text-white', 'border-blue-600');
                p.classList.add('bg-slate-50', 'text-slate-700', 'border-slate-200');
            });
            pill.classList.remove('bg-slate-50', 'text-slate-700', 'border-slate-200');
            pill.classList.add('bg-blue-600', 'text-white', 'border-blue-600');

            filters.suburb = pill.getAttribute('data-suburb');
            filters.state = pill.getAttribute('data-state');

            const stateSel = document.getElementById('filter-state');
            if (stateSel) stateSel.value = filters.state;

            fetchListings();
        });
    });

    // State Selector
    document.getElementById('filter-state')?.addEventListener('change', (e) => {
        filters.state = e.target.value;
        fetchListings();
    });

    // Price Selector
    document.getElementById('filter-price-select')?.addEventListener('change', (e) => {
        const val = parseInt(e.target.value) || 0;
        filters.max_price = val;
        const valDisp = document.getElementById('price-display-val');
        if (valDisp) {
            if (!val) valDisp.textContent = 'Any';
            else if (filters.mode === 'rent') valDisp.textContent = `$${val}/wk`;
            else valDisp.textContent = `$${(val / 1000).toFixed(0)}k`;
        }
        fetchListings();
    });

    // Bedrooms Selector
    document.getElementById('filter-beds')?.addEventListener('change', (e) => {
        filters.min_beds = parseInt(e.target.value) || 0;
        fetchListings();
    });

    // Property Type
    document.getElementById('filter-prop-type')?.addEventListener('change', (e) => {
        filters.prop_type = e.target.value;
        fetchListings();
    });

    // Sort Selector
    document.getElementById('filter-sort')?.addEventListener('change', (e) => {
        filters.sort_by = e.target.value;
        fetchListings();
    });

    // 1-Tap Feature Chips
    document.querySelectorAll('.feature-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const feat = chip.getAttribute('data-feature');
            toggleFeatureChip(feat, chip);
        });
    });

    // Reset Filters
    document.getElementById('btn-reset-filters')?.addEventListener('click', resetFilters);

    // Header Shortlist Button
    document.getElementById('btn-header-shortlist')?.addEventListener('click', () => {
        filters.only_favorites = !filters.only_favorites;
        const favChip = document.querySelector('.feature-chip[data-feature="favorites"]');
        if (favChip) syncChipVisual(favChip, filters.only_favorites);
        fetchListings();
    });

    // Modal Trigger Buttons
    document.getElementById('btn-add-modal')?.addEventListener('click', () => showModal('modal-add'));
    document.getElementById('btn-settings-modal')?.addEventListener('click', () => showModal('modal-settings'));
    document.getElementById('btn-open-more-filters')?.addEventListener('click', () => showModal('modal-more-filters'));

    // Modal Close Buttons
    document.getElementById('modal-close-btn')?.addEventListener('click', () => hideModal('modal-property'));
    document.getElementById('modal-add-close')?.addEventListener('click', () => hideModal('modal-add'));
    document.getElementById('modal-add-cancel')?.addEventListener('click', () => hideModal('modal-add'));
    document.getElementById('modal-settings-close')?.addEventListener('click', () => hideModal('modal-settings'));
    document.getElementById('modal-settings-cancel')?.addEventListener('click', () => hideModal('modal-settings'));
    document.getElementById('modal-more-filters-close')?.addEventListener('click', () => hideModal('modal-more-filters'));

    // Details Modal Save Notes & Toggle Favorite
    document.getElementById('modal-save-btn')?.addEventListener('click', saveActiveListingMeta);
    document.getElementById('modal-fav-btn')?.addEventListener('click', toggleActiveFavorite);

    // Add Custom Property Form
    document.getElementById('form-add-rental')?.addEventListener('submit', handleAddRental);

    // Settings Save
    document.getElementById('modal-settings-save')?.addEventListener('click', () => {
        hideModal('modal-settings');
        showToast("Session preferences updated!");
    });

    // More Filters Apply & Reset
    document.getElementById('btn-more-apply')?.addEventListener('click', applyMoreFilters);
    document.getElementById('btn-more-reset')?.addEventListener('click', resetMoreFilters);
}

function setMode(mode) {
    filters.mode = mode;

    document.querySelectorAll('.mode-switch-btn').forEach(b => {
        if (b.getAttribute('data-mode') === mode) {
            b.classList.add('mode-pill-active');
            b.classList.remove('text-slate-600');
        } else {
            b.classList.remove('mode-pill-active');
            b.classList.add('text-slate-600');
        }
    });

    // Adjust default max price based on mode
    if (mode === 'rent') {
        filters.max_price = 550;
    } else {
        filters.max_price = 1000000;
    }

    initPriceSelector();
    fetchStats();
    fetchListings();
}

function toggleFeatureChip(feat, chipEl) {
    if (feat === 'pets') {
        filters.only_pets = !filters.only_pets;
        syncChipVisual(chipEl, filters.only_pets);
    } else if (feat === 'inspections') {
        filters.only_inspections = !filters.only_inspections;
        syncChipVisual(chipEl, filters.only_inspections);
    } else if (feat === 'pool') {
        filters.only_pool = !filters.only_pool;
        syncChipVisual(chipEl, filters.only_pool);
    } else if (feat === 'aircon') {
        filters.only_aircon = !filters.only_aircon;
        syncChipVisual(chipEl, filters.only_aircon);
    } else if (feat === 'favorites') {
        filters.only_favorites = !filters.only_favorites;
        syncChipVisual(chipEl, filters.only_favorites);
    }
    fetchListings();
}

function syncChipVisual(chipEl, isActive) {
    if (!chipEl) return;
    if (isActive) {
        chipEl.classList.add('bg-blue-600', 'text-white', 'border-blue-600', 'shadow-xs');
        chipEl.classList.remove('bg-slate-50', 'text-slate-700', 'border-slate-200');
    } else {
        chipEl.classList.remove('bg-blue-600', 'text-white', 'border-blue-600', 'shadow-xs');
        chipEl.classList.add('bg-slate-50', 'text-slate-700', 'border-slate-200');
    }
}

function applyMoreFilters() {
    filters.min_baths = parseInt(document.getElementById('more-filter-baths')?.value) || 0;
    filters.min_cars = parseInt(document.getElementById('more-filter-cars')?.value) || 0;
    filters.min_price = parseInt(document.getElementById('more-filter-min-price')?.value) || 0;
    const maxP = parseInt(document.getElementById('more-filter-max-price')?.value);
    if (maxP && maxP > 0) filters.max_price = maxP;

    filters.only_pets = document.getElementById('more-pets')?.checked || false;
    filters.only_pool = document.getElementById('more-pool')?.checked || false;
    filters.only_aircon = document.getElementById('more-aircon')?.checked || false;
    filters.only_inspections = document.getElementById('more-inspections')?.checked || false;

    // Sync chip visual states
    syncChipVisual(document.querySelector('.feature-chip[data-feature="pets"]'), filters.only_pets);
    syncChipVisual(document.querySelector('.feature-chip[data-feature="pool"]'), filters.only_pool);
    syncChipVisual(document.querySelector('.feature-chip[data-feature="aircon"]'), filters.only_aircon);
    syncChipVisual(document.querySelector('.feature-chip[data-feature="inspections"]'), filters.only_inspections);

    hideModal('modal-more-filters');
    fetchListings();
}

function resetMoreFilters() {
    if (document.getElementById('more-filter-baths')) document.getElementById('more-filter-baths').value = '0';
    if (document.getElementById('more-filter-cars')) document.getElementById('more-filter-cars').value = '0';
    if (document.getElementById('more-filter-min-price')) document.getElementById('more-filter-min-price').value = '';
    if (document.getElementById('more-filter-max-price')) document.getElementById('more-filter-max-price').value = '';
    if (document.getElementById('more-pets')) document.getElementById('more-pets').checked = false;
    if (document.getElementById('more-pool')) document.getElementById('more-pool').checked = false;
    if (document.getElementById('more-aircon')) document.getElementById('more-aircon').checked = false;
    if (document.getElementById('more-inspections')) document.getElementById('more-inspections').checked = false;
    applyMoreFilters();
}

function resetFilters() {
    filters.state = 'all';
    filters.suburb = 'all';
    filters.query = '';
    filters.min_beds = 0;
    filters.min_baths = 0;
    filters.min_cars = 0;
    filters.min_price = 0;
    filters.max_price = (filters.mode === 'rent') ? 550 : 1000000;
    filters.prop_type = 'all';
    filters.sort_by = 'price_asc';
    filters.only_inspections = false;
    filters.only_favorites = false;
    filters.only_pets = false;
    filters.only_pool = false;
    filters.only_aircon = false;

    // Reset inputs
    const qInput = document.getElementById('filter-query');
    if (qInput) qInput.value = '';
    const stateSel = document.getElementById('filter-state');
    if (stateSel) stateSel.value = 'all';
    const bedSel = document.getElementById('filter-beds');
    if (bedSel) bedSel.value = '0';
    const typeSel = document.getElementById('filter-prop-type');
    if (typeSel) typeSel.value = 'all';
    const sortSel = document.getElementById('filter-sort');
    if (sortSel) sortSel.value = 'price_asc';

    document.querySelectorAll('.feature-chip').forEach(c => syncChipVisual(c, false));
    document.querySelectorAll('.loc-pill').forEach((p, idx) => {
        if (idx === 0) {
            p.classList.add('bg-blue-600', 'text-white', 'border-blue-600');
            p.classList.remove('bg-slate-50', 'text-slate-700', 'border-slate-200');
        } else {
            p.classList.remove('bg-blue-600', 'text-white', 'border-blue-600');
            p.classList.add('bg-slate-50', 'text-slate-700', 'border-slate-200');
        }
    });

    initPriceSelector();
    fetchListings();
}

// ==========================================
// 4. FETCH LISTINGS & RENDER CARDS
// ==========================================
async function fetchListings() {
    try {
        const params = new URLSearchParams();
        params.append('listing_type', filters.mode);
        if (filters.state !== 'all') params.append('state', filters.state);
        if (filters.suburb !== 'all') params.append('suburb', filters.suburb);
        if (filters.max_price > 0) params.append('max_price', filters.max_price);
        if (filters.min_price > 0) params.append('min_price', filters.min_price);
        if (filters.min_beds > 0) params.append('min_beds', filters.min_beds);
        if (filters.min_baths > 0) params.append('min_baths', filters.min_baths);
        if (filters.min_cars > 0) params.append('min_cars', filters.min_cars);
        if (filters.prop_type !== 'all') params.append('prop_type', filters.prop_type);
        if (filters.query) params.append('query', filters.query);
        params.append('sort_by', filters.sort_by);
        if (filters.only_inspections) params.append('only_inspections', 'true');
        if (filters.only_favorites) params.append('only_favorites', 'true');
        if (filters.only_pets) params.append('only_pets', 'true');
        if (filters.only_pool) params.append('only_pool', 'true');
        if (filters.only_aircon) params.append('only_aircon', 'true');
        params.append('user_id', userToken);

        const res = await fetch(`/api/listings?${params.toString()}`);
        const data = await res.json();
        allListings = data.listings || [];

        // Update results counter & headline
        const countBadge = document.getElementById('results-count-badge');
        if (countBadge) countBadge.textContent = `${allListings.length} ${filters.mode === 'rent' ? 'rentals' : 'properties'}`;

        const headline = document.getElementById('results-headline');
        if (headline) {
            const locName = filters.suburb !== 'all' ? filters.suburb : (filters.state !== 'all' ? filters.state : 'Australia');
            headline.textContent = `${filters.mode === 'rent' ? 'Rentals' : 'Properties for Sale'} in ${locName}`;
        }

        renderListingsGrid(allListings);

        if (currentTab === 'map') {
            initOrUpdateMap();
        } else if (currentTab === 'kanban') {
            renderKanban();
        }

        initIcons();
    } catch (e) {
        console.error("Error fetching listings:", e);
        showToast("Could not load listings. Please check connection.");
    }
}

function renderListingsGrid(items) {
    const grid = document.getElementById('listings-grid');
    const noResults = document.getElementById('no-results');

    if (!items || items.length === 0) {
        if (grid) grid.innerHTML = '';
        if (noResults) noResults.classList.remove('hidden');
        return;
    }

    if (noResults) noResults.classList.add('hidden');
    if (grid) grid.innerHTML = items.map(item => createListingCardHtml(item)).join('');
}

function createListingCardHtml(item) {
    const isSale = item.listing_type === 'sale';
    const fallbackImg = "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=800&q=80";
    const imgUrl = item.image_url || fallbackImg;

    // Price Display
    let priceFormatted = '';
    let priceBadge = '';
    if (isSale) {
        priceFormatted = `$${(item.price || 0).toLocaleString()}`;
        const weeklyEst = Math.round((item.price * 0.8 * 0.0615) / 52);
        priceBadge = `<span class="text-[11px] font-bold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700">~$${weeklyEst.toLocaleString()}/wk mortgage</span>`;
    } else {
        priceFormatted = `$${item.price || '--'}<span class="text-xs font-normal text-slate-500"> /wk</span>`;
        const valTag = item.price <= 450 ? 'Bargain' : (item.price <= 550 ? 'Under $550' : 'Rental');
        const colorTag = item.price <= 450 ? 'bg-emerald-50 text-emerald-700' : 'bg-blue-50 text-blue-700';
        priceBadge = `<span class="text-[11px] font-bold px-2 py-0.5 rounded-full ${colorTag}">${valTag}</span>`;
    }

    // Open home badge
    let inspBadge = '';
    if (item.inspection_date) {
        inspBadge = `
            <div class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
                <i data-lucide="calendar" class="w-3 h-3 mr-1 text-indigo-500"></i>
                <span>Open: ${formatInspection(item.inspection_date)}</span>
            </div>
        `;
    }

    // Pet friendly badge
    let petBadge = '';
    if (item.pets_allowed) {
        petBadge = `
            <div class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-100">
                <i data-lucide="paw-print" class="w-3 h-3 mr-1 text-emerald-600"></i>
                <span>Pets OK</span>
            </div>
        `;
    }

    const favFill = item.is_favorite ? 'text-rose-500 fill-current' : 'text-slate-400 hover:text-rose-500';

    return `
        <div class="property-card-touch bg-white rounded-3xl border border-slate-200/90 shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden flex flex-col group cursor-pointer" data-id="${item.id}" onclick="openListingModal('${item.id}')">
            <!-- Card Image -->
            <div class="relative h-52 sm:h-56 bg-slate-900 overflow-hidden">
                <img src="${imgUrl}" alt="${escapeHtml(item.street)}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.src='${fallbackImg}'">
                <div class="absolute inset-0 bg-gradient-to-t from-slate-950/60 via-transparent to-black/20"></div>

                <!-- Mode Tag & Property Type -->
                <div class="absolute top-3 left-3 flex items-center space-x-1.5">
                    <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${isSale ? 'bg-purple-600' : 'bg-blue-600'} text-white shadow-md">
                        ${isSale ? 'FOR SALE' : 'FOR RENT'}
                    </span>
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-black/60 text-white backdrop-blur">
                        ${escapeHtml(item.prop_type || 'House')}
                    </span>
                </div>

                <!-- Shortlist Heart Button (Cookie Isolated) -->
                <button onclick="event.stopPropagation(); quickToggleFav('${item.id}')" class="absolute top-3 right-3 w-10 h-10 rounded-full bg-white/95 hover:bg-white flex items-center justify-center shadow-lg transition active:scale-90" title="Shortlist / Save to my session">
                    <i data-lucide="heart" class="w-4 h-4 ${favFill}"></i>
                </button>

                <!-- Suburb and State on image bottom -->
                <div class="absolute bottom-3 left-3 right-3 flex justify-between items-center text-white">
                    <span class="text-xs font-bold flex items-center drop-shadow">
                        <i data-lucide="map-pin" class="w-3.5 h-3.5 mr-1 text-emerald-400"></i>
                        ${escapeHtml(item.suburb)}, ${escapeHtml(item.state || 'NSW')} ${item.postcode || ''}
                    </span>
                    <span class="text-[10px] font-semibold bg-white/20 backdrop-blur px-2 py-0.5 rounded-full">
                        ${escapeHtml(item.source || 'Portal')}
                    </span>
                </div>
            </div>

            <!-- Card Body: Spacious details -->
            <div class="p-5 flex-1 flex flex-col justify-between space-y-3.5">
                <div>
                    <!-- Price Row -->
                    <div class="flex items-baseline justify-between">
                        <span class="text-xl sm:text-2xl font-black text-slate-900">${priceFormatted}</span>
                        ${priceBadge}
                    </div>

                    <!-- Street Address -->
                    <h3 class="font-extrabold text-sm sm:text-base text-slate-900 mt-1 truncate group-hover:text-blue-600 transition" title="${escapeHtml(item.street)}">
                        ${escapeHtml(item.street)}
                    </h3>

                    <!-- Specs row: Beds, Baths, Cars -->
                    <div class="flex items-center space-x-4 mt-3 pt-3 border-t border-slate-100 text-xs font-bold text-slate-600">
                        <span class="flex items-center" title="Bedrooms">
                            <i data-lucide="bed" class="w-4 h-4 mr-1 text-slate-400"></i> ${item.beds || 1} Bed
                        </span>
                        <span class="flex items-center" title="Bathrooms">
                            <i data-lucide="bath" class="w-4 h-4 mr-1 text-slate-400"></i> ${item.baths || 1} Bath
                        </span>
                        <span class="flex items-center" title="Parking / Garage">
                            <i data-lucide="car" class="w-4 h-4 mr-1 text-slate-400"></i> ${item.cars || 0} Car
                        </span>
                    </div>

                    <!-- Feature Badges: Inspections & Pets -->
                    <div class="mt-3 flex flex-wrap gap-1.5 items-center">
                        ${inspBadge}
                        ${petBadge}
                    </div>
                </div>

                <!-- Footer with personal pipeline stage and action -->
                <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs" onclick="event.stopPropagation()">
                    <select onchange="updateListingStatus('${item.id}', this.value)" class="text-[11px] font-bold py-1 px-2.5 border border-slate-200 rounded-xl bg-slate-50 text-slate-700 hover:bg-slate-100 focus:outline-none transition">
                        <option value="discovered" ${item.status === 'discovered' ? 'selected' : ''}>🔍 Discovered</option>
                        <option value="saved" ${item.status === 'saved' ? 'selected' : ''}>⭐ Shortlisted</option>
                        <option value="inspecting" ${item.status === 'inspecting' ? 'selected' : ''}>📅 Inspecting</option>
                        <option value="applied" ${item.status === 'applied' ? 'selected' : ''}>📝 ${isSale ? 'Offer Made' : 'Applied'}</option>
                        <option value="offered" ${item.status === 'offered' ? 'selected' : ''}>🎉 Approved</option>
                    </select>

                    <button onclick="openListingModal('${item.id}')" class="font-extrabold text-blue-600 hover:text-blue-800 transition flex items-center p-1 active:scale-95">
                        <span>Details</span>
                        <i data-lucide="chevron-right" class="w-4 h-4 ml-0.5"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// ==========================================
// 5. LISTING DETAILS MODAL & PERSONAL WORKSPACE
// ==========================================
function openListingModal(listingId) {
    const item = allListings.find(l => l.id == listingId);
    if (!item) return;

    activeListing = item;
    const isSale = item.listing_type === 'sale';
    const fallbackImg = "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=800&q=80";

    const modalImg = document.getElementById('modal-img');
    if (modalImg) modalImg.src = item.image_url || fallbackImg;

    const modalMode = document.getElementById('modal-mode-badge');
    if (modalMode) {
        modalMode.textContent = isSale ? 'FOR SALE' : 'FOR RENT';
        modalMode.className = `px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider ${isSale ? 'bg-purple-600' : 'bg-blue-600'} text-white`;
    }

    const modalType = document.getElementById('modal-type-badge');
    if (modalType) modalType.textContent = item.prop_type || 'House';

    const modalPrice = document.getElementById('modal-price');
    if (modalPrice) {
        if (isSale) modalPrice.textContent = `$${(item.price || 0).toLocaleString()}`;
        else modalPrice.innerHTML = `$${item.price || '--'} <span class="text-sm font-normal text-slate-200">/ week</span>`;
    }

    const modalAddress = document.getElementById('modal-address');
    if (modalAddress) modalAddress.textContent = `${item.street}, ${item.suburb} ${item.state || 'NSW'} ${item.postcode || ''}`;

    const modalBeds = document.getElementById('modal-beds');
    if (modalBeds) modalBeds.textContent = item.beds || 1;

    const modalBaths = document.getElementById('modal-baths');
    if (modalBaths) modalBaths.textContent = item.baths || 1;

    const modalCars = document.getElementById('modal-cars');
    if (modalCars) modalCars.textContent = item.cars || 0;

    // Financial label & val
    const finLabel = document.getElementById('modal-financial-label');
    const finVal = document.getElementById('modal-financial-val');
    if (finLabel && finVal) {
        if (isSale) {
            finLabel.textContent = 'Est. Mortgage';
            const weeklyEst = Math.round((item.price * 0.8 * 0.0615) / 52);
            finVal.textContent = `~$${weeklyEst}/wk`;
        } else {
            finLabel.textContent = 'Bond (4wks)';
            finVal.textContent = `$${((item.price || 0) * 4).toLocaleString()}`;
        }
    }

    // Description
    const modalDesc = document.getElementById('modal-desc');
    if (modalDesc) modalDesc.textContent = item.description || "Modern Australian property with premium inclusions.";

    // Personal Workspace (Loaded per cookie user_id)
    const modalNotes = document.getElementById('modal-notes');
    if (modalNotes) modalNotes.value = item.notes || "";

    const modalStatus = document.getElementById('modal-status-select');
    if (modalStatus) modalStatus.value = item.status || "discovered";

    const modalRating = document.getElementById('modal-rating-select');
    if (modalRating) modalRating.value = item.rating || 0;

    // Inspection Box
    const inspBox = document.getElementById('modal-inspection-box');
    if (item.inspection_date && inspBox) {
        inspBox.classList.remove('hidden');
        const inspText = document.getElementById('modal-inspection-text');
        if (inspText) inspText.textContent = formatInspection(item.inspection_date);
        const icalBtn = document.getElementById('modal-ical-btn');
        if (icalBtn) icalBtn.href = `/api/calendar/${item.id}.ics`;
    } else if (inspBox) {
        inspBox.classList.add('hidden');
    }

    // Pet Box
    const petBox = document.getElementById('modal-pet-box');
    const petText = document.getElementById('modal-pet-text');
    const petBadge = document.getElementById('modal-pet-badge');
    const petIcon = document.getElementById('modal-pet-icon-wrap');
    if (petBox && petText && petBadge) {
        if (item.pets_allowed) {
            petText.textContent = "Pets Allowed / Considered Upon Application";
            petBadge.textContent = "Pet Friendly";
            petBadge.className = "px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800";
            if (petIcon) petIcon.className = "w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 bg-emerald-100 text-emerald-700";
        } else {
            petText.textContent = "Check with agent regarding pets policy";
            petBadge.textContent = "Subject to Policy";
            petBadge.className = "px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-200 text-slate-700";
            if (petIcon) petIcon.className = "w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 bg-slate-100 text-slate-500";
        }
    }

    // Maps link
    const q = encodeURIComponent(`${item.street}, ${item.suburb} ${item.state || 'NSW'} Australia`);
    const mapsLink = document.getElementById('modal-maps-link');
    if (mapsLink) mapsLink.href = `https://www.google.com/maps/search/?api=1&query=${q}`;

    // Portal link
    const portalLink = document.getElementById('modal-portal-link');
    if (portalLink) portalLink.href = item.url || '#';

    // Favorite heart icon
    updateModalFavIcon(item.is_favorite);

    showModal('modal-property');
    initIcons();
}

function updateModalFavIcon(isFav) {
    const icon = document.getElementById('modal-fav-icon');
    if (icon) {
        if (isFav) {
            icon.classList.add('text-rose-500', 'fill-current');
            icon.classList.remove('text-white');
        } else {
            icon.classList.remove('text-rose-500', 'fill-current');
            icon.classList.add('text-white');
        }
    }
}

async function toggleActiveFavorite() {
    if (!activeListing) return;
    const newFav = activeListing.is_favorite ? 0 : 1;
    activeListing.is_favorite = newFav;
    updateModalFavIcon(newFav);

    await fetch(`/api/listings/${activeListing.id}/meta?user_id=${userToken}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_favorite: newFav })
    });
    fetchStats();
    fetchListings();
}

async function quickToggleFav(lid) {
    const item = allListings.find(l => l.id == lid);
    if (!item) return;
    const newFav = item.is_favorite ? 0 : 1;
    item.is_favorite = newFav;

    showToast(newFav ? "Saved to your private shortlist!" : "Removed from shortlist");

    await fetch(`/api/listings/${lid}/meta?user_id=${userToken}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_favorite: newFav })
    });

    fetchStats();
    renderListingsGrid(allListings);
    initIcons();
}

async function updateListingStatus(lid, newStatus) {
    const item = allListings.find(l => l.id == lid);
    if (item) item.status = newStatus;

    await fetch(`/api/listings/${lid}/meta?user_id=${userToken}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
    });
    showToast(`Updated to stage: ${newStatus}`);
    fetchStats();
}

async function saveActiveListingMeta() {
    if (!activeListing) return;
    const newNotes = document.getElementById('modal-notes')?.value || "";
    const newStatus = document.getElementById('modal-status-select')?.value || "discovered";
    const newRating = parseInt(document.getElementById('modal-rating-select')?.value) || 0;

    await fetch(`/api/listings/${activeListing.id}/meta?user_id=${userToken}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            notes: newNotes,
            status: newStatus,
            rating: newRating
        })
    });

    activeListing.notes = newNotes;
    activeListing.status = newStatus;
    activeListing.rating = newRating;

    hideModal('modal-property');
    showToast("Personal workspace notes saved!");
    fetchListings();
}

// ==========================================
// 6. SHOW DON'T TELL INTERACTIVE SPOTLIGHT TOUR
// ==========================================
let currentTourStep = 1;
const totalTourSteps = 5;
let typingInterval = null;

function initTourEngine() {
    const triggerBtn = document.getElementById('btn-tour-trigger');
    const skipBtn = document.getElementById('tour-btn-skip');
    const nextBtn = document.getElementById('tour-btn-next');
    const prevBtn = document.getElementById('tour-btn-prev');

    triggerBtn?.addEventListener('click', startInteractiveTour);
    skipBtn?.addEventListener('click', closeTour);

    nextBtn?.addEventListener('click', () => {
        if (currentTourStep < totalTourSteps) {
            currentTourStep++;
            renderTourStep();
        } else {
            closeTour();
            showToast("Tour complete! Enjoy exploring properties across Australia.");
        }
    });

    prevBtn?.addEventListener('click', () => {
        if (currentTourStep > 1) {
            currentTourStep--;
            renderTourStep();
        }
    });

    // Auto-launch for new users if not previously seen
    const tourSeen = localStorage.getItem('radar_tour_seen');
    if (!tourSeen) {
        setTimeout(startInteractiveTour, 800);
    }
}

function startInteractiveTour() {
    currentTourStep = 1;
    const overlay = document.getElementById('tour-overlay');
    if (overlay) overlay.classList.remove('hidden');
    renderTourStep();
}

function closeTour() {
    clearInterval(typingInterval);
    const overlay = document.getElementById('tour-overlay');
    if (overlay) overlay.classList.add('hidden');
    localStorage.setItem('radar_tour_seen', 'true');

    // Reset search input if tour simulated typing
    const searchInput = document.getElementById('filter-query');
    if (searchInput && (searchInput.value === 'Sydney NSW' || searchInput.value === 'Nowra 2541')) {
        searchInput.value = '';
        filters.query = '';
        fetchListings();
    }
}

function renderTourStep() {
    clearInterval(typingInterval);
    const badge = document.getElementById('tour-step-badge');
    const title = document.getElementById('tour-title');
    const desc = document.getElementById('tour-desc');
    const actionText = document.getElementById('tour-action-text');
    const dots = document.getElementById('tour-dots');
    const prevBtn = document.getElementById('tour-btn-prev');
    const nextBtn = document.getElementById('tour-btn-next');
    const spotlight = document.getElementById('tour-spotlight');
    const card = document.getElementById('tour-dialog-card');

    if (badge) badge.textContent = `Step ${currentTourStep} of ${totalTourSteps}`;
    if (prevBtn) prevBtn.disabled = currentTourStep === 1;
    if (nextBtn) nextBtn.textContent = currentTourStep === totalTourSteps ? 'Got It! Finish' : 'Next Step →';

    // Update dots
    if (dots) {
        dots.innerHTML = Array.from({ length: totalTourSteps }).map((_, i) => {
            const active = (i + 1) === currentTourStep;
            return `<span class="w-2 h-2 rounded-full ${active ? 'bg-blue-600 w-4' : 'bg-slate-300'} transition-all duration-300"></span>`;
        }).join('');
    }

    // Step-by-step logic
    if (currentTourStep === 1) {
        // STEP 1: Search Anywhere in Australia
        const target = document.getElementById('tour-step-search');
        positionSpotlight(target, spotlight, card, 'bottom');

        title.textContent = "1. Search Anywhere in Australia";
        desc.textContent = "Watch: As you type a suburb or city, live properties filter instantly!";
        actionText.textContent = 'Simulating typing "Sydney NSW" into search bar...';

        // Simulated typewriter demo
        simulateTyping("Sydney NSW", () => {
            actionText.textContent = 'Filtered to Sydney! Now typing "Nowra 2541"...';
            setTimeout(() => {
                simulateTyping("Nowra 2541", () => {
                    actionText.textContent = 'Now showing 2541 regional rentals in real-time!';
                });
            }, 1200);
        });

    } else if (currentTourStep === 2) {
        // STEP 2: Rent vs Buy Switch
        const target = document.getElementById('tour-step-mode');
        positionSpotlight(target, spotlight, card, 'bottom');

        title.textContent = "2. Toggle Rent vs Buy";
        desc.textContent = "Switch effortlessly between renting and buying. Prices transform to purchase prices with estimated weekly mortgage repayments!";
        actionText.textContent = 'Simulating click on "For Sale"...';

        setTimeout(() => {
            setMode('sale');
            actionText.textContent = 'Properties updated to Houses for Sale across Australia!';
        }, 600);

    } else if (currentTourStep === 3) {
        // STEP 3: 1-Tap Feature Filters
        const target = document.getElementById('tour-step-chips');
        positionSpotlight(target, spotlight, card, 'bottom');

        title.textContent = "3. One-Tap Quick Toggles";
        desc.textContent = "Filter for Pet Friendly, Upcoming Open Homes, Swimming Pools, or Air Conditioning with a single tap.";
        actionText.textContent = 'Simulating activating "🐾 Pets Allowed"...';

        setTimeout(() => {
            filters.only_pets = true;
            syncChipVisual(document.querySelector('.feature-chip[data-feature="pets"]'), true);
            fetchListings();
            actionText.textContent = 'Active! All displayed properties now guarantee pets allowed.';
        }, 500);

    } else if (currentTourStep === 4) {
        // STEP 4: Smooth Scrolling & Personal Shortlist
        const firstCard = document.querySelector('.property-card-touch');
        if (firstCard) {
            firstCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            setTimeout(() => {
                positionSpotlight(firstCard, spotlight, card, 'top');
            }, 450);
        }

        title.textContent = "4. Private Shortlist & Notes";
        desc.textContent = "Every visitor receives a private session cookie. When you tap the heart or add inspection notes, only you see them!";
        actionText.textContent = 'Tapping heart icon to shortlist property to your session...';

        setTimeout(() => {
            if (firstCard) {
                const id = firstCard.getAttribute('data-id');
                quickToggleFav(id);
                actionText.textContent = 'Saved to your private shortlist (persisted across visits)!';
            }
        }, 700);

    } else if (currentTourStep === 5) {
        // STEP 5: Interactive Map & Calculators
        window.scrollTo({ top: 0, behavior: 'smooth' });
        const tabs = document.querySelector('nav[aria-label="Tabs"]');
        setTimeout(() => {
            positionSpotlight(tabs, spotlight, card, 'bottom');
        }, 350);

        title.textContent = "5. Australia Map & Financial Tools";
        desc.textContent = "Explore our interactive pin map across all Australian states, or calculate rental bond and mortgage repayments in the calculator.";
        actionText.textContent = 'You are ready to search! Tap "Got It" to start.';
    }

    initIcons();
}

function positionSpotlight(targetEl, spotlight, card, placement = 'bottom') {
    if (!targetEl || !spotlight || !card) return;
    const rect = targetEl.getBoundingClientRect();
    const pad = 8;

    spotlight.style.top = `${rect.top - pad}px`;
    spotlight.style.left = `${rect.left - pad}px`;
    spotlight.style.width = `${rect.width + (pad * 2)}px`;
    spotlight.style.height = `${rect.height + (pad * 2)}px`;
    spotlight.style.borderRadius = `16px`;

    // Calculate card positioning
    const cardWidth = card.offsetWidth || 380;
    let cardTop = 0;
    let cardLeft = Math.max(16, Math.min(window.innerWidth - cardWidth - 16, rect.left));

    if (placement === 'bottom') {
        cardTop = rect.bottom + 20;
        if (cardTop + 240 > window.innerHeight) {
            cardTop = Math.max(20, rect.top - 260);
        }
    } else {
        cardTop = Math.max(20, rect.top - 260);
    }

    card.style.top = `${cardTop}px`;
    card.style.left = `${cardLeft}px`;
}

function simulateTyping(text, onComplete) {
    const input = document.getElementById('filter-query');
    if (!input) return;
    input.value = '';
    let idx = 0;

    clearInterval(typingInterval);
    typingInterval = setInterval(() => {
        if (idx < text.length) {
            input.value += text[idx];
            idx++;
        } else {
            clearInterval(typingInterval);
            filters.query = text;
            fetchListings();
            if (onComplete) onComplete();
        }
    }, 60);
}

// ==========================================
// 7. FINANCIAL CALCULATORS (BOND & MORTGAGE)
// ==========================================
function initCalculators() {
    // Rental Upfront & Bond
    const rentInput = document.getElementById('calc-rent-input');
    const updateRent = () => {
        const rent = parseFloat(rentInput.value) || 0;
        const bond = rent * 4;
        const advance = rent * 2;
        const upfront = bond + advance;
        const monthly = (rent * 52) / 12;

        const bEl = document.getElementById('calc-bond');
        const aEl = document.getElementById('calc-advance');
        const uEl = document.getElementById('calc-upfront');
        const mEl = document.getElementById('calc-monthly');

        if (bEl) bEl.textContent = `$${bond.toLocaleString()}`;
        if (aEl) aEl.textContent = `$${advance.toLocaleString()}`;
        if (uEl) uEl.textContent = `$${upfront.toLocaleString()}`;
        if (mEl) mEl.textContent = `$${Math.round(monthly).toLocaleString()} / mo`;
    };
    rentInput?.addEventListener('input', updateRent);

    // Purchase Mortgage Repayments
    const priceInput = document.getElementById('calc-sale-price');
    const depInput = document.getElementById('calc-deposit');
    const rateInput = document.getElementById('calc-rate');

    const updateMortgage = () => {
        const price = parseFloat(priceInput?.value) || 0;
        const deposit = parseFloat(depInput?.value) || (price * 0.2);
        const rate = (parseFloat(rateInput?.value) || 6.15) / 100;
        const loan = Math.max(0, price - deposit);

        const monthlyRate = rate / 12;
        const nPayments = 30 * 12; // 30 years
        let monthlyRepayment = 0;
        if (monthlyRate > 0) {
            monthlyRepayment = loan * (monthlyRate * Math.pow(1 + monthlyRate, nPayments)) / (Math.pow(1 + monthlyRate, nPayments) - 1);
        }
        const weeklyRepayment = (monthlyRepayment * 12) / 52;

        const lEl = document.getElementById('calc-loan-amount');
        const wEl = document.getElementById('calc-mortgage-weekly');
        const mEl = document.getElementById('calc-mortgage-monthly');

        if (lEl) lEl.textContent = `$${Math.round(loan).toLocaleString()}`;
        if (wEl) wEl.textContent = `$${Math.round(weeklyRepayment).toLocaleString()} / wk`;
        if (mEl) mEl.textContent = `$${Math.round(monthlyRepayment).toLocaleString()} / mo`;
    };

    priceInput?.addEventListener('input', () => {
        if (depInput && priceInput) depInput.value = Math.round(parseFloat(priceInput.value) * 0.2);
        updateMortgage();
    });
    depInput?.addEventListener('input', updateMortgage);
    rateInput?.addEventListener('input', updateMortgage);

    updateRent();
    updateMortgage();
}

// ==========================================
// 8. INTERACTIVE LEAFLET MAP
// ==========================================
function initOrUpdateMap() {
    const container = document.getElementById('map');
    if (!container) return;

    if (!leafletMap) {
        // Default center on Australia
        leafletMap = L.map('map', { zoomControl: false }).setView([-30.0, 135.0], 5);
        L.control.zoom({ position: 'bottomright' }).addTo(leafletMap);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(leafletMap);

        markersGroup = L.layerGroup().addTo(leafletMap);
    }

    leafletMap.invalidateSize();
    markersGroup.clearLayers();

    const bounds = [];

    allListings.forEach(item => {
        if (!item.lat || !item.lng) return;

        const isSale = item.listing_type === 'sale';
        let pinClass = 'pin-blue';
        let label = '';

        if (isSale) {
            pinClass = 'pin-purple';
            label = `$${(item.price / 1000).toFixed(0)}k`;
        } else {
            label = `$${item.price || '?'}`;
            pinClass = item.price <= 450 ? 'pin-green' : (item.price <= 550 ? 'pin-blue' : 'pin-amber');
        }

        const customIcon = L.divIcon({
            className: `custom-price-pin ${pinClass}`,
            html: `<span>${label}</span>`,
            iconSize: [54, 26],
            iconAnchor: [27, 13]
        });

        const marker = L.marker([item.lat, item.lng], { icon: customIcon });

        const popupContent = `
            <div style="width: 220px;" class="p-2 space-y-1 text-xs">
                ${item.image_url ? `<img src="${item.image_url}" class="w-full h-24 object-cover rounded-xl mb-1.5">` : ''}
                <div class="flex justify-between items-center">
                    <span class="font-extrabold text-sm text-slate-900">${isSale ? `$${item.price.toLocaleString()}` : `$${item.price}/wk`}</span>
                    <span class="text-[10px] uppercase font-bold text-slate-500">${escapeHtml(item.suburb)}</span>
                </div>
                <p class="font-bold text-slate-800 truncate">${escapeHtml(item.street)}</p>
                <p class="text-slate-500">${item.beds || 1}b • ${item.baths || 1}ba (${escapeHtml(item.prop_type || 'House')})</p>
                <button onclick="openListingModal('${item.id}')" class="w-full mt-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-center block transition">
                    View Details
                </button>
            </div>
        `;

        marker.bindPopup(popupContent);
        markersGroup.addLayer(marker);
        bounds.push([item.lat, item.lng]);
    });

    if (bounds.length > 0) {
        leafletMap.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    }
}

function zoomToRegion(lat, lng, zoom) {
    if (leafletMap) {
        leafletMap.setView([lat, lng], zoom, { animate: true });
    }
}

// ==========================================
// 9. KANBAN APPLICATION PIPELINE
// ==========================================
function renderKanban() {
    const cols = {
        discovered: document.getElementById('kanban-discovered'),
        saved: document.getElementById('kanban-saved'),
        inspecting: document.getElementById('kanban-inspecting'),
        applied: document.getElementById('kanban-applied'),
        offered: document.getElementById('kanban-offered')
    };

    Object.values(cols).forEach(c => { if (c) c.innerHTML = ''; });
    const counts = { discovered: 0, saved: 0, inspecting: 0, applied: 0, offered: 0 };

    allListings.forEach(item => {
        const st = item.status || 'discovered';
        if (cols[st]) {
            counts[st]++;
            const card = document.createElement('div');
            card.className = "property-card-touch bg-white p-3.5 rounded-2xl border border-slate-200 shadow-sm space-y-2 cursor-pointer hover:border-blue-400 transition";
            card.onclick = () => openListingModal(item.id);

            const isSale = item.listing_type === 'sale';
            card.innerHTML = `
                <div class="flex justify-between items-baseline">
                    <span class="font-extrabold text-slate-900">${isSale ? `$${item.price.toLocaleString()}` : `$${item.price}/wk`}</span>
                    <span class="text-[10px] font-bold text-slate-500 uppercase">${escapeHtml(item.suburb)}</span>
                </div>
                <p class="font-bold text-xs text-slate-800 truncate">${escapeHtml(item.street)}</p>
                <div class="text-[11px] text-slate-500 flex justify-between">
                    <span>${item.beds || 1}b • ${item.baths || 1}ba</span>
                    <span>${escapeHtml(item.prop_type || 'House')}</span>
                </div>
                ${item.notes ? `<p class="text-[10px] italic text-slate-600 bg-slate-50 p-1.5 rounded truncate">📝 ${escapeHtml(item.notes)}</p>` : ''}
            `;
            cols[st].appendChild(card);
        }
    });

    Object.keys(counts).forEach(k => {
        const el = document.getElementById(`kanban-${k}-count`);
        if (el) el.textContent = counts[k];
    });
}

// ==========================================
// 10. SUPER PORTALS GENERATOR
// ==========================================
async function loadPortalLinks() {
    try {
        const res = await fetch(`/api/portal-links?listing_type=${filters.mode}&suburb=${filters.suburb}`);
        const data = await res.json();
        const container = document.getElementById('portal-links-container');
        if (!container) return;

        container.innerHTML = (data.portals || []).map(p => `
            <a href="${p.url}" target="_blank" class="property-card-touch bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md hover:border-blue-400 transition flex flex-col justify-between group">
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-extrabold text-sm text-slate-900 group-hover:text-blue-600 transition">${escapeHtml(p.name)}</span>
                        <i data-lucide="external-link" class="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition"></i>
                    </div>
                    <p class="text-xs text-slate-500 leading-relaxed">${escapeHtml(p.tagline)}</p>
                </div>
                <div class="mt-4 pt-2.5 border-t border-slate-100 flex items-center text-xs font-bold text-blue-600">
                    <span>Search on ${escapeHtml(p.name)}</span>
                    <i data-lucide="arrow-right" class="w-3.5 h-3.5 ml-1"></i>
                </div>
            </a>
        `).join('');

        initIcons();
    } catch (e) {
        console.error("Error loading portals:", e);
    }
}

// ==========================================
// 11. VIEW SWITCHER
// ==========================================
function switchView(viewName) {
    currentTab = viewName;

    // Desktop top tabs
    document.querySelectorAll('.view-tab').forEach(t => {
        if (t.getAttribute('data-view') === viewName) {
            t.classList.add('active', 'bg-blue-600', 'text-white');
            t.classList.remove('bg-white', 'text-slate-600');
        } else {
            t.classList.remove('active', 'bg-blue-600', 'text-white');
            t.classList.add('bg-white', 'text-slate-600');
        }
    });

    // Mobile bottom nav
    document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
        if (btn.getAttribute('data-view') === viewName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Container visibility
    document.querySelectorAll('.tab-view').forEach(v => v.classList.add('hidden'));
    const target = document.getElementById(`view-${viewName}`);
    if (target) target.classList.remove('hidden');

    if (viewName === 'map') {
        setTimeout(initOrUpdateMap, 150);
    } else if (viewName === 'kanban') {
        renderKanban();
    } else if (viewName === 'portals') {
        loadPortalLinks();
    }

    initIcons();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==========================================
// 12. ADD CUSTOM PROPERTY (RENT OR BUY)
// ==========================================
async function handleAddRental(e) {
    e.preventDefault();
    const payload = {
        listing_type: document.getElementById('add-mode')?.value || 'rent',
        street: document.getElementById('add-street')?.value || '',
        suburb: document.getElementById('add-suburb')?.value || 'Nowra',
        state: document.getElementById('add-state')?.value || 'NSW',
        postcode: document.getElementById('add-postcode')?.value || '2541',
        price: parseInt(document.getElementById('add-price')?.value) || 0,
        beds: parseInt(document.getElementById('add-beds')?.value) || 1,
        baths: parseInt(document.getElementById('add-baths')?.value) || 1,
        cars: parseInt(document.getElementById('add-cars')?.value) || 1,
        prop_type: document.getElementById('add-type')?.value || 'House',
        url: document.getElementById('add-url')?.value || '',
        pets_allowed: document.getElementById('add-pets-allowed')?.checked ? 1 : 0
    };

    try {
        const res = await fetch(`/api/listings/add?user_id=${userToken}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            hideModal('modal-add');
            document.getElementById('form-add-rental')?.reset();
            showToast("Property added to your personal tracker!");
            fetchStats();
            fetchListings();
        }
    } catch (e) {
        showToast("Failed to add property.");
    }
}

// ==========================================
// 13. STATS & NOTIFICATIONS
// ==========================================
async function fetchStats() {
    try {
        const res = await fetch(`/api/stats?listing_type=${filters.mode}&user_id=${userToken}`);
        const s = await res.json();

        // Update shortlist header badge
        const savedBadge = document.getElementById('header-saved-count');
        if (savedBadge) savedBadge.textContent = s.favorites_count || 0;
    } catch (e) {
        console.error("Error fetching stats:", e);
    }
}

function showModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
    initIcons();
}

function hideModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    const msgEl = document.getElementById('toast-msg');
    if (!toast || !msgEl) return;

    msgEl.textContent = msg;
    toast.classList.remove('hidden');
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 4000);
}

function formatInspection(isoStr) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr);
        return d.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return isoStr;
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
