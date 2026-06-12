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
    
    const validUntilInput = document.querySelector('input[name="valid_until"]');
    const cargoContainer = document.getElementById('cargo-types-container');
    const selectedDataElement = document.getElementById('selected_cargo_data');
    const tiersContainer = document.getElementById('tiers-container');

       // ==========================================
    // ۲. وابستگی استان مبدا -> شهر مبدا (با AJAX)
    // ==========================================
    function checkOriginCityState() {
        if (!provinceSelect || !originCitySelect) return;
        if (!provinceSelect.value) {
            originCitySelect.innerHTML = '<option value="" disabled selected>ابتدا استان مبدا را مشخص کنید</option>';
            originCitySelect.disabled = true;
        } else {
            originCitySelect.disabled = false;
        }
    }

    if (provinceSelect && originCitySelect) {
        checkOriginCityState(); // بررسی در زمان لود صفحه
        
        provinceSelect.addEventListener('change', function() {
            checkOriginCityState();
            const provinceId = this.value;
            
            if (provinceId) {
                originCitySelect.innerHTML = '<option value="">در حال بارگذاری...</option>';
                fetch(`/rates/ajax/load-cities/?province_id=${provinceId}`)
                    .then(response => response.json())
                    .then(data => {
                        originCitySelect.innerHTML = '<option value="">---------</option>';
                        data.forEach(city => {
                            originCitySelect.innerHTML += `<option value="${city.id}">${city.name}</option>`;
                        });
                    })
                    .catch(error => console.error('Error loading cities:', error));
            }
        });
    }

    // ==========================================
    // ۳. وابستگی کشور مقصد -> شهر مقصد (با AJAX)
    // ==========================================
    function checkDestCityState() {
        if (!destCountrySelect || !destCitySelect) return;
        if (!destCountrySelect.value) {
            destCitySelect.innerHTML = '<option value="" disabled selected>ابتدا کشور مقصد را مشخص کنید</option>';
            destCitySelect.disabled = true;
        } else {
            destCitySelect.disabled = false;
        }
    }

    if (destCountrySelect && destCitySelect) {
        checkDestCityState(); // بررسی در زمان لود صفحه
        
        destCountrySelect.addEventListener('change', function() {
            checkDestCityState();
            const countryId = this.value;
            
            // ریست کردن پورت در صورت تغییر کشور
            if (destPortSelect) {
                destPortSelect.innerHTML = '<option value="" disabled selected>ابتدا مشخصات مقصد و روش حمل را وارد کنید</option>';
                destPortSelect.disabled = true;
            }
            
            if (countryId) {
                destCitySelect.innerHTML = '<option value="">در حال بارگذاری...</option>';
                fetch(`/rates/ajax/load-destination-cities/?country_id=${countryId}`)
                    .then(response => response.json())
                    .then(data => {
                        destCitySelect.innerHTML = '<option value="">---------</option>';
                        data.forEach(city => {
                            destCitySelect.innerHTML += `<option value="${city.id}">${city.name}</option>`;
                        });
                    });
            }
        });
    }

    // ==========================================
    // ۴. وابستگی شهر مقصد + روش حمل -> پورت مقصد (با AJAX)
    // ==========================================
    function loadPorts() {
        if (!destCountrySelect || !destCitySelect || !destPortSelect || !transportModeSelect) return;
        
        const countryId = destCountrySelect.value;
        const cityId = destCitySelect.value;
        const transportMode = transportModeSelect.value;
        
        if (!countryId || !cityId || !transportMode) {
            destPortSelect.innerHTML = '<option value="" disabled selected>ابتدا مشخصات مقصد و روش حمل را وارد کنید</option>';
            destPortSelect.disabled = true;
            return;
        }

        destPortSelect.disabled = false;
        destPortSelect.innerHTML = '<option value="">در حال بارگذاری...</option>';

        fetch(`/rates/ajax/load-ports/?city_id=${cityId}&transport_mode=${transportMode}`)
            .then(response => response.json())
            .then(data => {
                destPortSelect.innerHTML = '<option value="">---------</option>';
                data.forEach(port => {
                    destPortSelect.innerHTML += `<option value="${port.id}">${port.name}</option>`;
                });
            });
    }

    // بررسی اولیه پورت‌ها در زمان لود صفحه
    if (destPortSelect) {
        if (!destCountrySelect?.value || !destCitySelect?.value || !transportModeSelect?.value) {
            destPortSelect.innerHTML = '<option value="" disabled selected>ابتدا مشخصات مقصد و روش حمل را وارد کنید</option>';
            destPortSelect.disabled = true;
        }
    }

    if (destCitySelect) destCitySelect.addEventListener('change', loadPorts);
    if (transportModeSelect) transportModeSelect.addEventListener('change', loadPorts);
    // ==========================================
    // ۵. وابستگی واحد قیمت‌گذاری -> روش حمل
    // ==========================================
    function updatePricingUnitOptions() {
        if (!transportModeSelect) return;

        const transportMode = transportModeSelect.value.toUpperCase(); 
        
        // پیدا کردن تمام فیلدهای واحد قیمت‌گذاری (چون داخل فرم‌ست هستند و ممکن است چند ردیف باشند)
        const pricingUnitSelects = document.querySelectorAll('select[name$="-pricing_unit"]');

        pricingUnitSelects.forEach(select => {
            const currentValue = select.value; // نگهداری مقدار انتخاب شده قبلی
            select.innerHTML = ''; // پاک کردن گزینه‌های فعلی

            if (!transportMode) {
                select.innerHTML = '<option value="" disabled selected>ابتدا روش حمل را مشخص کنید</option>';
                select.disabled = true;
                return;
            }

            select.disabled = false;
            select.innerHTML = '<option value="" selected>---------</option>';

            // مقادیر value با حروف کوچک تنظیم شده‌اند تا با مدل جنگو دقیقاً تطابق داشته باشند
            if (transportMode === 'AIR') {
                select.innerHTML += '<option value="fixed">نرخ ثابت (Fixed)</option>';
                select.innerHTML += '<option value="per_kg">به ازای هر کیلوگرم (Per KG)</option>';
                
            } else if (transportMode === 'SEA_FCL') {
                select.innerHTML += '<option value="per_container">به ازای هر کانتینر (Per Container)</option>';
                
            } else if (transportMode === 'SEA_LCL') {
                select.innerHTML += '<option value="fixed">نرخ ثابت (Fixed)</option>';
                select.innerHTML += '<option value="per_kg">به ازای هر کیلوگرم (Per KG)</option>';
                
            } else {
                select.innerHTML += '<option value="fixed">نرخ ثابت (Fixed)</option>';
                select.innerHTML += '<option value="per_kg">به ازای هر کیلوگرم (Per KG)</option>';
                select.innerHTML += '<option value="per_container">به ازای هر کانتینر (Per Container)</option>';
            }

            // اگر مقدار قبلی هنوز در گزینه‌های جدید وجود داشت، آن را دوباره انتخاب کن
            if (currentValue && select.querySelector(`option[value="${currentValue}"]`)) {
                select.value = currentValue;
            }
        });
    }

    if (transportModeSelect) {
        updatePricingUnitOptions(); // بررسی و اعمال در زمان لود صفحه
        transportModeSelect.addEventListener('change', updatePricingUnitOptions);
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
    // ۷. منطق دکمه‌های فرم‌ست (افزودن و حذف) و پنهان کردن فرم‌های خالی
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

            // پاک کردن نمایش قیمت تومانی و ارور در ردیف جدید
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

    // پنهان کردن ردیف‌های خالی فرم‌ست در صورت وجود
    let tierRows = document.querySelectorAll('.tier-row');
    if (tierRows.length > 1) {
        tierRows.forEach(row => {
            let weightFrom = row.querySelector('input[name$="-weight_from"]');
            let weightTo = row.querySelector('input[name$="-weight_to"]');
            let price = row.querySelector('input[name$="-price"]');
            
            if (weightFrom && !weightFrom.value && !weightTo.value && !price.value) {
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
    // ۱۰. تنظیم تقویم شمسی و حداقل تاریخ
    // ==========================================
    let dateField = document.getElementById('id_valid_until');
    if (dateField) {
        // ایجاد محدودیت حداقل تاریخ مرورگر در صورت عدم پشتیبانی از JS
        let tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        let yyyy = tomorrow.getFullYear();
        let mm = String(tomorrow.getMonth() + 1).padStart(2, '0');
        let dd = String(tomorrow.getDate()).padStart(2, '0');
        dateField.setAttribute('min', `${yyyy}-${mm}-${dd}`);

        // راه‌اندازی Persian Datepicker
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
                initialValue: !dateField.value, 
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

            // بررسی وزن‌ها
            if (!validateTiers()) hasError = true;

            // بررسی تاریخ
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
                // پاک کردن کاماها قبل از ارسال
                document.querySelectorAll('input[id$="-price"]').forEach(function(input) {
                    let valStr = input.value.split('.')[0];
                    input.value = valStr.replace(/,/g, '');
                });
            }
        });
    }
        // ==========================================
    // ۱۲. بارگذاری داینامیک نوع کالا بر اساس روش حمل
    // ==========================================
    function loadCargoTypes() {
        if (!transportModeSelect || !cargoContainer) return;

        const transportMode = transportModeSelect.value;
        if (!transportMode) {
            cargoContainer.innerHTML = '<span class="text-muted small">ابتدا روش حمل را انتخاب کنید.</span>';
            return;
        }

        cargoContainer.innerHTML = '<span class="text-muted small">در حال بارگذاری...</span>';

        // بررسی کالاهای از پیش انتخاب شده در حالت ویرایش
        let selectedIds = [];
        if (selectedDataElement) {
            try {
                const parsedData = JSON.parse(selectedDataElement.textContent);
                selectedIds = parsedData.map(item => item.id || item.pk || item);
            } catch (e) {
                console.error('Error parsing selected cargo data:', e);
            }
        }

        fetch(`${loadCargoTypesUrl}?transport_mode=${transportMode}`)
            .then(response => response.json())
            .then(data => {
                cargoContainer.innerHTML = ''; 
                
                if (data.length === 0) {
                    cargoContainer.innerHTML = '<span class="text-muted small">کالایی برای این روش حمل یافت نشد.</span>';
                    return;
                }

                data.forEach(cargo => {
                    const isChecked = selectedIds.includes(cargo.id) ? 'checked' : '';
                    const div = document.createElement('div');
                    div.className = 'form-check form-check-inline me-3 mb-2';
                    div.innerHTML = `
                        <input class="form-check-input" type="checkbox" name="cargo_types" id="cargo_${cargo.id}" value="${cargo.id}" ${isChecked}>
                        <label class="form-check-label" style="cursor: pointer;" for="cargo_${cargo.id}">${cargo.name}</label>
                    `;
                    cargoContainer.appendChild(div);
                });
            })
            .catch(error => {
                console.error('Error loading cargo types:', error);
                cargoContainer.innerHTML = '<span class="text-danger small">خطا در ارتباط با سرور.</span>';
            });
    }

    if (transportModeSelect) {
        // اجرای تابع هنگام تغییر روش حمل
        transportModeSelect.addEventListener('change', loadCargoTypes);
        
        // اجرای تابع هنگام لود صفحه (برای زمان ویرایش نرخ که روش حمل از قبل مقدار دارد)
        if (transportModeSelect.value) {
            loadCargoTypes();
        }
    }

});
