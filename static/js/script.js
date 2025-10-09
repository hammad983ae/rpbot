// Property Data Scraper Frontend JavaScript

class PropertyScraper {
    constructor() {
        this.currentData = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupTabs();
    }

    bindEvents() {
        const searchForm = document.getElementById('searchForm');
        const searchBtn = document.getElementById('searchBtn');
        const addressInput = document.getElementById('addressInput');

        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSearch();
        });

        // Add enter key support
        addressInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.handleSearch();
            }
        });

        // Add input validation
        addressInput.addEventListener('input', () => {
            this.validateInput();
        });
    }

    setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabPanels = document.querySelectorAll('.tab-panel');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.getAttribute('data-tab');
                
                // Remove active class from all tabs and panels
                tabBtns.forEach(b => b.classList.remove('active'));
                tabPanels.forEach(p => p.classList.remove('active'));
                
                // Add active class to clicked tab and corresponding panel
                btn.classList.add('active');
                document.getElementById(targetTab).classList.add('active');
            });
        });
    }

    validateInput() {
        const addressInput = document.getElementById('addressInput');
        const searchBtn = document.getElementById('searchBtn');
        const value = addressInput.value.trim();
        
        searchBtn.disabled = value.length < 5;
    }

    async handleSearch() {
        const addressInput = document.getElementById('addressInput');
        const address = addressInput.value.trim();

        if (!address) {
            this.showError('Please enter a property address');
            return;
        }

        this.showLoading();
        this.hideError();
        this.hideResults();

        try {
            const response = await fetch('/scrape-property', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ address: address })
            });

            const data = await response.json();

            if (data.success) {
                this.currentData = data.data;
                this.displayResults(data.data);
            } else {
                this.showError(data.message || 'Failed to retrieve property data');
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Network error. Please check your connection and try again.');
        } finally {
            this.hideLoading();
        }
    }

    showLoading() {
        const loadingSection = document.getElementById('loadingSection');
        const searchBtn = document.getElementById('searchBtn');
        
        loadingSection.style.display = 'block';
        searchBtn.disabled = true;
        searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Searching...</span>';

        // Animate loading steps
        this.animateLoadingSteps();
    }

    hideLoading() {
        const loadingSection = document.getElementById('loadingSection');
        const searchBtn = document.getElementById('searchBtn');
        
        loadingSection.style.display = 'none';
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="fas fa-search"></i><span>Search Property</span>';
    }

    animateLoadingSteps() {
        const steps = ['step1', 'step2', 'step3'];
        let currentStep = 0;

        const interval = setInterval(() => {
            if (currentStep < steps.length) {
                document.getElementById(steps[currentStep]).classList.add('active');
                currentStep++;
            } else {
                clearInterval(interval);
            }
        }, 1000);
    }

    showError(message) {
        const errorSection = document.getElementById('errorSection');
        const errorMessage = document.getElementById('errorMessage');
        
        errorMessage.textContent = message;
        errorSection.style.display = 'block';
    }

    hideError() {
        const errorSection = document.getElementById('errorSection');
        errorSection.style.display = 'none';
    }

    hideResults() {
        const resultsSection = document.getElementById('resultsSection');
        resultsSection.style.display = 'none';
    }

    displayResults(data) {
        this.populatePropertyOverview(data);
        this.populateBasicInfo(data);
        this.populateValuationInfo(data);
        this.populateHistoryInfo(data);
        this.populateSchoolsInfo(data);
        this.populateAdditionalInfo(data);

        const resultsSection = document.getElementById('resultsSection');
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    populatePropertyOverview(data) {
        const overview = document.getElementById('propertyOverview');
        
        const badges = [];
        if (data.type) badges.push(`<span class="badge">${data.type}</span>`);
        if (data.scrapedAt) badges.push(`<span class="badge success">Recently Updated</span>`);

        const stats = [];
        if (data.bedrooms && data.bedrooms !== '-') {
            stats.push(`
                <div class="stat-item">
                    <div class="stat-value">${data.bedrooms}</div>
                    <div class="stat-label">Bedrooms</div>
                </div>
            `);
        }
        if (data.bathrooms && data.bathrooms !== '-') {
            stats.push(`
                <div class="stat-item">
                    <div class="stat-value">${data.bathrooms}</div>
                    <div class="stat-label">Bathrooms</div>
                </div>
            `);
        }
        if (data.carSpaces && data.carSpaces !== '-') {
            stats.push(`
                <div class="stat-item">
                    <div class="stat-value">${data.carSpaces}</div>
                    <div class="stat-label">Car Spaces</div>
                </div>
            `);
        }
        if (data.landSize && data.landSize !== '-') {
            stats.push(`
                <div class="stat-item">
                    <div class="stat-value">${data.landSize}</div>
                    <div class="stat-label">Land Size</div>
                </div>
            `);
        }

        overview.innerHTML = `
            <div class="property-header">
                <div class="property-title">
                    <h2>${data.address || 'Property Information'}</h2>
                    <p>Comprehensive property data and analysis</p>
                </div>
                <div class="property-badges">
                    ${badges.join('')}
                </div>
            </div>
            <div class="property-stats">
                ${stats.join('')}
            </div>
        `;
    }

    populateBasicInfo(data) {
        const basicInfo = document.getElementById('basicInfo');
        
        const infoItems = [
            { label: 'Property Type', value: data.type || 'Not available' },
            { label: 'Bedrooms', value: data.bedrooms || 'Not available' },
            { label: 'Bathrooms', value: data.bathrooms || 'Not available' },
            { label: 'Car Spaces', value: data.carSpaces || 'Not available' },
            { label: 'Land Size', value: data.landSize || 'Not available' },
            { label: 'Floor Area', value: data.floorArea || 'Not available' },
            { label: 'Last Sold Price', value: data.lastSold?.price || 'Not available' },
            { label: 'Last Sold Date', value: data.lastSold?.date || 'Not available' },
            { label: 'Sold By', value: data.lastSold?.soldBy || 'Not available' },
            { label: 'Land Use', value: data.sale?.landUse || 'Not available' },
            { label: 'Issue Date', value: data.sale?.issueDate || 'Not available' },
            { label: 'Advertisement Date', value: data.sale?.advertisementDate || 'Not available' }
        ];

        // Create the regular grid items
        let gridContent = infoItems.map(item => `
            <div class="info-item">
                <div class="info-label">${item.label}</div>
                <div class="info-value">${item.value}</div>
            </div>
        `).join('');

        // Add the listing description as a full-width item below the grid
        const listingDescription = this.formatListingDescription(data.sale?.listingDescription);
        if (listingDescription && listingDescription !== 'Not available') {
            gridContent += `
                <div class="info-item info-item-full-width">
                    <div class="info-label">Listing Information</div>
                    <div class="info-value info-value-description">${listingDescription}</div>
                </div>
            `;
        }

        basicInfo.innerHTML = gridContent;
    }

    populateValuationInfo(data) {
        const valuationInfo = document.getElementById('valuationInfo');
        
        let valuationContent = '';

        // Property Valuation
        if (data.valuation?.estimate || data.valuation?.estimateJson) {
            const estimate = data.valuation.estimateJson || {};
            valuationContent += `
                <div class="valuation-card">
                    <div class="valuation-title">Property Valuation</div>
                    <div class="valuation-grid">
                        ${estimate.low_value ? `
                            <div class="valuation-item">
                                <div class="valuation-value">$${this.formatNumber(estimate.low_value)}</div>
                                <div class="valuation-label">Low Estimate</div>
                            </div>
                        ` : ''}
                        ${estimate.estimate_value ? `
                            <div class="valuation-item">
                                <div class="valuation-value">$${this.formatNumber(estimate.estimate_value)}</div>
                                <div class="valuation-label">Estimated Value</div>
                            </div>
                        ` : ''}
                        ${estimate.high_value ? `
                            <div class="valuation-item">
                                <div class="valuation-value">$${this.formatNumber(estimate.high_value)}</div>
                                <div class="valuation-label">High Estimate</div>
                            </div>
                        ` : ''}
                        ${estimate.confidence ? `
                            <div class="valuation-item">
                                <div class="valuation-value">${estimate.confidence}</div>
                                <div class="valuation-label">Confidence Level</div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }

        // Rental Estimate
        if (data.valuation?.rental || data.valuation?.rentalJson) {
            const rental = data.valuation.rentalJson || {};
            valuationContent += `
                <div class="valuation-card">
                    <div class="valuation-title">Rental Estimate</div>
                    <div class="valuation-grid">
                        ${rental.low_value ? `
                            <div class="valuation-item">
                                <div class="valuation-value">$${this.formatNumber(rental.low_value)}</div>
                                <div class="valuation-label">Low Estimate</div>
                            </div>
                        ` : ''}
                        ${rental.estimate_value ? `
                            <div class="valuation-item">
                                <div class="valuation-value">$${this.formatNumber(rental.estimate_value)}</div>
                                <div class="valuation-label">Estimated Rent</div>
                            </div>
                        ` : ''}
                        ${rental.high_value ? `
                            <div class="valuation-item">
                                <div class="valuation-value">$${this.formatNumber(rental.high_value)}</div>
                                <div class="valuation-label">High Estimate</div>
                            </div>
                        ` : ''}
                        ${rental.rental_yield ? `
                            <div class="valuation-item">
                                <div class="valuation-value">${rental.rental_yield}</div>
                                <div class="valuation-label">Rental Yield</div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }

        if (!valuationContent) {
            valuationContent = '<p class="text-center">No valuation data available</p>';
        }

        valuationInfo.innerHTML = valuationContent;
    }

    populateHistoryInfo(data) {
        const historyInfo = document.getElementById('historyInfo');
        
        
        // Debug logging
        console.log('🔍 Full API response data:', data);
        console.log('🔍 History data received:', data.history);
        console.log('🔍 History events_by_type:', data.history?.events_by_type);
        console.log('🔍 History total_events:', data.history?.total_events);
        
        // Debug each type array
        if (data.history?.events_by_type) {
            Object.entries(data.history.events_by_type).forEach(([type, events]) => {
                console.log(`🔍 ${type} events (${events.length}):`, events);
            });
        }
        
        if (!data.history || !data.history.events_by_type || data.history.total_events === 0) {
            console.log('❌ No history data found, showing placeholder');
            historyInfo.innerHTML = `
                <div class="history-content">
                    <div class="history-item">
                        <div class="history-date">No History Available</div>
                        <div class="history-description">No property history data found</div>
                        <div class="history-details">Property history information is not available for this property.</div>
                    </div>
                </div>
            `;
            return;
        }
        
        console.log('✅ History data found, proceeding with display');

        const history = data.history;
        let historyContent = '';

        // Create history type tabs (removed 'All' tab)
        const historyTypes = [
            { key: 'sale', label: 'Sale', icon: 'fas fa-dollar-sign', color: '#10b981' },
            { key: 'listing', label: 'Listing', icon: 'fas fa-list-alt', color: '#f59e0b' },
            { key: 'rental', label: 'Rental', icon: 'fas fa-key', color: '#3b82f6' },
            { key: 'da', label: 'DA', icon: 'fas fa-file-alt', color: '#8b5cf6' }
        ];

        // Create tabs
        historyContent += `
            <div class="history-tabs">
                ${historyTypes.map(type => `
                    <button class="history-tab-btn" data-history-type="${type.key}">
                        <i class="${type.icon}"></i>
                        <span>${type.label}</span>
                        <span class="event-count">${this.getEventCount(history, type.key)}</span>
                    </button>
                `).join('')}
            </div>
        `;

        // Create content for each tab
        historyTypes.forEach((type, index) => {
            const events = this.getEventsByType(history, type.key);
            historyContent += `
                <div class="history-tab-content" id="history-${type.key}" style="display: ${index === 0 ? 'block' : 'none'};">
                    ${this.renderHistoryEvents(events, type)}
                </div>
            `;
        });

        historyInfo.innerHTML = `<div class="history-content">${historyContent}</div>`;

        // Add event listeners for history tabs
        this.setupHistoryTabs();
    }

    getEventCount(history, type) {
        return history.events_by_type[type]?.length || 0;
    }

    getEventsByType(history, type) {
        console.log(`🔍 getEventsByType called for type: ${type}`);
        console.log(`🔍 History object:`, history);
        console.log(`🔍 Available events_by_type keys:`, Object.keys(history.events_by_type || {}));
        console.log(`🔍 Events for ${type}:`, history.events_by_type?.[type]);
        
        const events = history.events_by_type[type] || [];
        console.log(`🔍 Final events for ${type}:`, events);
        console.log(`🔍 Events length for ${type}:`, events.length);
        
        // Sort events by date in descending order (newest first)
        return events.sort((a, b) => {
            const dateA = new Date(a.date);
            const dateB = new Date(b.date);
            return dateB - dateA; // Descending order
        });
    }

    renderHistoryEvents(events, type) {
        if (!events || events.length === 0) {
            return `
                <div class="history-item">
                    <div class="history-date">No ${type.label} Events</div>
                    <div class="history-description">No ${type.label.toLowerCase()} history found for this property</div>
                </div>
            `;
        }

        return events.map(event => {
            // Format the details properly
            let formattedDetails = '';
            if (event.details) {
                formattedDetails = this.formatHistoryDetails(event.details);
            }

            return `
                <div class="history-item" style="border-left-color: ${type.color};">
                    <div class="history-date">
                        <i class="${type.icon}"></i>
                        ${event.date || 'Date not available'}
                    </div>
                    <div class="history-description">${event.description || 'No description'}</div>
                    ${formattedDetails ? `<div class="history-details">${formattedDetails}</div>` : ''}
                    <div class="history-type" style="color: ${type.color}; font-size: 0.875rem; font-weight: 500; margin-top: 0.5rem;">
                        ${type.label.toUpperCase()}
                    </div>
                </div>
            `;
        }).join('');
    }

    formatHistoryDetails(details) {
        if (!details) return '';
        
        try {
            // If details is a string that looks like JSON, try to parse it
            if (typeof details === 'string' && details.includes('{') && details.includes('}')) {
                // Try to parse as JSON array or object
                const cleaned = details.replace(/[{}]/g, '').replace(/"/g, '');
                const parts = cleaned.split(',').map(part => part.trim()).filter(part => part);
                return parts.join(' • ');
            }
            
            // If details is an array, join with bullets
            if (Array.isArray(details)) {
                return details.join(' • ');
            }
            
            // If details is an object, format key-value pairs
            if (typeof details === 'object') {
                return Object.entries(details).map(([key, value]) => `${key}: ${value}`).join(' • ');
            }
            
            // Otherwise, return as string
            return String(details);
        } catch (error) {
            // If parsing fails, return cleaned version
            return String(details).replace(/[{}]/g, '').replace(/,/g, ' • ').trim();
        }
    }

    setupHistoryTabs() {
        const tabBtns = document.querySelectorAll('.history-tab-btn');
        const tabContents = document.querySelectorAll('.history-tab-content');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetType = btn.getAttribute('data-history-type');
                
                // Remove active class from all tabs
                tabBtns.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.style.display = 'none');
                
                // Add active class to clicked tab and show corresponding content
                btn.classList.add('active');
                document.getElementById(`history-${targetType}`).style.display = 'block';
            });
        });

        // Set first tab as active
        if (tabBtns.length > 0) {
            tabBtns[0].classList.add('active');
        }
    }

    getHistoryTypeIcon(type) {
        const icons = {
            'sale': 'fas fa-dollar-sign',
            'rental': 'fas fa-key',
            'listing': 'fas fa-list',
            'other': 'fas fa-info-circle'
        };
        return icons[type] || icons['other'];
    }

    getHistoryTypeColor(type) {
        const colors = {
            'sale': '#10b981',
            'rental': '#3b82f6',
            'listing': '#f59e0b',
            'other': '#6b7280'
        };
        return colors[type] || colors['other'];
    }

    formatListingDescription(listingData) {
        if (!listingData) return null;
        
        try {
            // Try to parse as JSON first
            if (typeof listingData === 'string' && listingData.includes('{')) {
                const parsed = JSON.parse(listingData);
                if (Array.isArray(parsed)) {
                    return parsed.join(' • ');
                } else if (typeof parsed === 'object') {
                    return Object.values(parsed).join(' • ');
                }
            }
            
            // Handle different formats
            let formatted = listingData;
            
            // Clean up common formatting issues
            formatted = formatted.replace(/^"|"$/g, ''); // Remove surrounding quotes
            formatted = formatted.replace(/\{|\}/g, ''); // Remove curly braces
            formatted = formatted.replace(/,/g, ' • '); // Replace commas with bullets
            
            // Handle specific patterns
            if (formatted.includes('Not Disclosed')) {
                formatted = formatted.replace(/Listing Price is Not Disclosed[^•]*/, 'Price: Not Disclosed');
            }
            
            // Clean up extra spaces and bullets
            formatted = formatted.replace(/\s*•\s*/g, ' • ').trim();
            formatted = formatted.replace(/^•\s*|•\s*$/g, '');
            
            return formatted || null;
        } catch (error) {
            // If parsing fails, return cleaned version
            return listingData.replace(/\{|\}|"/g, '').replace(/,/g, ' • ').trim();
        }
    }

    populateSchoolsInfo(data) {
        const schoolsInfo = document.getElementById('schoolsInfo');
        
        let schoolsContent = '';

        // In Catchment Schools
        if (data.schools?.inCatchment && Array.isArray(data.schools.inCatchment)) {
            schoolsContent += `
                <div class="schools-section">
                    <div class="schools-title">Schools in Catchment</div>
                    ${data.schools.inCatchment.map(school => `
                        <div class="school-item">
                            <div class="school-name">${school.name || 'Unknown School'}</div>
                            <div class="school-address">${school.address || 'Address not available'}</div>
                            <div class="school-distance">${school.distance || 'Distance not available'}</div>
                            ${school.attributes ? `
                                <div class="school-attributes">
                                    ${school.attributes.type ? `<span class="school-attribute">${school.attributes.type}</span>` : ''}
                                    ${school.attributes.sector ? `<span class="school-attribute">${school.attributes.sector}</span>` : ''}
                                    ${school.attributes.gender ? `<span class="school-attribute">${school.attributes.gender}</span>` : ''}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // All Nearby Schools
        if (data.schools?.allNearby && Array.isArray(data.schools.allNearby)) {
            schoolsContent += `
                <div class="schools-section">
                    <div class="schools-title">All Nearby Schools</div>
                    ${data.schools.allNearby.map(school => `
                        <div class="school-item">
                            <div class="school-name">${school.name || 'Unknown School'}</div>
                            <div class="school-address">${school.address || 'Address not available'}</div>
                            <div class="school-distance">${school.distance || 'Distance not available'}</div>
                            ${school.attributes ? `
                                <div class="school-attributes">
                                    ${school.attributes.type ? `<span class="school-attribute">${school.attributes.type}</span>` : ''}
                                    ${school.attributes.sector ? `<span class="school-attribute">${school.attributes.sector}</span>` : ''}
                                    ${school.attributes.gender ? `<span class="school-attribute">${school.attributes.gender}</span>` : ''}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        }

        if (!schoolsContent) {
            schoolsContent = '<p class="text-center">No school information available</p>';
        }

        schoolsInfo.innerHTML = schoolsContent;
    }

    populateAdditionalInfo(data) {
        const additionalInfo = document.getElementById('additionalInfo');
        
        let additionalContent = '';

        // Agent Information
        if (data.agent) {
            additionalContent += `
                <div class="additional-section">
                    <div class="additional-title">Agent Information</div>
                    <div class="additional-grid">
                        ${data.agent.agency ? `
                            <div class="additional-item">
                                <div class="additional-label">Agency</div>
                                <div class="additional-value">${data.agent.agency}</div>
                            </div>
                        ` : ''}
                        ${data.agent.name ? `
                            <div class="additional-item">
                                <div class="additional-label">Agent Name</div>
                                <div class="additional-value">${data.agent.name}</div>
                            </div>
                        ` : ''}
                        ${data.agent.phone ? `
                            <div class="additional-item">
                                <div class="additional-label">Phone</div>
                                <div class="additional-value">${data.agent.phone}</div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }

        // Household Information
        if (data.household) {
            const hasHouseholdData = data.household.ownerType || data.household.currentTenure;
            
            if (hasHouseholdData) {
                additionalContent += `
                    <div class="additional-section">
                        <div class="additional-title">Household Information</div>
                        <div class="additional-grid">
                            ${data.household.ownerType ? `
                                <div class="additional-item">
                                    <div class="additional-label">Owner Type</div>
                                    <div class="additional-value">${data.household.ownerType}</div>
                                </div>
                            ` : ''}
                            ${data.household.currentTenure ? `
                                <div class="additional-item">
                                    <div class="additional-label">Current Tenure</div>
                                    <div class="additional-value">${data.household.currentTenure}</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            } else {
                additionalContent += `
                    <div class="additional-section">
                        <div class="additional-title">Household Information</div>
                        <div class="additional-grid">
                            <div class="additional-item">
                                <div class="additional-label">Status</div>
                                <div class="additional-value">No household information available</div>
                            </div>
                        </div>
                    </div>
                `;
            }
        } else {
            additionalContent += `
                <div class="additional-section">
                    <div class="additional-title">Household Information</div>
                    <div class="additional-grid">
                        <div class="additional-item">
                            <div class="additional-label">Status</div>
                            <div class="additional-value">Household data not found</div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Additional Information
        if (data.additional) {
            if (data.additional.legalDescription && typeof data.additional.legalDescription === 'object') {
                additionalContent += `
                    <div class="additional-section">
                        <div class="additional-title">Legal Description</div>
                        <div class="additional-grid">
                            ${Object.entries(data.additional.legalDescription).map(([key, value]) => `
                                <div class="additional-item">
                                    <div class="additional-label">${key}</div>
                                    <div class="additional-value">${value}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            if (data.additional.features && typeof data.additional.features === 'object') {
                additionalContent += `
                    <div class="additional-section">
                        <div class="additional-title">Property Features</div>
                        <div class="additional-grid">
                            ${Object.entries(data.additional.features).map(([key, value]) => `
                                <div class="additional-item">
                                    <div class="additional-label">${key}</div>
                                    <div class="additional-value">${value}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            if (data.additional.landValues && typeof data.additional.landValues === 'object') {
                additionalContent += `
                    <div class="additional-section">
                        <div class="additional-title">Land Values</div>
                        <div class="additional-grid">
                            ${Object.entries(data.additional.landValues).map(([key, value]) => `
                                <div class="additional-item">
                                    <div class="additional-label">${key}</div>
                                    <div class="additional-value">${value}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
        }

        if (!additionalContent) {
            additionalContent = '<p class="text-center">No additional information available</p>';
        }

        additionalInfo.innerHTML = additionalContent;
    }

    formatNumber(value) {
        if (!value) return '0';
        const num = parseFloat(value.toString().replace(/[^0-9.-]/g, ''));
        if (isNaN(num)) return value;
        return num.toLocaleString();
    }
}

// Global functions for error handling
function hideError() {
    const errorSection = document.getElementById('errorSection');
    errorSection.style.display = 'none';
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PropertyScraper();
});

// Add some utility functions for better UX
document.addEventListener('DOMContentLoaded', () => {
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add loading state to form submission
    const form = document.getElementById('searchForm');
    if (form) {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Searching...</span>';
            }
        });
    }
});
