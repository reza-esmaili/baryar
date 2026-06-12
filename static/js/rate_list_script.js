document.addEventListener('DOMContentLoaded', function() {
    
    // 1. ارسال خودکار فرم فیلتر هنگام تغییر دراپ‌داون‌ها
    const filterSelects = document.querySelectorAll('.filter-select');
    const filterForm = document.getElementById('filter-form');
    
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            filterForm.submit();
        });
    });

    // 2. تابع کمکی برای گرفتن توکن CSRF
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // 3. تغییر وضعیت (Toggle Switch)
    const toggleInputs = document.querySelectorAll('.toggle-rate-status');
    toggleInputs.forEach(input => {
        input.addEventListener('change', function() {
            const url = this.getAttribute('data-url');
            const isActive = this.checked;

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    'is_active': isActive
                })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    this.checked = !isActive;
                    alert('خطا در تغییر وضعیت!');
                }
            })
            .catch(error => {
                this.checked = !isActive;
                console.error('Error:', error);
            });
        });
    });

    // 4. حذف نرخ تکی
    const deleteButtons = document.querySelectorAll('.delete-rate-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            if (confirm('آیا از حذف این نرخ اطمینان دارید؟ این عمل غیرقابل بازگشت است.')) {
                const url = this.getAttribute('data-url');
                const row = this.closest('tr');

                fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        row.style.opacity = '0';
                        setTimeout(() => row.remove(), 300);
                    } else {
                        alert('خطا در حذف نرخ: ' + (data.error || 'ناشناخته'));
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('خطایی در ارتباط با سرور رخ داد.');
                });
            }
        });
    });

    // ========================================================
    // 5. قابلیت انتخاب و حذف دسته‌جمعی (Bulk Delete)
    // ========================================================
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const rateCheckboxes = document.querySelectorAll('.rate-checkbox');
    const bulkActionContainer = document.getElementById('bulk-action-container');
    const selectedCountText = document.getElementById('selected-count');
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');

    // تابع بروزرسانی UI نوار ابزار حذف دسته‌جمعی
    function updateBulkActionUI() {
        if (!rateCheckboxes.length) return;

        const checkedBoxes = document.querySelectorAll('.rate-checkbox:checked');
        const checkedCount = checkedBoxes.length;

        // وضعیت دکمه «انتخاب همه»
        selectAllCheckbox.checked = checkedCount > 0 && checkedCount === rateCheckboxes.length;

        // نمایش یا مخفی کردن کانتینر
        if (checkedCount > 0) {
            bulkActionContainer.classList.remove('hidden');
            selectedCountText.textContent = checkedCount;
        } else {
            bulkActionContainer.classList.add('hidden');
        }
    }

    // رویداد تیک زدن «انتخاب همه»
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const isChecked = this.checked;
            rateCheckboxes.forEach(cb => {
                cb.checked = isChecked;
            });
            updateBulkActionUI();
        });
    }

    // رویداد تیک زدن چک‌باکس‌های تکی
    rateCheckboxes.forEach(cb => {
        cb.addEventListener('change', updateBulkActionUI);
    });

    // عملیات ارسال اطلاعات برای حذف گروهی
    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', function() {
            const checkedBoxes = document.querySelectorAll('.rate-checkbox:checked');
            if (checkedBoxes.length === 0) return;

            if (confirm(`آیا از حذف ${checkedBoxes.length} نرخ انتخاب شده اطمینان دارید؟`)) {
                const url = this.getAttribute('data-url');
                // استخراج ID های انتخاب شده
                const idsToDelete = Array.from(checkedBoxes).map(cb => cb.value);

                fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ ids: idsToDelete })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // حذف بصری (انیمیشن) ردیف‌های حذف شده از جدول
                        checkedBoxes.forEach(cb => {
                            const row = cb.closest('tr');
                            row.style.opacity = '0';
                            setTimeout(() => row.remove(), 300);
                        });
                        // مخفی کردن نوار ابزار پس از 310 میلی‌ثانیه
                        setTimeout(updateBulkActionUI, 310);
                    } else {
                        alert('خطا در حذف گروهی: ' + (data.error || 'خطای سرور'));
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('خطایی در ارتباط با سرور رخ داد.');
                });
            }
        });
    }
});
