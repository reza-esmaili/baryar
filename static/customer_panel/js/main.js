document.addEventListener('DOMContentLoaded', function() {
    const addBtn = document.getElementById('add-dimension');
    const formsContainer = document.getElementById('dimension-forms');
    const totalFormsInput = document.getElementById('id_dimensions-TOTAL_FORMS');

    if (addBtn && formsContainer && totalFormsInput) {
        addBtn.addEventListener('click', function() {
            // دریافت تعداد فرم‌های فعلی
            let formIdx = parseInt(totalFormsInput.value);
            
            // گرفتن اولین فرم به عنوان الگو
            let formRows = document.querySelectorAll('.dimension-form-row');
            if (formRows.length === 0) return;
            
            let newForm = formRows[0].cloneNode(true);
            
            // جایگزینی ایندکس‌های قدیمی (مانند 0) با ایندکس جدید
            newForm.innerHTML = newForm.innerHTML.replace(/-0-/g, `-${formIdx}-`);
            newForm.innerHTML = newForm.innerHTML.replace(/_0_/g, `_${formIdx}_`);
            
            // پاک کردن مقادیر قبلی در فرم جدید
            let inputs = newForm.querySelectorAll('input');
            inputs.forEach(input => {
                if(input.type !== 'hidden' && input.type !== 'checkbox') {
                    input.value = '';
                }
            });

            // افزودن فرم جدید به کانتینر
            formsContainer.appendChild(newForm);
            
            // به‌روزرسانی تعداد کل فرم‌ها در منیجمنت فرم
            totalFormsInput.value = formIdx + 1;
        });
    }
});
