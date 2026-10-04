// 2541 Rental Radar Frontend Engine - Mobile & Desktop

let allListings = [];
let activeListing = null;
let leafletMap = null;
let markersGroup = null;
let landmarkGroup = null;
let currentTab = 'grid';

const filters = {
    max_price: 550,
    suburb: 'all',
    min_beds: 0,
    prop_type: 'all',
    query: '',
    sort_by: 'price_asc',
    only_inspections: false,
    only_favorites: false,
    only_pets: false
};

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    initIcons();
    initEventListeners();
    initMobileNav();
    initMobileFilters();
    initMobileChips();
    initCalculator();
    initBioGenerator();
    initTipsModal();
    loadSettings();
    loadPortals();
    fetchStats();
    fetchListings();
});

function initIcons() {
    if (window.lucide) {
        lucide.createIcons();
    }
}

// Event Listeners
function initEventListeners() {
    // Desktop Navigation Tabs
    document.querySelectorAll('.view-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const targetView = tab.getAttribute('data-view');
            switchView(targetView);
        });
    });

    // Suburb Pills
    document.querySelectorAll('.suburb-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.suburb-btn').forEach(b => {
                b.classList.remove('bg-blue-600', 'text-white', 'shadow-sm');
                b.classList.add('bg-slate-100', 'text-slate-700');
            });
            btn.classList.remove('bg-slate-100', 'text-slate-700');
            btn.classList.add('bg-blue-600', 'text-white', 'shadow-sm');

            filters.suburb = btn.getAttribute('data-suburb');
            updateActiveFilterBadge();
            fetchListings();
        });
    });

    // Desktop Filter controls
    const priceSlider = document.getElementById('filter-max-price');
    const priceVal = document.getElementById('price-slider-val');
    priceSlider?.addEventListener('input', (e) => {
        priceVal.textContent = `$${e.target.value}`;
        filters.max_price = parseInt(e.target.value);
        syncFilterControls();
        fetchListings();
    });

    document.getElementById('filter-beds')?.addEventListener('change', (e) => {
        filters.min_beds = parseInt(e.target.value);
        syncFilterControls();
        fetchListings();
    });

    document.getElementById('filter-prop-type')?.addEventListener('change', (e) => {
        filters.prop_type = e.target.value;
        syncFilterControls();
        fetchListings();
    });

    document.getElementById('filter-sort')?.addEventListener('change', (e) => {
        filters.sort_by = e.target.value;
        const mobSort = document.getElementById('filter-sort-mobile');
        if (mobSort) mobSort.value = e.target.value;
        fetchListings();
    });

    let searchTimeout;
    const searchInput = document.getElementById('filter-query');
    searchInput?.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            filters.query = e.target.value.trim();
            const mobSearch = document.getElementById('filter-query-mobile');
            if (mobSearch) mobSearch.value = e.target.value;
            syncMobileSearchClearBtn();
            updateActiveFilterBadge();
            fetchListings();
        }, 300);
    });

    // Mobile Search Input
    const mobSearchInput = document.getElementById('filter-query-mobile');
    const mobClearBtn = document.getElementById('btn-clear-search-mobile');
    mobSearchInput?.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        syncMobileSearchClearBtn();
        searchTimeout = setTimeout(() => {
            filters.query = e.target.value.trim();
            if (searchInput) searchInput.value = e.target.value;
            updateActiveFilterBadge();
            fetchListings();
        }, 300);
    });

    mobClearBtn?.addEventListener('click', () => {
        if (mobSearchInput) mobSearchInput.value = '';
        if (searchInput) searchInput.value = '';
        filters.query = '';
        syncMobileSearchClearBtn();
        updateActiveFilterBadge();
        fetchListings();
    });

    // Mobile Sort Dropdown
    document.getElementById('filter-sort-mobile')?.addEventListener('change', (e) => {
        filters.sort_by = e.target.value;
        const deskSort = document.getElementById('filter-sort');
        if (deskSort) deskSort.value = e.target.value;
        fetchListings();
    });

    document.getElementById('filter-only-pets')?.addEventListener('change', (e) => {
        filters.only_pets = e.target.checked;
        syncFilterControls();
        fetchListings();
    });

    document.getElementById('filter-only-inspections')?.addEventListener('change', (e) => {
        filters.only_inspections = e.target.checked;
        syncFilterControls();
        fetchListings();
    });

    document.getElementById('filter-only-favorites')?.addEventListener('change', (e) => {
        filters.only_favorites = e.target.checked;
        syncFilterControls();
        fetchListings();
    });

    document.getElementById('btn-reset-filters')?.addEventListener('click', resetFilters);

    // Header buttons
    document.getElementById('btn-refresh')?.addEventListener('click', syncLive);
    document.getElementById('btn-add-modal')?.addEventListener('click', () => showModal('modal-add'));
    document.getElementById('btn-settings-modal')?.addEventListener('click', () => showModal('modal-settings'));
    document.getElementById('btn-print')?.addEventListener('click', printRunSheet);
    document.getElementById('btn-export-csv')?.addEventListener('click', () => {
        window.location.href = `/api/export/csv?max_price=${filters.max_price}`;
    });

    // Modal close buttons
    document.getElementById('modal-close-btn')?.addEventListener('click', () => hideModal('modal-property'));
    document.getElementById('modal-add-close')?.addEventListener('click', () => hideModal('modal-add'));
    document.getElementById('modal-add-cancel')?.addEventListener('click', () => hideModal('modal-add'));
    document.getElementById('modal-settings-close')?.addEventListener('click', () => hideModal('modal-settings'));
    document.getElementById('modal-settings-cancel')?.addEventListener('click', () => hideModal('modal-settings'));

    // Save Listing Meta
    document.getElementById('modal-save-btn')?.addEventListener('click', saveActiveListingMeta);
    document.getElementById('modal-fav-btn')?.addEventListener('click', toggleActiveFavorite);

    // Add Custom Rental Form
    document.getElementById('form-add-rental')?.addEventListener('submit', handleAddRental);

    // Save Settings
    document.getElementById('modal-settings-save')?.addEventListener('click', handleSaveSettings);
    document.getElementById('btn-request-notify')?.addEventListener('click', requestBrowserNotification);

    // Landmark toggles
    document.getElementById('toggle-train')?.addEventListener('click', () => panToLandmark(-34.8517, 150.6120, "Bomaderry Railway Station (Trains to Sydney)"));
    document.getElementById('toggle-hospital')?.addEventListener('click', () => panToLandmark(-34.8765, 150.5985, "Shoalhaven District Memorial Hospital"));
    document.getElementById('toggle-shops')?.addEventListener('click', () => panToLandmark(-34.8745, 150.6025, "Stockland Nowra Shopping Centre"));

    // GPS Locate Me Button on Map
    document.getElementById('btn-locate-me')?.addEventListener('click', handleLocateUser);

    // Mobile Map Peek Card Close Button
    document.getElementById('map-peek-close')?.addEventListener('click', () => {
        document.getElementById('map-card-peek')?.classList.add('hidden');
    });

    // Mobile Kanban Stage Switcher Tabs
    document.querySelectorAll('.kanban-stage-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const stage = tab.getAttribute('data-stage');
            document.querySelectorAll('.kanban-stage-tab').forEach(t => {
                t.classList.remove('bg-blue-600', 'text-white', 'shadow-sm');
                t.classList.add('bg-slate-100', 'text-slate-700');
            });
            tab.classList.remove('bg-slate-100', 'text-slate-700');
            tab.classList.add('bg-blue-600', 'text-white', 'shadow-sm');

            const targetCol = document.querySelector(`.kanban-col-wrapper[data-col="${stage}"]`);
            if (targetCol) {
                targetCol.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
            }
        });
    });
}

function syncMobileSearchClearBtn() {
    const mobSearchInput = document.getElementById('filter-query-mobile');
    const mobClearBtn = document.getElementById('btn-clear-search-mobile');
    if (!mobSearchInput || !mobClearBtn) return;
    if (mobSearchInput.value.length > 0) {
        mobClearBtn.classList.remove('hidden');
    } else {
        mobClearBtn.classList.add('hidden');
    }
}

// Mobile Bottom Nav & Floating View Switcher
function initMobileNav() {
    document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetView = btn.getAttribute('data-view');
            switchView(targetView);
        });
    });

    const floatingToggle = document.getElementById('floating-view-toggle');
    floatingToggle?.addEventListener('click', () => {
        if (currentTab === 'grid') {
            switchView('map');
        } else {
            switchView('grid');
        }
    });
}

// Mobile Filter Bottom Sheet
function initMobileFilters() {
    const btnOpen = document.getElementById('btn-open-mobile-filters');
    const btnClose = document.getElementById('btn-mobile-filters-close');
    const btnApply = document.getElementById('btn-mobile-apply-filters');
    const btnReset = document.getElementById('btn-mobile-reset-filters');
    const sheetPrice = document.getElementById('mobile-sheet-price');
    const sheetPriceVal = document.getElementById('mobile-sheet-price-val');

    btnOpen?.addEventListener('click', () => {
        // Populate current filter values into sheet
        if (sheetPrice) sheetPrice.value = filters.max_price;
        if (sheetPriceVal) sheetPriceVal.textContent = `$${filters.max_price}`;
        
        document.querySelectorAll('.sheet-bed-btn').forEach(btn => {
            const val = parseInt(btn.getAttribute('data-val'));
            if (val === filters.min_beds) {
                btn.classList.add('bg-blue-600', 'text-white', 'shadow-sm');
                btn.classList.remove('bg-slate-50', 'text-slate-700');
            } else {
                btn.classList.remove('bg-blue-600', 'text-white', 'shadow-sm');
                btn.classList.add('bg-slate-50', 'text-slate-700');
            }
        });

        const propSelect = document.getElementById('mobile-sheet-prop-type');
        if (propSelect) propSelect.value = filters.prop_type;

        const petsCheck = document.getElementById('mobile-sheet-pets');
        if (petsCheck) petsCheck.checked = filters.only_pets;

        const inspCheck = document.getElementById('mobile-sheet-insp');
        if (inspCheck) inspCheck.checked = filters.only_inspections;

        const favCheck = document.getElementById('mobile-sheet-fav');
        if (favCheck) favCheck.checked = filters.only_favorites;

        showModal('modal-mobile-filters');
        initIcons();
    });

    btnClose?.addEventListener('click', () => hideModal('modal-mobile-filters'));

    sheetPrice?.addEventListener('input', (e) => {
        if (sheetPriceVal) sheetPriceVal.textContent = `$${e.target.value}`;
    });

    document.querySelectorAll('.sheet-bed-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.sheet-bed-btn').forEach(b => {
                b.classList.remove('bg-blue-600', 'text-white', 'shadow-sm');
                b.classList.add('bg-slate-50', 'text-slate-700');
            });
            btn.classList.remove('bg-slate-50', 'text-slate-700');
            btn.classList.add('bg-blue-600', 'text-white', 'shadow-sm');
        });
    });

    btnApply?.addEventListener('click', () => {
        if (sheetPrice) filters.max_price = parseInt(sheetPrice.value);
        
        const activeBedBtn = document.querySelector('.sheet-bed-btn.bg-blue-600');
        if (activeBedBtn) filters.min_beds = parseInt(activeBedBtn.getAttribute('data-val'));

        const propSelect = document.getElementById('mobile-sheet-prop-type');
        if (propSelect) filters.prop_type = propSelect.value;

        const petsCheck = document.getElementById('mobile-sheet-pets');
        if (petsCheck) filters.only_pets = petsCheck.checked;

        const inspCheck = document.getElementById('mobile-sheet-insp');
        if (inspCheck) filters.only_inspections = inspCheck.checked;

        const favCheck = document.getElementById('mobile-sheet-fav');
        if (favCheck) filters.only_favorites = favCheck.checked;

        syncDesktopFiltersFromState();
        updateActiveFilterBadge();
        hideModal('modal-mobile-filters');
        fetchListings();
    });

    btnReset?.addEventListener('click', () => {
        resetFilters();
        hideModal('modal-mobile-filters');
    });
}

// Mobile 1-Tap Filter Chips
function initMobileChips() {
    document.querySelectorAll('.mobile-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const type = chip.getAttribute('data-chip');
            if (type === 'pets') {
                filters.only_pets = !filters.only_pets;
            } else if (type === 'insp') {
                filters.only_inspections = !filters.only_inspections;
            } else if (type === 'fav') {
                filters.only_favorites = !filters.only_favorites;
            } else if (type === 'price-450') {
                filters.max_price = (filters.max_price === 450) ? 550 : 450;
            } else if (type === 'beds-2') {
                filters.min_beds = (filters.min_beds === 2) ? 0 : 2;
            } else if (type === 'beds-3') {
                filters.min_beds = (filters.min_beds === 3) ? 0 : 3;
            }
            syncFilterControls();
            fetchListings();
        });
    });
}

function updateChipVisualStates() {
    document.querySelectorAll('.mobile-chip').forEach(chip => {
        const type = chip.getAttribute('data-chip');
        let isActive = false;
        if (type === 'pets') isActive = filters.only_pets;
        else if (type === 'insp') isActive = filters.only_inspections;
        else if (type === 'fav') isActive = filters.only_favorites;
        else if (type === 'price-450') isActive = (filters.max_price === 450);
        else if (type === 'beds-2') isActive = (filters.min_beds === 2);
        else if (type === 'beds-3') isActive = (filters.min_beds === 3);

        if (isActive) {
            chip.classList.add('bg-blue-600', 'text-white', 'border-blue-600', 'shadow-xs');
            chip.classList.remove('bg-slate-50', 'text-slate-700', 'border-slate-200');
        } else {
            chip.classList.remove('bg-blue-600', 'text-white', 'border-blue-600', 'shadow-xs');
            chip.classList.add('bg-slate-50', 'text-slate-700', 'border-slate-200');
        }
    });
}

function updateActiveFilterBadge() {
    let count = 0;
    if (filters.max_price !== 550) count++;
    if (filters.suburb !== 'all') count++;
    if (filters.min_beds > 0) count++;
    if (filters.prop_type !== 'all') count++;
    if (filters.query && filters.query.length > 0) count++;
    if (filters.only_pets) count++;
    if (filters.only_inspections) count++;
    if (filters.only_favorites) count++;

    const badge = document.getElementById('mobile-filter-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }
    updateChipVisualStates();
}

function syncFilterControls() {
    syncDesktopFiltersFromState();
    updateActiveFilterBadge();
}

function syncDesktopFiltersFromState() {
    const priceSlider = document.getElementById('filter-max-price');
    const priceVal = document.getElementById('price-slider-val');
    if (priceSlider) priceSlider.value = filters.max_price;
    if (priceVal) priceVal.textContent = `$${filters.max_price}`;

    const beds = document.getElementById('filter-beds');
    if (beds) beds.value = filters.min_beds;

    const prop = document.getElementById('filter-prop-type');
    if (prop) prop.value = filters.prop_type;

    const pets = document.getElementById('filter-only-pets');
    if (pets) pets.checked = filters.only_pets;

    const mobPets = document.getElementById('mobile-sheet-pets');
    if (mobPets) mobPets.checked = filters.only_pets;

    const insp = document.getElementById('filter-only-inspections');
    if (insp) insp.checked = filters.only_inspections;

    const fav = document.getElementById('filter-only-favorites');
    if (fav) fav.checked = filters.only_favorites;

    const sortDesk = document.getElementById('filter-sort');
    if (sortDesk) sortDesk.value = filters.sort_by;

    const sortMob = document.getElementById('filter-sort-mobile');
    if (sortMob) sortMob.value = filters.sort_by;
}

function switchView(viewName) {
    currentTab = viewName;

    // Desktop top tabs
    document.querySelectorAll('.view-tab').forEach(t => {
        if (t.getAttribute('data-view') === viewName) {
            t.classList.add('border-blue-600', 'text-blue-600');
            t.classList.remove('border-transparent', 'text-slate-500');
        } else {
            t.classList.remove('border-blue-600', 'text-blue-600');
            t.classList.add('border-transparent', 'text-slate-500');
        }
    });

    // Mobile bottom navigation buttons
    document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
        if (btn.getAttribute('data-view') === viewName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Views container visibility
    document.querySelectorAll('.tab-view').forEach(v => v.classList.add('hidden'));
    const target = document.getElementById(`view-${viewName}`);
    if (target) target.classList.remove('hidden');

    // Update Mobile Header View Title
    const mobTitle = document.getElementById('mobile-view-title');
    if (mobTitle) {
        const titles = {
            grid: '<i data-lucide="home" class="w-4 h-4 mr-1.5 text-blue-600"></i><span>Available Rentals in 2541</span>',
            map: '<i data-lucide="map" class="w-4 h-4 mr-1.5 text-blue-600"></i><span>2541 Interactive Map</span>',
            kanban: '<i data-lucide="kanban" class="w-4 h-4 mr-1.5 text-blue-600"></i><span>Application Pipeline</span>',
            portals: '<i data-lucide="external-link" class="w-4 h-4 mr-1.5 text-blue-600"></i><span>Super Search Portals</span>',
            toolkit: '<i data-lucide="calculator" class="w-4 h-4 mr-1.5 text-blue-600"></i><span>Tenant Toolkit & Calculator</span>'
        };
        mobTitle.innerHTML = titles[viewName] || '';
    }

    // Floating Map / List Toggle Button State
    const floatingToggle = document.getElementById('floating-view-toggle');
    const floatingIcon = document.getElementById('floating-toggle-icon');
    const floatingText = document.getElementById('floating-toggle-text');

    if (floatingToggle && floatingIcon && floatingText) {
        if (viewName === 'grid') {
            floatingToggle.classList.remove('hidden');
            floatingIcon.setAttribute('data-lucide', 'map');
            floatingText.textContent = 'View Map';
        } else if (viewName === 'map') {
            floatingToggle.classList.remove('hidden');
            floatingIcon.setAttribute('data-lucide', 'layout-grid');
            floatingText.textContent = 'View List';
        } else {
            floatingToggle.classList.add('hidden');
        }
    }

    if (viewName === 'map') {
        setTimeout(initOrUpdateMap, 150);
    } else if (viewName === 'kanban') {
        renderKanban();
    }

    initIcons();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Fetch Listings from API
async function fetchListings() {
    try {
        const params = new URLSearchParams();
        params.append('max_price', filters.max_price);
        if (filters.suburb !== 'all') params.append('suburb', filters.suburb);
        if (filters.min_beds > 0) params.append('min_beds', filters.min_beds);
        if (filters.prop_type !== 'all') params.append('prop_type', filters.prop_type);
        if (filters.query) params.append('query', filters.query);
        params.append('sort_by', filters.sort_by);
        if (filters.only_inspections) params.append('only_inspections', 'true');
        if (filters.only_favorites) params.append('only_favorites', 'true');
        if (filters.only_pets) params.append('only_pets', 'true');

        const res = await fetch(`/api/listings?${params.toString()}`);
        const data = await res.json();
        allListings = data.listings || [];

        const resultsCountEl = document.getElementById('results-count');
        if (resultsCountEl) resultsCountEl.textContent = allListings.length;

        const mobileResultsEl = document.getElementById('mobile-results-count');
        if (mobileResultsEl) mobileResultsEl.textContent = `${allListings.length} listings`;

        const bottomNavResultsEl = document.getElementById('bottom-nav-results');
        if (bottomNavResultsEl) bottomNavResultsEl.textContent = allListings.length;

        renderListingsGrid(allListings);

        if (currentTab === 'map') {
            initOrUpdateMap();
        } else if (currentTab === 'kanban') {
            renderKanban();
        }

        initIcons();
    } catch (e) {
        console.error("Error fetching listings:", e);
        showToast("Error loading listings. Make sure the server is running.");
    }
}

// Render Property Grid Cards
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
    const priceColor = item.price <= 450 ? 'text-emerald-700 bg-emerald-50' : (item.price <= 500 ? 'text-blue-700 bg-blue-50' : 'text-amber-800 bg-amber-50');
    const fallbackImg = "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=600&q=80";
    const imgUrl = item.image_url || fallbackImg;

    // Inspection badge
    let inspBadge = '';
    if (item.inspection_date) {
        inspBadge = `
            <div class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
                <i data-lucide="calendar" class="w-3 h-3 mr-1 text-indigo-500"></i>
                <span>Open: ${formatInspection(item.inspection_date)}</span>
            </div>
        `;
    }

    // New Badge
    const newBadge = item.is_new ? `
        <span class="absolute top-2.5 left-2.5 px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-emerald-600 text-white shadow-md tracking-wider">
            NEW
        </span>
    ` : '';

    const favColor = item.is_favorite ? 'text-rose-500 fill-current' : 'text-slate-400 hover:text-rose-500';

    return `
        <div class="property-card-touch bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden flex flex-col group" data-id="${item.id}">
            <!-- Card Image -->
            <div class="relative h-44 sm:h-48 bg-slate-100 overflow-hidden cursor-pointer" onclick="openListingModal('${item.id}')">
                <img src="${imgUrl}" alt="${escapeHtml(item.street)}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" onerror="this.src='${fallbackImg}'">
                ${newBadge}
                <button onclick="event.stopPropagation(); quickToggleFav('${item.id}')" class="absolute top-2.5 right-2.5 w-9 h-9 rounded-full bg-white/95 hover:bg-white flex items-center justify-center shadow-md transition active:scale-90" title="Shortlist / Save">
                    <i data-lucide="heart" class="w-4 h-4 ${favColor}"></i>
                </button>
                <div class="absolute bottom-2.5 left-2.5 flex items-center space-x-1.5">
                    <span class="px-2 py-0.5 rounded-md text-[10px] sm:text-[11px] font-bold uppercase bg-slate-900/80 text-white backdrop-blur-sm">
                        ${escapeHtml(item.prop_type || 'Rental')}
                    </span>
                    <span class="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-blue-600/90 text-white backdrop-blur-sm">
                        ${escapeHtml(item.source || 'Portal')}
                    </span>
                </div>
            </div>

            <!-- Card Content -->
            <div class="p-3.5 sm:p-4 flex-1 flex flex-col justify-between space-y-3">
                <div>
                    <!-- Price and Suburb -->
                    <div class="flex items-baseline justify-between">
                        <span class="text-xl sm:text-2xl font-extrabold text-slate-900">$${item.price || '--'}<span class="text-xs font-normal text-slate-500"> /wk</span></span>
                        <span class="text-[11px] sm:text-xs font-bold px-2 py-0.5 rounded-full ${priceColor}">
                            ${item.price <= 450 ? 'Bargain' : (item.price <= 500 ? 'Great Value' : 'Under $550')}
                        </span>
                    </div>

                    <!-- Address -->
                    <h3 class="font-bold text-xs sm:text-sm text-slate-900 mt-1 cursor-pointer hover:text-blue-600 transition truncate" onclick="openListingModal('${item.id}')" title="${escapeHtml(item.street)}, ${escapeHtml(item.suburb)}">
                        ${escapeHtml(item.street)}
                    </h3>
                    <p class="text-xs text-slate-500 flex items-center mt-0.5">
                        <i data-lucide="map-pin" class="w-3 h-3 mr-1 text-slate-400 flex-shrink-0"></i>
                        <span>${escapeHtml(item.suburb)} NSW ${item.postcode || '2541'}</span>
                    </p>

                    <!-- Features -->
                    <div class="flex items-center space-x-3 sm:space-x-4 mt-2.5 pt-2.5 border-t border-slate-100 text-xs text-slate-600">
                        <span class="flex items-center font-medium" title="Bedrooms">
                            <i data-lucide="bed" class="w-3.5 h-3.5 mr-1 text-slate-400"></i> ${item.beds || 1} Bed
                        </span>
                        <span class="flex items-center font-medium" title="Bathrooms">
                            <i data-lucide="bath" class="w-3.5 h-3.5 mr-1 text-slate-400"></i> ${item.baths || 1} Bath
                        </span>
                        <span class="flex items-center font-medium" title="Parking / Car spaces">
                            <i data-lucide="car" class="w-3.5 h-3.5 mr-1 text-slate-400"></i> ${item.cars || 0} Car
                        </span>
                    </div>

                    <!-- Inspection / Badges -->
                    <div class="mt-2 flex flex-wrap gap-1.5 items-center">
                        ${inspBadge}
                        ${item.pets_allowed ? `
                            <div class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
                                <i data-lucide="paw-print" class="w-3 h-3 mr-1 text-emerald-600"></i>
                                <span>Pets OK</span>
                            </div>
                        ` : ''}
                    </div>
                </div>

                <!-- Footer Actions -->
                <div class="pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
                    <!-- Status selector -->
                    <select onchange="updateListingStatus('${item.id}', this.value)" class="text-[11px] font-semibold py-1 px-2 border border-slate-200 rounded-lg bg-slate-50 text-slate-700 hover:bg-slate-100 transition focus:outline-none">
                        <option value="discovered" ${item.status === 'discovered' ? 'selected' : ''}>🔍 Discovered</option>
                        <option value="saved" ${item.status === 'saved' ? 'selected' : ''}>⭐ Shortlisted</option>
                        <option value="inspecting" ${item.status === 'inspecting' ? 'selected' : ''}>📅 Inspecting</option>
                        <option value="applied" ${item.status === 'applied' ? 'selected' : ''}>📝 Applied</option>
                        <option value="offered" ${item.status === 'offered' ? 'selected' : ''}>🎉 Offered</option>
                    </select>

                    <button onclick="openListingModal('${item.id}')" class="font-bold text-blue-600 hover:text-blue-800 transition flex items-center p-1 active:scale-95">
                        <span>Details</span>
                        <i data-lucide="chevron-right" class="w-3.5 h-3.5 ml-0.5"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Leaflet Map Logic
function initOrUpdateMap() {
    const mapContainer = document.getElementById('map');
    if (!mapContainer) return;

    if (!leafletMap) {
        // Center on Nowra CBD
        leafletMap = L.map('map', { zoomControl: false }).setView([-34.8727, 150.6019], 13);
        L.control.zoom({ position: 'bottomright' }).addTo(leafletMap);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(leafletMap);

        markersGroup = L.layerGroup().addTo(leafletMap);
        landmarkGroup = L.layerGroup().addTo(leafletMap);

        addLandmarks();
    }

    leafletMap.invalidateSize();
    markersGroup.clearLayers();

    const bounds = [];

    allListings.forEach(item => {
        if (!item.lat || !item.lng) return;

        const pinClass = item.price <= 450 ? 'pin-green' : (item.price <= 500 ? 'pin-blue' : 'pin-amber');
        const customIcon = L.divIcon({
            className: `custom-price-pin ${pinClass}`,
            html: `<span>$${item.price || '?'}</span>`,
            iconSize: [52, 26],
            iconAnchor: [26, 13]
        });

        const marker = L.marker([item.lat, item.lng], { icon: customIcon });

        // On mobile, clicking marker triggers the bottom preview peek card
        marker.on('click', () => {
            if (window.innerWidth < 640) {
                showMobileMapPeek(item);
            }
        });

        const popupContent = `
            <div style="width: 220px;" class="p-2 space-y-1 text-xs">
                ${item.image_url ? `<img src="${item.image_url}" class="w-full h-24 object-cover rounded-lg mb-2">` : ''}
                <div class="flex justify-between items-center">
                    <span class="font-bold text-sm text-slate-900">$${item.price}/wk</span>
                    <span class="text-[10px] uppercase font-bold text-slate-500">${escapeHtml(item.suburb)}</span>
                </div>
                <p class="font-semibold text-slate-800 truncate">${escapeHtml(item.street)}</p>
                <p class="text-slate-500">${item.beds || 1}b • ${item.baths || 1}ba • ${item.cars || 0}c (${escapeHtml(item.prop_type || 'House')})</p>
                ${item.inspection_date ? `<p class="text-indigo-600 font-medium">📅 ${formatInspection(item.inspection_date)}</p>` : ''}
                <button onclick="openListingModal('${item.id}')" class="w-full mt-2 py-1.5 bg-blue-600 text-white rounded font-bold text-center block active:scale-95 transition">
                    View Details
                </button>
            </div>
        `;

        marker.bindPopup(popupContent);
        markersGroup.addLayer(marker);
        bounds.push([item.lat, item.lng]);
    });

    if (bounds.length > 0) {
        leafletMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }
}

function showMobileMapPeek(item) {
    const peekCard = document.getElementById('map-card-peek');
    const peekImg = document.getElementById('map-peek-img');
    const peekPrice = document.getElementById('map-peek-price');
    const peekStreet = document.getElementById('map-peek-street');
    const peekMeta = document.getElementById('map-peek-meta');
    const peekBtn = document.getElementById('map-peek-btn');

    if (!peekCard) return;

    const fallbackImg = "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=400&q=80";
    if (peekImg) peekImg.src = item.image_url || fallbackImg;
    if (peekPrice) peekPrice.textContent = `$${item.price}/wk`;
    if (peekStreet) peekStreet.textContent = item.street;
    if (peekMeta) peekMeta.textContent = `${item.beds || 1}b • ${item.baths || 1}ba • ${item.suburb}`;
    if (peekBtn) peekBtn.onclick = () => openListingModal(item.id);

    peekCard.classList.remove('hidden');
    initIcons();
}

function handleLocateUser() {
    if (!("geolocation" in navigator)) {
        showToast("Geolocation is not supported by your browser.");
        return;
    }

    showToast("Finding your current location in 2541...");
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const { latitude, longitude } = pos.coords;
            if (leafletMap) {
                leafletMap.setView([latitude, longitude], 15, { animate: true });
                if (window.userLocationMarker) {
                    window.userLocationMarker.setLatLng([latitude, longitude]);
                } else {
                    window.userLocationMarker = L.circleMarker([latitude, longitude], {
                        radius: 8,
                        color: '#2563eb',
                        fillColor: '#3b82f6',
                        fillOpacity: 0.9,
                        weight: 3
                    }).addTo(leafletMap).bindPopup("<b>📍 You are here</b>").openPopup();
                }
                showToast("Centered on your current location!");
            }
        },
        (err) => {
            showToast("Could not get location. Check GPS permissions.");
        },
        { enableHighAccuracy: true, timeout: 8000 }
    );
}

function addLandmarks() {
    const landmarks = [
        { name: "🚆 Bomaderry Railway Station", lat: -34.8517, lng: 150.6120, desc: "Direct South Coast train link to Sydney Central" },
        { name: "🏥 Shoalhaven District Hospital", lat: -34.8765, lng: 150.5985, desc: "Shoalhaven Memorial Hospital & Health Services" },
        { name: "🛍️ Stockland Nowra", lat: -34.8745, lng: 150.6025, desc: "Central shopping mall, Woolworths, Kmart, stores" },
        { name: "🎓 UOW Shoalhaven Campus", lat: -34.8967, lng: 150.5790, desc: "University of Wollongong campus (West Nowra)" },
        { name: "🚌 Nowra Bus Interchange", lat: -34.8755, lng: 150.6040, desc: "Stewart Place regional bus connections" }
    ];

    landmarks.forEach(l => {
        const marker = L.circleMarker([l.lat, l.lng], {
            radius: 7,
            color: '#dc2626',
            fillColor: '#ef4444',
            fillOpacity: 0.9,
            weight: 2
        });
        marker.bindPopup(`<b>${l.name}</b><br><small class="text-slate-600">${l.desc}</small>`);
        landmarkGroup.addLayer(marker);
    });
}

function panToLandmark(lat, lng, name) {
    if (leafletMap) {
        leafletMap.setView([lat, lng], 15, { animate: true });
        showToast(`Centered on ${name}`);
    }
}

// Kanban Board Renderer
function renderKanban() {
    const cols = {
        discovered: document.getElementById('kanban-discovered'),
        saved: document.getElementById('kanban-saved'),
        inspecting: document.getElementById('kanban-inspecting'),
        applied: document.getElementById('kanban-applied'),
        offered: document.getElementById('kanban-offered')
    };

    // Clear columns
    Object.values(cols).forEach(c => { if (c) c.innerHTML = ''; });

    const counts = { discovered: 0, saved: 0, inspecting: 0, applied: 0, offered: 0 };

    allListings.forEach(item => {
        const st = item.status || 'discovered';
        if (cols[st]) {
            counts[st]++;
            const card = document.createElement('div');
            card.className = "property-card-touch bg-white p-3 rounded-xl border border-slate-200 shadow-sm space-y-2 cursor-pointer hover:border-blue-400 transition";
            card.onclick = () => openListingModal(item.id);

            card.innerHTML = `
                <div class="flex justify-between items-baseline">
                    <span class="font-extrabold text-slate-900">$${item.price}/wk</span>
                    <span class="text-[10px] font-bold text-slate-500 uppercase">${escapeHtml(item.suburb)}</span>
                </div>
                <p class="font-semibold text-xs text-slate-800 truncate">${escapeHtml(item.street)}</p>
                <div class="text-[11px] text-slate-500 flex justify-between">
                    <span>${item.beds || 1}b • ${item.baths || 1}ba</span>
                    <span>${escapeHtml(item.prop_type || 'House')}</span>
                </div>
                ${item.inspection_date ? `<div class="text-[10px] font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">📅 ${formatInspection(item.inspection_date)}</div>` : ''}
            `;
            cols[st].appendChild(card);
        }
    });

    Object.keys(counts).forEach(k => {
        const el = document.getElementById(`kanban-${k}-count`);
        if (el) el.textContent = counts[k];

        const tabCnt = document.getElementById(`tab-cnt-${k}`);
        if (tabCnt) tabCnt.textContent = counts[k];
    });
}

// Listing Details Modal
function openListingModal(listingId) {
    const item = allListings.find(l => l.id == listingId);
    if (!item) return;

    activeListing = item;
    const fallbackImg = "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=800&q=80";

    const modalImg = document.getElementById('modal-img');
    if (modalImg) modalImg.src = item.image_url || fallbackImg;

    const modalPrice = document.getElementById('modal-price');
    if (modalPrice) modalPrice.innerHTML = `$${item.price || '--'} <span class="text-xs sm:text-base font-normal text-slate-200">/ week</span>`;

    const modalAddress = document.getElementById('modal-address');
    if (modalAddress) modalAddress.textContent = `${item.street}, ${item.suburb} NSW ${item.postcode || '2541'}`;

    const modalType = document.getElementById('modal-type-badge');
    if (modalType) modalType.textContent = item.prop_type || 'Property';

    const modalBeds = document.getElementById('modal-beds');
    if (modalBeds) modalBeds.textContent = item.beds || 1;

    const modalBaths = document.getElementById('modal-baths');
    if (modalBaths) modalBaths.textContent = item.baths || 1;

    const modalCars = document.getElementById('modal-cars');
    if (modalCars) modalCars.textContent = item.cars || 0;

    const modalBond = document.getElementById('modal-bond');
    if (modalBond) modalBond.textContent = `$${(item.price || 0) * 4}`;

    const modalDesc = document.getElementById('modal-desc');
    if (modalDesc) modalDesc.textContent = item.description || "No full description provided.";

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

    // Pet Policy Box
    const petBox = document.getElementById('modal-pet-box');
    const petText = document.getElementById('modal-pet-text');
    const petBadge = document.getElementById('modal-pet-badge');
    const petIconWrap = document.getElementById('modal-pet-icon-wrap');
    if (petBox && petText && petBadge) {
        if (item.pets_allowed) {
            petText.textContent = "Pets Allowed / Considered Upon Application";
            petText.className = "text-xs font-bold text-emerald-700";
            petBadge.textContent = "Pet Friendly";
            petBadge.className = "px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800";
            if (petIconWrap) petIconWrap.className = "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-emerald-100 text-emerald-700";
        } else {
            petText.textContent = "No pets specified or subject to landlord discretion";
            petText.className = "text-xs font-medium text-slate-600";
            petBadge.textContent = "Check with Agent";
            petBadge.className = "px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600";
            if (petIconWrap) petIconWrap.className = "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-slate-100 text-slate-500";
        }
    }

    // Google Maps Link
    const q = encodeURIComponent(`${item.street}, ${item.suburb} NSW 2541`);
    const mapsLink = document.getElementById('modal-maps-link');
    if (mapsLink) mapsLink.href = `https://www.google.com/maps/search/?api=1&query=${q}`;

    // External Portal Link
    const portalLink = document.getElementById('modal-portal-link');
    if (portalLink) portalLink.href = item.url;

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

    await fetch(`/api/listings/${activeListing.id}/meta`, {
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

    await fetch(`/api/listings/${lid}/meta`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_favorite: newFav })
    });
    fetchStats();
    fetchListings();
}

async function updateListingStatus(lid, newStatus) {
    await fetch(`/api/listings/${lid}/meta`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
    });
    const item = allListings.find(l => l.id == lid);
    if (item) item.status = newStatus;
    showToast(`Updated status to ${newStatus}`);
    fetchStats();
    if (currentTab === 'kanban') renderKanban();
}

async function saveActiveListingMeta() {
    if (!activeListing) return;
    const newStatus = document.getElementById('modal-status-select').value;
    const newNotes = document.getElementById('modal-notes').value;
    const newRating = parseInt(document.getElementById('modal-rating-select').value);

    await fetch(`/api/listings/${activeListing.id}/meta`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            status: newStatus,
            notes: newNotes,
            rating: newRating
        })
    });

    activeListing.status = newStatus;
    activeListing.notes = newNotes;
    activeListing.rating = newRating;

    hideModal('modal-property');
    showToast("Changes saved successfully!");
    fetchListings();
}

// Sync Live Scraper
async function syncLive() {
    const icon = document.getElementById('refresh-icon');
    if (icon) icon.classList.add('animate-spin');

    try {
        showToast("Checking for new 2541 listings...");
        const res = await fetch('/api/listings/refresh', { method: 'POST' });
        const data = await res.json();

        if (data.newly_added > 0) {
            playChime();
            showToast(`🎉 Found ${data.newly_added} new rental(s) in 2541!`);
            sendDesktopNotification(`2541 Rental Radar`, `Found ${data.newly_added} new rental(s) under $550/wk!`);
        } else {
            showToast(`Sync complete: ${data.scraped} properties checked, up to date.`);
        }

        fetchStats();
        fetchListings();
    } catch (e) {
        showToast("Sync failed. Check connection.");
    } finally {
        if (icon) icon.classList.remove('animate-spin');
    }
}

// Add Custom Rental
async function handleAddRental(e) {
    e.preventDefault();
    const payload = {
        street: document.getElementById('add-street').value,
        suburb: document.getElementById('add-suburb').value,
        price: parseInt(document.getElementById('add-price').value),
        beds: parseInt(document.getElementById('add-beds').value),
        baths: parseInt(document.getElementById('add-baths').value),
        cars: parseInt(document.getElementById('add-cars').value),
        prop_type: document.getElementById('add-type').value,
        url: document.getElementById('add-url').value,
        image_url: document.getElementById('add-image').value,
        notes: document.getElementById('add-notes').value,
        pets_allowed: document.getElementById('add-pets-allowed')?.checked ? 1 : 0
    };

    try {
        const res = await fetch('/api/listings/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            hideModal('modal-add');
            document.getElementById('form-add-rental').reset();
            showToast("Custom rental added to your tracker!");
            fetchStats();
            fetchListings();
        }
    } catch (e) {
        showToast("Failed to add custom rental.");
    }
}

// Settings & Preferences
async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        if (data.max_price && document.getElementById('setting-max-price')) {
            document.getElementById('setting-max-price').value = data.max_price;
        }
        if (data.auto_refresh_interval && document.getElementById('setting-refresh-interval')) {
            document.getElementById('setting-refresh-interval').value = data.auto_refresh_interval;
        }
        if (data.webhook_url && document.getElementById('setting-webhook-url')) {
            document.getElementById('setting-webhook-url').value = data.webhook_url;
        }
        if (data.sound_enabled && document.getElementById('setting-sound')) {
            document.getElementById('setting-sound').checked = data.sound_enabled === 'true';
        }
    } catch (e) {}
}

async function handleSaveSettings() {
    const payload = {
        max_price: document.getElementById('setting-max-price').value,
        auto_refresh_interval: document.getElementById('setting-refresh-interval').value,
        webhook_url: document.getElementById('setting-webhook-url').value,
        sound_enabled: document.getElementById('setting-sound').checked ? 'true' : 'false'
    };

    try {
        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        hideModal('modal-settings');
        showToast("Preferences saved!");
    } catch (e) {
        showToast("Failed to save settings.");
    }
}

// Load Super Search Portals
async function loadPortals() {
    try {
        const res = await fetch('/api/portal-links?max_price=550');
        const data = await res.json();
        const portals = data.portals || [];

        const majorContainer = document.getElementById('portal-major-cards');
        const agencyContainer = document.getElementById('portal-agency-cards');
        const privateContainer = document.getElementById('portal-private-cards');

        if (majorContainer) majorContainer.innerHTML = '';
        if (agencyContainer) agencyContainer.innerHTML = '';
        if (privateContainer) privateContainer.innerHTML = '';

        portals.forEach(p => {
            const card = `
                <a href="${p.url}" target="_blank" class="property-card-touch bg-white p-3.5 sm:p-4 rounded-xl border border-slate-200 shadow-sm hover:shadow-md hover:border-blue-400 transition flex flex-col justify-between group">
                    <div>
                        <div class="flex items-center justify-between mb-1.5">
                            <span class="font-bold text-xs sm:text-sm text-slate-900 group-hover:text-blue-600 transition">${escapeHtml(p.name)}</span>
                            <i data-lucide="external-link" class="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition"></i>
                        </div>
                        <p class="text-[11px] sm:text-xs text-slate-500 leading-relaxed">${escapeHtml(p.tagline)}</p>
                    </div>
                    <div class="mt-2.5 pt-2 border-t border-slate-100 flex items-center text-[10px] sm:text-[11px] font-semibold text-blue-600">
                        <span>Search 2541 &lt;=$550</span>
                        <i data-lucide="arrow-right" class="w-3 h-3 ml-1"></i>
                    </div>
                </a>
            `;

            if (p.category === 'Major Portals' && majorContainer) majorContainer.innerHTML += card;
            else if (p.category === 'Local Agencies' && agencyContainer) agencyContainer.innerHTML += card;
            else if (privateContainer) privateContainer.innerHTML += card;
        });

        initIcons();
    } catch (e) {
        console.error("Error loading portals:", e);
    }
}

// Calculator & Bond
function initCalculator() {
    const input = document.getElementById('calc-rent-input');
    if (!input) return;

    const update = () => {
        const rent = parseFloat(input.value) || 0;
        const bond = rent * 4;
        const advance = rent * 2;
        const upfront = bond + advance;
        const monthly = (rent * 52) / 12;
        const annual = rent * 52;
        const grossWeekly = (rent / 0.3);
        const grossAnnual = grossWeekly * 52;

        document.getElementById('calc-bond').textContent = `$${bond.toLocaleString()}`;
        document.getElementById('calc-advance').textContent = `$${advance.toLocaleString()}`;
        document.getElementById('calc-upfront').textContent = `$${upfront.toLocaleString()}`;
        document.getElementById('calc-monthly').textContent = `$${Math.round(monthly).toLocaleString()} / mo`;
        document.getElementById('calc-annual').textContent = `$${Math.round(annual).toLocaleString()} / yr`;
        document.getElementById('calc-income-weekly').textContent = `$${Math.round(grossWeekly).toLocaleString()}/wk`;
        document.getElementById('calc-income-annual').textContent = `$${Math.round(grossAnnual).toLocaleString()}/yr`;
    };

    input.addEventListener('input', update);
    update();
}

// Renter Bio Generator
function initBioGenerator() {
    const nameInput = document.getElementById('gen-name');
    const jobInput = document.getElementById('gen-job');
    const houseInput = document.getElementById('gen-household');
    const petsInput = document.getElementById('gen-pets');
    const output = document.getElementById('gen-output');
    const copyBtn = document.getElementById('btn-copy-bio');

    if (!nameInput || !output) return;

    const generate = () => {
        const text = `Dear Property Manager,\n\nI am writing to express my strong interest in leasing a rental property in the Nowra / Bomaderry (2541) area. My name is ${nameInput.value}, working as a ${jobInput.value} with secure and reliable income.\n\nHousehold Profile:\n- Occupants: ${houseInput.value}\n- Pets: ${petsInput.value}\n- Rental Track Record: Spotless rental payment ledger, non-smokers, exceptionally respectful of property upkeep.\n\nMy 100 points of ID, 3 recent payslips, bank statements, and rental references are attached and verified on 2Apply/Ignite. I am ready to pay the 4-week bond and 2 weeks advance rent immediately upon approval.\n\nThank you for your time and consideration,\n${nameInput.value}`;
        output.value = text;
    };

    [nameInput, jobInput, houseInput, petsInput].forEach(inp => inp.addEventListener('input', generate));
    generate();

    copyBtn?.addEventListener('click', () => {
        navigator.clipboard.writeText(output.value);
        showToast("Cover letter copied to clipboard!");
    });
}

// Print Run Sheet
function printRunSheet() {
    const list = document.getElementById('print-inspections-list');
    document.getElementById('print-date').textContent = new Date().toLocaleDateString('en-AU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    const withInspections = allListings.filter(l => l.inspection_date);
    if (withInspections.length === 0) {
        list.innerHTML = `<p class="text-gray-500">No scheduled open home inspections found right now. Check individual listings on the portals.</p>`;
    } else {
        list.innerHTML = withInspections.map(item => `
            <div class="card-print p-3 border border-gray-300 rounded mb-2">
                <div class="flex justify-between font-bold text-sm">
                    <span>${formatInspection(item.inspection_date)}</span>
                    <span>$${item.price}/wk</span>
                </div>
                <div class="text-sm font-semibold">${escapeHtml(item.street)}, ${escapeHtml(item.suburb)} NSW 2541</div>
                <div class="text-xs text-gray-600">${item.beds || 1} Bed, ${item.baths || 1} Bath, ${item.cars || 0} Car (${escapeHtml(item.prop_type || 'House')})</div>
                ${item.notes ? `<div class="text-xs italic text-gray-700 mt-1">Notes: ${escapeHtml(item.notes)}</div>` : ''}
            </div>
        `).join('');
    }

    window.print();
}

// Fetch Stats from API
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const s = await res.json();
        const statCount = document.getElementById('stat-count');
        if (statCount) statCount.textContent = s.total_under_550;

        const statAvg = document.getElementById('stat-avg');
        if (statAvg) statAvg.textContent = `$${Math.round(s.avg_price)}`;

        const statMin = document.getElementById('stat-min');
        if (statMin) statMin.textContent = `$${s.min_price}`;

        const statInsp = document.getElementById('stat-inspections');
        if (statInsp) statInsp.textContent = s.inspections_count;

        const statPets = document.getElementById('stat-pets');
        if (statPets) statPets.textContent = s.pets_count ?? '--';

        const statSaved = document.getElementById('stat-saved');
        if (statSaved) statSaved.textContent = s.favorites_count;

        // Suburb counts in pills
        s.suburbs.forEach(sub => {
            const el = document.getElementById(`sub-${sub.suburb.toLowerCase().replace(/\s+/g, '-')}-count`);
            if (el) el.textContent = sub.count;
        });
        const allEl = document.getElementById('sub-all-count');
        if (allEl) allEl.textContent = s.total_under_550;
    } catch (e) {
        console.error("Error fetching stats:", e);
    }
}

// Helpers
function resetFilters() {
    filters.max_price = 550;
    filters.suburb = 'all';
    filters.min_beds = 0;
    filters.prop_type = 'all';
    filters.query = '';
    filters.sort_by = 'price_asc';
    filters.only_pets = false;
    filters.only_inspections = false;
    filters.only_favorites = false;

    syncFilterControls();

    const mobSearch = document.getElementById('filter-query-mobile');
    if (mobSearch) mobSearch.value = '';
    const deskSearch = document.getElementById('filter-query');
    if (deskSearch) deskSearch.value = '';
    syncMobileSearchClearBtn();

    document.querySelectorAll('.suburb-btn').forEach(b => {
        b.classList.remove('bg-blue-600', 'text-white', 'shadow-sm');
        b.classList.add('bg-slate-100', 'text-slate-700');
    });
    const allBtn = document.querySelector('.suburb-btn[data-suburb="all"]');
    if (allBtn) {
        allBtn.classList.remove('bg-slate-100', 'text-slate-700');
        allBtn.classList.add('bg-blue-600', 'text-white', 'shadow-sm');
    }

    updateActiveFilterBadge();
    fetchListings();
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

function showModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
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

function playChime() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
        osc.frequency.setValueAtTime(880, ctx.currentTime + 0.15); // A5
        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
        osc.start();
        osc.stop(ctx.currentTime + 0.5);
    } catch (e) {}
}

function requestBrowserNotification() {
    if (!("Notification" in window)) {
        showToast("Desktop notifications not supported in this browser.");
        return;
    }
    Notification.requestPermission().then(permission => {
        if (permission === "granted") {
            showToast("Notifications enabled!");
            new Notification("2541 Rental Radar", { body: "You will be alerted when new rentals under $550 are found!" });
        } else {
            showToast("Notification permission denied.");
        }
    });
}

function sendDesktopNotification(title, body) {
    if ("Notification" in window && Notification.permission === "granted") {
        new Notification(title, { body: body, icon: "/favicon.ico" });
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// First-Time Tips & Walkthrough Tour with Mobile Touch Swipe
let currentTipStep = 1;
const totalTipSteps = 6;

function initTipsModal() {
    const btnTips = document.getElementById('btn-tips');
    const modalTips = document.getElementById('modal-tips');
    const closeBtn = document.getElementById('modal-tips-close');
    const prevBtn = document.getElementById('btn-tip-prev');
    const nextBtn = document.getElementById('btn-tip-next');
    const dontShowCheck = document.getElementById('tips-dont-show');
    const tipsContainer = document.getElementById('tips-container');

    if (!modalTips) return;

    btnTips?.addEventListener('click', () => {
        currentTipStep = 1;
        updateTipStep();
        showModal('modal-tips');
    });

    closeBtn?.addEventListener('click', () => {
        hideModal('modal-tips');
    });

    prevBtn?.addEventListener('click', () => {
        if (currentTipStep > 1) {
            currentTipStep--;
            updateTipStep();
        }
    });

    nextBtn?.addEventListener('click', () => {
        if (currentTipStep < totalTipSteps) {
            currentTipStep++;
            updateTipStep();
        } else {
            hideModal('modal-tips');
            showToast("You're all set! Start exploring 2541 rentals.");
        }
    });

    dontShowCheck?.addEventListener('change', (e) => {
        localStorage.setItem('2541_tips_dont_show', e.target.checked ? 'true' : 'false');
    });

    // Touch Swipe Detection for Mobile Phones
    let touchStartX = 0;
    tipsContainer?.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    tipsContainer?.addEventListener('touchend', (e) => {
        const touchEndX = e.changedTouches[0].screenX;
        const diffX = touchStartX - touchEndX;

        if (diffX > 45 && currentTipStep < totalTipSteps) {
            // Swiped left -> Next
            currentTipStep++;
            updateTipStep();
        } else if (diffX < -45 && currentTipStep > 1) {
            // Swiped right -> Prev
            currentTipStep--;
            updateTipStep();
        }
    }, { passive: true });

    // Auto-open on first visit if not disabled
    const dontShow = localStorage.getItem('2541_tips_dont_show');
    if (dontShow !== 'true') {
        setTimeout(() => {
            currentTipStep = 1;
            updateTipStep();
            showModal('modal-tips');
        }, 600);
    }
}

function updateTipStep() {
    const slides = document.querySelectorAll('.tip-slide');
    const dotsContainer = document.getElementById('tips-dots');
    const prevBtn = document.getElementById('btn-tip-prev');
    const nextBtn = document.getElementById('btn-tip-next');

    slides.forEach(s => {
        const step = parseInt(s.getAttribute('data-step'));
        if (step === currentTipStep) {
            s.classList.remove('hidden');
        } else {
            s.classList.add('hidden');
        }
    });

    // Update Dots
    if (dotsContainer) {
        dotsContainer.innerHTML = Array.from({ length: totalTipSteps }).map((_, i) => {
            const active = (i + 1) === currentTipStep;
            return `<span class="w-2 h-2 rounded-full ${active ? 'bg-blue-600' : 'bg-slate-300'} transition-colors"></span>`;
        }).join('');
    }

    if (prevBtn) prevBtn.disabled = (currentTipStep === 1);
    if (nextBtn) {
        nextBtn.textContent = (currentTipStep === totalTipSteps) ? 'Done' : 'Next';
    }
    initIcons();
}
