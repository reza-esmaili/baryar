document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // ۱. گرفتن المان‌های اصلی فرم
    // ==========================================
    const transportModeSelect = document.querySelector('select[name="transport_mode"]') || document.getElementById('id_transport_mode');
    const provinceSelect = document.querySelector('select[name="origin_province"]');
    const originCitySelect = document.querySelector('select[name="origin_city"]');
    const destCountrySelect = document.querySelector('select[name="destination_country"]');
    const destCitySelect = document.querySelector('select[name="destination_city"]');
    const destPortSelect = document.querySelector('select[name="destination_port"]');
    
    const cargoContainer = document.getElementById('cargo-types-container');
    const selectedDataElement = document.getElementById('selected_cargo_data');
    const tiersContainer = document.getElementById('tiers-container');

    // ==========================================
    // ۲. وابستگی استان مبدا -> شهر مبدا
    // ==========================================
    if (provinceSelect && originCitySelect) {
        provinceSelect.addEventListener('change', function() {
            const provinceId = this.value;
            originCitySelect.innerHTML = '<option value="">---------</option>';
            if (provinceId) {
                fetch(`/rates/ajax/load-cities/?province_id=${provinceId}`)
                    .then(response => response.json())
                    .then(data => {
                        data.forEach(city => {
                            originCitySelect.innerHTML += `<option value="${city.id}">${city.name}</option>`;
                        });
                    });
            }
        });
    }

    // ==========================================
    // ۳. وابستگی کشور مقصد -> شهر مقصد
    // ==========================================
    if (destCountrySelect && destCitySelect) {
        destCountrySelect.addEventListener('change', function() {
            const countryId = this.value;
            destCitySelect.innerHTML = '<option value="">---------</option>';
            if (destPortSelect) destPortSelect.innerHTML = '<option value="">---------</option>'; 
            if (countryId) {
                fetch(`/rates/ajax/load-destination-cities/?country_id=${countryId}`)
                    .then(response => response.json())
                    .then(data => {
                        data.forEach(city => {
                            destCitySelect.innerHTML += `<option value="${city.id}">${city.name}</option>`;
                        });
                    });
            }
        });
    }

    // ==========================================
    // ۴. وابستگی شهر مقصد + روش حمل -> پورت مقصد
    // ==========================================
    function loadPorts() {
        if (!destCitySelect || !destPortSelect || !transportModeSelect) return;
        const cityId = destCitySelect.value;
        const transportMode = transportModeSelect.value;
        destPortSelect.innerHTML = '<option value="">---------</option>';
        if (cityId && transportMode) {
            fetch(`/rates/ajax/load-ports/?city_id=${cityId}&transport_mode=${transportMode}`)
                .then(response => response.json())
                .then(data => {
                    data.forEach(port => {
                        destPortSelect.innerHTML += `<option value="${port.id}">${port.name}</option>`;
                    });
                });
        }
    }
    if (destCitySelect) destCitySelect.addEventListener('change', loadPorts);
    if (transportModeSelect) transportModeSelect.addEventListener('change', loadPorts);

    // ==========================================
    // ۵. لود داینامیک انواع کالا براساس روش حمل
    // ==========================================
    let selectedCargoTypes = [];
    if(selectedDataElement) {
        try {
            const parsedData = JSON.parse(selectedDataElement.textContent);
            selectedCargoTypes = parsedData.map(item => item.id || item);
        } catch(e) {
            console.error('Error parsing selected cargo data:', e);
        }
    }

    function loadCargoTypes(mode) {
        if (!cargoContainer) return;
        if (!mode) {
            cargoContainer.innerHTML = '<span class="text-muted small">ابتدا روش حمل را انتخاب کنید.</span>';
            return;
        }

        cargoContainer.innerHTML = '<span class="text-muted small">در حال بارگذاری...</span>';
        
        if (typeof loadCargoTypesUrl !== 'undefined') {
            fetch(`${loadCargoTypesUrl}?transport_mode=${mode}`)
                .then(response => response.json())
                .then(data => {
                    cargoContainer.innerHTML = '';
                    if (data.length === 0) {
                        cargoContainer.innerHTML = '<span class="text-muted small">کالایی برای این روش حمل یافت نشد.</span>';
                        return;
                    }
                    data.forEach(cargo => {
                        const isChecked = selectedCargoTypes.includes(cargo.id) ? 'checked' : '';
                        cargoContainer.innerHTML += `
                            <div class="form-check form-check-inline mt-1 mb-1 me-3">
                                <input class="form-check-input" type="checkbox" name="cargo_types" value="${cargo.id}" id="cargo_${cargo.id}" ${isChecked}>
                                <label class="form-check-label" for="cargo_${cargo.id}">${cargo.name}</label>
                            </div>
                        `;
                    });
                })
                .catch(error => {
                    console.error('Error loading cargo types:', error);
                    cargoContainer.innerHTML = '<span class="text-danger small">خطا در دریافت اطلاعات.</span>';
                });
        }
    }

    if (transportModeSelect && cargoContainer) {
        transportModeSelect.addEventListener('change', function() {
            loadCargoTypes(this.value);
        });
        if (transportModeSelect.value) {
            loadCargoTypes(transportModeSelect.value);
        }
    }

    // ==========================================
    // ۶. منطق نمایش/مخفی کردن فیلدهای وزن و کانتینر
    // ==========================================
    function toggleFieldDisplay(inputElement, show) {
        if (inputElement) {
            const wrapper = inputElement.closest('td') || inputElement.closest('.form-group') || inputElement.parentElement;
            if (wrapper) wrapper.style.display = show ? '' : 'none';
        }
    }

    function toggleTierFields() {
        if (!transportModeSelect) return;
        const mode = transportModeSelect.value;
        const rows = document.querySelectorAll('.tier-row');
        
        rows.forEach(row => {
            const weightFrom = row.querySelector('input[name$="-weight_from"]');
            const weightTo = row.querySelector('input[name$="-weight_to"]');
            const containerSize = row.querySelector('select[name$="-container_size"]');
            const containerType = row.querySelector('select[name$="-container_type"]');

            if (mode === 'sea_fcl') {
                toggleFieldDisplay(weightFrom, false);
                toggleFieldDisplay(weightTo, false);
                toggleFieldDisplay(containerSize, true);
                toggleFieldDisplay(containerType, true);
            } else {
                toggleFieldDisplay(weightFrom, true);
                toggleFieldDisplay(weightTo, true);
                toggleFieldDisplay(containerSize, false);
                toggleFieldDisplay(containerType, false);
            }
        });
    }

    if (transportModeSelect) {
        transportModeSelect.addEventListener('change', toggleTierFields);
        toggleTierFields(); 
    }

    // ==========================================
    // ۷. منطق دکمه‌های فرم‌ست (افزودن و حذف)
    // ==========================================
    const addButton = document.getElementById('add-tier-btn');
    const totalForms = document.querySelector('input[name$="-TOTAL_FORMS"]');

    if (addButton && tiersContainer && totalForms) {
        addButton.addEventListener('click', function(e) {
            e.preventDefault();
            const rows = tiersContainer.querySelectorAll('.tier-row');
            if (rows.length === 0) return;
            
            const formCount = parseInt(totalForms.value);
            const newRow = rows[0].cloneNode(true);
            
            newRow.innerHTML = newRow.innerHTML.replace(/-0-/g, `-${formCount}-`);
            newRow.innerHTML = newRow.innerHTML.replace(/_0_/g, `_${formCount}_`);
            
            const inputs = newRow.querySelectorAll('input:not([type=hidden]), select');
            inputs.forEach(input => {
                if(input.type === 'checkbox') input.checked = false;
                else input.value = '';
            });

            // برای فیلد ID مخفی که نباید کپی شود
            const idInput = newRow.querySelector('input[name$="-id"]');
            if(idInput) idInput.value = '';

            const tomanDisplay = newRow.querySelector('.toman-display');
            if(tomanDisplay) tomanDisplay.innerText = '';
            const tierError = newRow.querySelector('.tier-error');
            if(tierError) {
                tierError.innerText = '';
                tierError.classList.add('d-none');
            }
            
            newRow.style.display = '';
            tiersContainer.appendChild(newRow);
            totalForms.value = formCount + 1;
            
            toggleTierFields(); 
        });
    }

    if (tiersContainer) {
        tiersContainer.addEventListener('click', function(e) {
            if (e.target.closest('.delete-tier') || e.target.classList.contains('delete-tier')) {
                e.preventDefault();
                const row = e.target.closest('.tier-row');
                const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
                
                if (deleteCheckbox) {
                    deleteCheckbox.checked = true;
                    row.style.display = 'none';
                } else {
                    row.remove();
                }
            }
        });
    }

    // پنهان کردن ردیف‌های خالی فرم‌ست در ویرایش
    let tierRows = document.querySelectorAll('.tier-row');
    if (tierRows.length > 1) {
        tierRows.forEach(row => {
            let weightFrom = row.querySelector('input[name$="-weight_from"]');
            let weightTo = row.querySelector('input[name$="-weight_to"]');
            let price = row.querySelector('input[name$="-price"]');
            let idField = row.querySelector('input[name$="-id"]');
            
            if (weightFrom && !weightFrom.value && !weightTo.value && !price.value && (!idField || !idField.value)) {
                row.style.display = 'none';
                let deleteCheckbox = row.querySelector('input[name$="-DELETE"]');
                if(deleteCheckbox) deleteCheckbox.checked = true;
            }
        });
    }

    // ==========================================
    // ۸. اعتبارسنجی محدوده‌های وزنی
    // ==========================================
    function validateTiers() {
        let rows = Array.from(document.querySelectorAll('.tier-row')).filter(row => row.style.display !== 'none');
        let isValid = true;

        for (let i = 0; i < rows.length; i++) {
            let errorDiv = rows[i].querySelector('.tier-error');
            if(errorDiv) {
                errorDiv.classList.add('d-none');
                errorDiv.innerText = '';
            }

            let currentMinInput = rows[i].querySelector('input[name$="-weight_from"]');
            if(!currentMinInput) continue;
            
            let currentMin = parseFloat(currentMinInput.value);

            if (i > 0) {
                let prevMaxInput = rows[i - 1].querySelector('input[name$="-weight_to"]');
                if(prevMaxInput) {
                    let prevMax = parseFloat(prevMaxInput.value);

                    if (!isNaN(currentMin) && !isNaN(prevMax)) {
                        if (currentMin <= prevMax) {
                            if(errorDiv) {
                                errorDiv.innerText = `حداقل وزن در این ردیف باید بیشتر از حداکثر وزن ردیف قبل (${prevMax} کیلوگرم) باشد.`;
                                errorDiv.classList.remove('d-none');
                            }
                            isValid = false;
                        }
                    }
                }
            }
        }
        return isValid;
    }

    if (tiersContainer) {
        tiersContainer.addEventListener('input', function(e) {
            if (e.target.name && (e.target.name.includes('weight_from') || e.target.name.includes('weight_to'))) {
                validateTiers();
            }
        });
    }

    // ==========================================
    // ۹. فرمت و نمایش قیمت
    // ==========================================
    function handlePriceInput(input) {
        if (input.type === 'number') input.type = 'text';

        let valStr = input.value.split('.')[0]; 
        let rawValue = valStr.replace(/,/g, '').replace(/\D/g, '');
        let displayTag = input.closest('.price-fields') ? input.closest('.price-fields').querySelector('.toman-display') : null;
        
        if (rawValue) {
            input.value = rawValue.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
            
            if (typeof String.prototype.num2persian !== 'undefined') {
                let tomanValue = Math.floor(parseInt(rawValue) / 10);
                let tomanWords = tomanValue.toString().num2persian() + ' تومان';
                if(displayTag) displayTag.innerText = "معادل: " + tomanWords;
            }
        } else {
            input.value = '';
            if(displayTag) displayTag.innerText = '';
        }
    }

    document.querySelectorAll('input[id$="-price"]').forEach(function(input) {
        handlePriceInput(input);
    });

    if (tiersContainer) {
        tiersContainer.addEventListener('input', function(e) {
            if (e.target.tagName === 'INPUT' && e.target.id.includes('-price')) {
                handlePriceInput(e.target);
            }
        });
    }

    // ==========================================
    // ۱۰. تنظیم Datepicker شمسی و هماهنگی با جنگو
    // ==========================================
    let dateField = document.getElementById('id_valid_until');
    if (dateField) {
        if (typeof $ !== 'undefined' && $.fn.persianDatepicker) {
            dateField.removeAttribute('readonly'); 
            dateField.setAttribute('type', 'text'); 
            
            let hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = dateField.name; 
            hiddenInput.id = 'hidden_valid_until';
            hiddenInput.value = dateField.value;
            
            dateField.removeAttribute('name');
            dateField.parentNode.appendChild(hiddenInput);
            
            $(dateField).persianDatepicker({
                format: 'YYYY/MM/DD',
                autoClose: true,
                initialValue: true, 
                initialValueType: 'gregorian', 
                observer: true,
                altField: '#hidden_valid_until',
                altFieldFormatter: function (unixDate) {
                    let d = new Date(unixDate);
                    let month = '' + (d.getMonth() + 1);
                    let day = '' + d.getDate();
                    let year = d.getFullYear();

                    if (month.length < 2) month = '0' + month;
                    if (day.length < 2) day = '0' + day;

                    return [year, month, day].join('-');
                }
            });
        }
    }

    // ==========================================
    // ۱۱. Submit فرم و بررسی نهایی خطاها
    // ==========================================
    const rateForm = document.getElementById('rate-form');
    if (rateForm) {
        rateForm.addEventListener('submit', function(e) {
            let hasError = false;

            if (!validateTiers()) hasError = true;

            let hiddenDateInput = document.getElementById('hidden_valid_until') || dateField;
            let dateErrorDiv = document.getElementById('date-error');
            
            if (hiddenDateInput && hiddenDateInput.value) {
                let selectedDate = new Date(hiddenDateInput.value);
                selectedDate.setHours(0,0,0,0);
                
                let tomorrow = new Date();
                tomorrow.setDate(tomorrow.getDate() + 1);
                tomorrow.setHours(0,0,0,0);

                if (selectedDate < tomorrow) {
                    if(dateErrorDiv) {
                        dateErrorDiv.innerText = "تاریخ اعتبار باید حداقل یک روز پس از تاریخ امروز باشد.";
                        dateErrorDiv.classList.remove('d-none');
                    }
                    hasError = true;
                } else {
                    if(dateErrorDiv) dateErrorDiv.classList.add('d-none');
                }
            }

            if (hasError) {
                e.preventDefault(); 
                window.scrollTo({ top: 0, behavior: 'smooth' });
            } else {
                document.querySelectorAll('input[id$="-price"]').forEach(function(input) {
                    let valStr = input.value.split('.')[0];
                    input.value = valStr.replace(/,/g, '');
                });
            }
        });
    }

    // ==========================================
    // ۱۲. دکمه حذف نرخ (در صورت وجود)
    // ==========================================
    let deleteBtn = document.getElementById('deleteBtn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function() {
            if (confirm('آیا از حذف این نرخ اطمینان دارید؟ این عمل غیرقابل بازگشت است.')) {
                const url = this.getAttribute('data-url');
                
                fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success && typeof rateListUrl !== 'undefined') {
                        window.location.href = rateListUrl;
                    } else {
                        alert('خطا در حذف نرخ.');
                    }
                })
                .catch(error => console.error('Error:', error));
            }
        });
    }
});
