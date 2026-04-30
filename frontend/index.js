document.addEventListener('DOMContentLoaded', () => {
    // URL to the raw JSON file
    const DATA_URL = 'https://raw.githubusercontent.com/smhasnanmonir/tok-automation/refs/heads/main/results/comparison_result.json';

    fetchData();

    async function fetchData() {
        try {
            const response = await fetch(DATA_URL);
            if (!response.ok) throw new Error('Failed to load data');
            const data = await response.json();
            renderDashboard(data);
        } catch (error) {
            console.error('Error:', error);
            document.getElementById('loading').innerHTML = `
                <p style="color: var(--danger)">Failed to load data. Please try again later.</p>
                <p class="text-sm text-muted">${error.message}</p>
            `;
        }
    }

    function renderDashboard(data) {
        // Hide loading, show dashboard
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard').style.display = 'block';

        // Setup Download Button
        const downloadBtn = document.getElementById('downloadBtn');
        downloadBtn.style.display = 'inline-flex';
        downloadBtn.onclick = () => {
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
            const downloadAnchorNode = document.createElement('a');
            downloadAnchorNode.setAttribute("href", dataStr);
            downloadAnchorNode.setAttribute("download", "comparison_result.json");
            document.body.appendChild(downloadAnchorNode); // required for firefox
            downloadAnchorNode.click();
            downloadAnchorNode.remove();
        };

        // 1. Render Metadata
        const date = new Date(data.metadata.comparison_date).toLocaleString();
        document.getElementById('lastUpdated').textContent = `Last Checked: ${date}`;

        // Clean up PDF names (remove path)
        const oldName = data.metadata.old_pdf.split('/').pop().replace('.pdf', '');
        const newName = data.metadata.new_pdf.split('/').pop().replace('.pdf', '');

        document.getElementById('oldPdfName').textContent = oldName;
        document.getElementById('newPdfName').textContent = newName;

        // 2. Render Counts
        document.getElementById('countNew').textContent = data.metadata.summary.newly_added_count;
        document.getElementById('countIncrease').textContent = data.metadata.summary.price_increased_count;
        document.getElementById('countDecrease').textContent = data.metadata.summary.price_decreased_count;
        document.getElementById('countStockout').textContent = data.metadata.summary.stock_out_count;

        // Update Bubbles
        document.getElementById('bubbleNew').textContent = data.metadata.summary.newly_added_count;
        document.getElementById('bubbleStockout').textContent = data.metadata.summary.stock_out_count;

        // 3. Render Grids
        renderGrid('gridNew', data.newly_added_products, 'new');
        renderGrid('gridIncrease', data.price_increased_products, 'increase');
        renderGrid('gridDecrease', data.price_decreased_products, 'decrease');
        renderGrid('gridStockout', data.stock_out_products, 'stockout');

        // 4. Setup Search
        setupSearch();
    }

    function renderGrid(elementId, products, type) {
        const container = document.getElementById(elementId);
        container.innerHTML = '';

        if (!products || products.length === 0) {
            container.innerHTML = '<p class="text-muted">No products found for this category.</p>';
            return;
        }

        products.forEach(product => {
            const card = document.createElement('div');
            card.className = `product-card card-${type}`;
            card.dataset.brand = (product.brand || '').toLowerCase();
            card.dataset.productName = (product.product_name || '').toLowerCase();

            // Determine price display based on type
            let priceHtml = '';

            if (type === 'new') {
                priceHtml = `
                    <div class="price-row">
                        <span class="price-label">Wholesale Price</span>
                        <span class="price-value">${formatPrice(product.wholesale_price_for_you)}</span>
                    </div>
                `;
            } else if (type === 'stockout') {
                priceHtml = `
                    <div class="price-row">
                        <span class="price-label">Last Price</span>
                        <span class="price-value">${formatPrice(product.wholesale_price_for_you)}</span>
                    </div>
                `;
            } else if (type === 'increase' || type === 'decrease') {
                const isIncrease = type === 'increase';
                const badgeClass = isIncrease ? 'increase' : 'decrease';
                const icon = isIncrease ? '↑' : '↓';

                priceHtml = `
                    <div class="price-row" style="flex-direction: column; align-items: flex-start; gap: 0.5rem;">
                        <div class="price-change-container">
                            <span class="old-price">${formatPrice(product.old_wholesale_price_for_you)}</span>
                            <span>➜</span>
                            <span class="new-price">${formatPrice(product.new_wholesale_price_for_you)}</span>
                        </div>
                        <div class="change-badge ${badgeClass}">
                            ${icon} ${product.price_difference} (${product.percentage_change}%)
                        </div>
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="card-header">
                    <span class="brand-tag">${product.brand}</span>
                    <span class="page-info">Page ${product.page || '?'}</span>
                </div>
                <div class="card-body">
                    <h3 class="product-name">${product.product_name}</h3>
                    ${priceHtml}
                </div>
            `;
            container.appendChild(card);
        });
    }

    function setupSearch() {
        const searchInput = document.getElementById('searchInput');
        const clearBtn = document.getElementById('clearSearch');
        const searchInfo = document.getElementById('searchInfo');
        let debounceTimer;

        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => filterProducts(searchInput.value), 150);
            clearBtn.style.display = searchInput.value ? 'block' : 'none';
        });

        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            clearBtn.style.display = 'none';
            filterProducts('');
            searchInput.focus();
        });

        function filterProducts(query) {
            const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
            const allCards = document.querySelectorAll('.product-card');
            let totalVisible = 0;

            allCards.forEach(card => {
                if (terms.length === 0) {
                    card.classList.remove('search-hidden');
                    totalVisible++;
                    return;
                }

                const brand = card.dataset.brand;
                const name = card.dataset.productName;
                const combined = brand + ' ' + name;

                // Every search term must appear in brand, product name, or their combination
                const matches = terms.every(term =>
                    combined.includes(term)
                );

                if (matches) {
                    card.classList.remove('search-hidden');
                    totalVisible++;
                } else {
                    card.classList.add('search-hidden');
                }
            });

            // Update section empty states
            document.querySelectorAll('.section').forEach(section => {
                const grid = section.querySelector('.product-grid');
                if (!grid) return;
                const visibleCards = grid.querySelectorAll('.product-card:not(.search-hidden)');
                section.classList.toggle('search-empty', visibleCards.length === 0 && terms.length > 0);
            });

            // Update search info
            if (terms.length > 0) {
                searchInfo.style.display = 'flex';
                searchInfo.innerHTML = `Showing <span class="match-count">${totalVisible}</span> matching product${totalVisible !== 1 ? 's' : ''} for "<strong>${escapeHtml(query.trim())}</strong>"`;
            } else {
                searchInfo.style.display = 'none';
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    function formatPrice(price) {
        if (!price) return 'N/A';
        // If it's already a number, format it
        // If it's a string, try to parse it, else return as is
        const num = parseFloat(price);
        if (isNaN(num)) return price;
        return num.toLocaleString();
    }
});