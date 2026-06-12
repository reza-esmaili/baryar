document.addEventListener('DOMContentLoaded', function() {
    // گرفتن المنت‌ها
    const originProvince = document.querySelector('select[name="origin_province"]');
    const originCity = document.querySelector('select[name="origin_city"]');
    
    const destCountry = document.querySelector('select[name="destination_country"]');
    const destCity = document.querySelector('select[name="destination_city"]');
    const transportMode = document.querySelector('select[name="transport_mode"]');
    const destPort = document.querySelector('select[name="destination_port"]');
    const cargoType = document.querySelector('select[name="cargo_type"]'); 

    const dimensionsSection = document.getElementById('dimensions-section');
    const containerSection = document.getElementById('container-section');

    // 1. استان -> شهر مبدا
    if (originProvince && originCity) {
        if (!originProvince.value && !originCity.value) {
            originCity.innerHTML = '<option value="" disabled selected>ابتدا استان را انتخاب کنید</option>';
            originCity.disabled = true;
        }

        originProvince.addEventListener('change', function() {
            const provinceId = this.value;
            if (provinceId) {
                originCity.disabled = false;
                originCity.innerHTML = '<option value="">در حال بارگذاری...</option>';
                
                fetch(`/locations/ajax/cities/?province_id=${provinceId}`)
                    .then(res => res.json())
                    .then(data => {
                        originCity.innerHTML = '<option value="">---------</option>';
                        data.forEach(city => {
                            originCity.innerHTML += `<option value="${city.id}">${city.name}</option>`;
                        });
                    })
                    .catch(err => console.error('خطا در بارگذاری شهرها:', err));
            } else {
                originCity.innerHTML = '<option value="" disabled selected>ابتدا استان را انتخاب کنید</option>';
                originCity.disabled = true;
            }
        });
    }

    // 2. کشور -> شهر مقصد
    if (destCountry && destCity) {
        if (!destCountry.value && !destCity.value) {
            destCity.innerHTML = '<option value="" disabled selected>ابتدا کشور را انتخاب کنید</option>';
            destCity.disabled = true;
        }

        destCountry.addEventListener('change', function() {
            const countryId = this.value;
            
            if (destPort) {
                destPort.innerHTML = '<option value="" disabled selected>ابتدا شهر و روش حمل انتخاب شود</option>';
                destPort.disabled = true;
            }

            if (countryId) {
                destCity.disabled = false;
                destCity.innerHTML = '<option value="">در حال بارگذاری...</option>';
                
                fetch(`/locations/ajax/destination-cities/?country_id=${countryId}`)
                    .then(res => res.json())
                    .then(data => {
                        destCity.innerHTML = '<option value="">---------</option>';
                        data.forEach(city => {
                            destCity.innerHTML += `<option value="${city.id}">${city.name}</option>`;
                        });
                    })
                    .catch(err => console.error('خطا در بارگذاری شهرهای مقصد:', err));
            } else {
                destCity.innerHTML = '<option value="" disabled selected>ابتدا کشور را انتخاب کنید</option>';
                destCity.disabled = true;
            }
        });
    }

    // 3. لود کردن پورت‌ها
    function loadPorts() {
        if (!destCity || !destPort || !transportMode) return;
        
        const cityId = destCity.value;
        const mode = transportMode.value;
        const previousPortValue = destPort.value;
        
        if (!cityId || !mode) {
            destPort.innerHTML = '<option value="" disabled selected>ابتدا شهر و روش حمل انتخاب شود</option>';
            destPort.disabled = true;
            return;
        }

        destPort.disabled = false;
        destPort.innerHTML = '<option value="">در حال بارگذاری...</option>';

        fetch(`/locations/ajax/ports/?city_id=${cityId}&transport_mode=${mode}`)
            .then(res => res.json())
            .then(data => {
                destPort.innerHTML = '<option value="">---------</option>';
                if (data.length > 0) {
                    data.forEach(port => {
                        const isSelected = (port.id.toString() === previousPortValue) ? 'selected' : '';
                        destPort.innerHTML += `<option value="${port.id}" ${isSelected}>${port.name}</option>`;
                    });
                    if (previousPortValue) destPort.value = previousPortValue;
                } else {
                    destPort.innerHTML = '<option value="" disabled>پورتی برای این روش یافت نشد</option>';
                }
            })
            .catch(err => console.error('خطا در بارگذاری پورت‌ها:', err));
    }

    // 4. لود کردن نوع کالا
    function loadCargoTypes() {
        if (!transportMode || !cargoType) return;
        const mode = transportMode.value;
        const previousCargoValue = cargoType.value;

        if (!mode) {
            cargoType.innerHTML = '<option value="" disabled selected>ابتدا روش حمل را انتخاب کنید</option>';
            cargoType.disabled = true;
            return;
        }

        cargoType.disabled = false;
        cargoType.innerHTML = '<option value="">در حال بارگذاری...</option>';

        fetch(`/orders/ajax/cargo-types/?transport_mode=${mode}`)
            .then(res => res.json())
            .then(data => {
                cargoType.innerHTML = '<option value="">---------</option>';
                if (data.length > 0) {
                    data.forEach(cargo => {
                        const isSelected = (cargo.id.toString() === previousCargoValue) ? 'selected' : '';
                        cargoType.innerHTML += `<option value="${cargo.id}" ${isSelected}>${cargo.name}</option>`;
                    });
                    if (previousCargoValue) cargoType.value = previousCargoValue;
                } else {
                    cargoType.innerHTML = '<option value="" disabled>کالایی برای این روش تعریف نشده</option>';
                }
            })
            .catch(err => console.error('خطا در بارگذاری نوع کالا:', err));
    }

    // 5. مدیریت جامع تغییر روش حمل
    function handleTransportModeChange() {
        if (!transportMode) return;
        const mode = transportMode.value;

        loadPorts();
        loadCargoTypes();

        const dimensionsSection = document.getElementById('dimensions-section');
        const containerSection = document.getElementById('container-section');
        const weightSection = document.getElementById('weight-section');

        const toggleElements = (section, isDisable) => {
            if (!section) return;
            const elements = section.querySelectorAll('input, select, textarea');
            elements.forEach(el => {
                if (el.type !== 'hidden' && !el.name.includes('TOTAL_FORMS') && !el.name.includes('INITIAL_FORMS')) {
                    el.disabled = isDisable;
                }
            });
        };

        if (mode === 'sea_fcl' || mode === 'FCL') { 
            if(containerSection) containerSection.style.display = 'block';
            if(dimensionsSection) dimensionsSection.style.display = 'none';
            if(weightSection) weightSection.style.display = 'none';
            
            toggleElements(dimensionsSection, true); 
            toggleElements(weightSection, true);
            toggleElements(containerSection, false); 
        } else {
            if(containerSection) containerSection.style.display = 'none';
            if(dimensionsSection) dimensionsSection.style.display = 'block';
            if(weightSection) weightSection.style.display = 'block';
            
            toggleElements(dimensionsSection, false); 
            toggleElements(weightSection, false);
            toggleElements(containerSection, true);   
        }
    }

    if (destCity) destCity.addEventListener('change', loadPorts);
    if (transportMode) {
        transportMode.addEventListener('change', handleTransportModeChange);
        handleTransportModeChange(); 
    }

    // 6. Formset داینامیک برای ابعاد
    const addBtn = document.getElementById('custom-add-btn');
    const formsContainer = document.getElementById('dimension-forms');
    const totalForms = document.getElementById('id_dimensions-TOTAL_FORMS'); 

    function updateFormIndexes() {
        const rows = formsContainer.querySelectorAll('.dimension-form-row');
        if(totalForms) totalForms.value = rows.length;
        
        rows.forEach((row, index) => {
            row.querySelectorAll('input, select, textarea, label').forEach(el => {
                if (el.id) el.id = el.id.replace(/-\d+-/, `-${index}-`);
                if (el.name) el.name = el.name.replace(/-\d+-/, `-${index}-`);
                if (el.htmlFor) el.htmlFor = el.htmlFor.replace(/-\d+-/, `-${index}-`);
            });
        });
    }

    if (addBtn && formsContainer && totalForms) {
        addBtn.onclick = function(e) {
            e.preventDefault();
            const rows = formsContainer.querySelectorAll('.dimension-form-row');
            if (rows.length === 0) return;
            
            const newRow = rows[0].cloneNode(true);
            newRow.querySelectorAll('input, select, textarea').forEach(input => {
                if(input.name.includes('quantity')) {
                    input.value = 1; 
                } else if (input.type !== 'hidden') {
                    input.value = ''; 
                } else if (input.name.includes('id')) {
                    input.value = ''; 
                }
            });
            newRow.querySelectorAll('.errorlist').forEach(err => err.remove());
            
            formsContainer.appendChild(newRow);
            updateFormIndexes();
        };

        formsContainer.onclick = function(e) {
            const deleteBtn = e.target.closest('.delete-row-btn');
            if (deleteBtn) {
                e.preventDefault();
                const rows = formsContainer.querySelectorAll('.dimension-form-row');
                if (rows.length > 1) {
                    const rowToRemove = deleteBtn.closest('.dimension-form-row');
                    rowToRemove.remove();
                    updateFormIndexes(); 
                } else {
                    alert('حداقل یک ردیف ابعاد باید وجود داشته باشد.');
                }
            }
        };
    }

    // ==========================================
    // 7. ارسال AJAX فرم برای محاسبه استعلام
    // ==========================================
    const cargoForm = document.getElementById('cargo-request-form');
    const resultsSection = document.getElementById('results-section');
    const ratesTbody = document.getElementById('rates-tbody');
    const displayCw = document.getElementById('display_chargeable_weight');
    
    if (cargoForm) {
        cargoForm.addEventListener('submit', function(e) {
            // اگر کاربر روی دکمه ثبت سفارش کلیک کرده باشد، فیلد مخفی پر است، پس اجازه ارسال عادی (بدون AJAX) را می‌دهیم
            if (document.getElementById('selected_rate_id').value !== "") {
                return;
            }
            
            e.preventDefault(); // جلوگیری از رفرش صفحه هنگام استعلام
            
            const formData = new FormData(cargoForm);
            const submitBtn = document.getElementById('calculate-btn');
            submitBtn.disabled = true;
            submitBtn.innerText = 'در حال محاسبه...';
            
            fetch('/orders/ajax/calculate-rates/', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' } // برای تشخیص AJAX در جنگو (اختیاری)
            })
            .then(res => res.json())
            .then(data => {
                submitBtn.disabled = false;
                submitBtn.innerText = 'محاسبه قیمت (استعلام)';
                
                if (data.success) {
                    resultsSection.style.display = 'block';
                    displayCw.innerText = parseFloat(data.chargeable_weight).toLocaleString('fa-IR');
                    
                    ratesTbody.innerHTML = '';
                    if (data.rates.length === 0) {
                        ratesTbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">هیچ نرخی یافت نشد.</td></tr>';
                    } else {
                        data.rates.forEach(rate => {
                            const unitPriceFmt = new Intl.NumberFormat('fa-IR').format(rate.unit_price) + ' ریال';
                            const totalPriceFmt = new Intl.NumberFormat('fa-IR').format(rate.total_price) + ' ریال';
                            
                            ratesTbody.innerHTML += `
                                <tr>
                                    <td class="fw-bold">${rate.company_name}</td>
                                    <td>${unitPriceFmt}</td>
                                    <td class="text-success fw-bold">${totalPriceFmt}</td>
                                    <td>
                                        <button type="button" class="btn btn-success btn-sm select-rate-btn" 
                                            data-rate-id="${rate.rate_id}" 
                                            data-cw="${data.chargeable_weight}" 
                                            data-price="${rate.total_price}">
                                            انتخاب و ثبت سفارش
                                        </button>
                                    </td>
                                </tr>
                            `;
                        });
                    }
                    // اسکرول نرم به بخش نتایج
                    resultsSection.scrollIntoView({ behavior: 'smooth' });
                } else {
                    alert('فرم دارای خطا است. لطفاً فیلدهای اجباری را بررسی کنید.');
                    console.log(data.errors);
                }
            })
            .catch(err => {
                submitBtn.disabled = false;
                submitBtn.innerText = 'محاسبه قیمت (استعلام)';
                console.error('خطا در دریافت نتایج AJAX:', err);
                alert('خطا در برقراری ارتباط با سرور.');
            });
        });

        // ==========================================
        // 8. هندل کردن کلیک روی "ثبت سفارش"
        // ==========================================
        ratesTbody.addEventListener('click', function(e) {
            if (e.target.classList.contains('select-rate-btn')) {
                const btn = e.target;
                const rateId = btn.getAttribute('data-rate-id');
                const cw = btn.getAttribute('data-cw');
                const price = btn.getAttribute('data-price');
                
                // پر کردن فیلدهای مخفی فرم
                document.getElementById('selected_rate_id').value = rateId;
                document.getElementById('hidden_chargeable_weight').value = cw;
                document.getElementById('hidden_final_price').value = price;
                
                // تغییر آدرس فرم به مسیر ثبت سفارش (view جدید) و ارسال فرم
                cargoForm.action = '/orders/request/submit/';
                cargoForm.submit(); 
            }
        });
    }
});
