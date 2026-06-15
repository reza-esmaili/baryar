$(document).ready(function () {

    $('.select2-multiple').select2({
        placeholder: "زیردسته‌های کالا را انتخاب کنید",
        allowClear: true,
        width: '100%',
        dir: "rtl"
    });

    const $checkbox = $('#is_for_other_checkbox');
    const $name = $('#id_sender_name');
    const $national = $('#id_sender_national_id');
    const $phone = $('#id_sender_phone');
    const $user = $('#current_user_data');

    function restoreUserData() {
        $name.val($user.data('name'));
        $national.val($user.data('national-id'));
        $phone.val($user.data('phone'));
    }

    if ($checkbox.length) {
        $checkbox.on('change', function () {
            if ($(this).is(':checked')) {
                $name.val('');
                $national.val('');
                $phone.val('');
            } else {
                restoreUserData();
            }
        });
    }

    $('#complete-order-form').on('submit', function () {
        const btn = $('#submit-btn');

        btn.prop('disabled', true);
        btn.html(`
            <span class="spinner-border spinner-border-sm"></span>
            در حال ثبت سفارش...
        `);
    });

    // ---------------------------
    // Wizard / Step Navigation
    // ---------------------------
    const panels = document.querySelectorAll('.complete-step-panel');
    const indicators = document.querySelectorAll('.complete-step-item');

    const prevBtn = document.getElementById('complete-prev-btn');
    const nextBtn = document.getElementById('complete-next-btn');
    const submitBtn = document.getElementById('submit-btn');

    const form = document.getElementById('complete-order-form');

    let currentStep = 1;
    const totalSteps = panels.length || 5;

    function showStep(step) {
        panels.forEach(panel => {
            const panelStep = Number(panel.dataset.step);
            panel.classList.toggle('active', panelStep === step);
        });

        indicators.forEach(indicator => {
            const indicatorStep = Number(indicator.dataset.stepIndicator);
            indicator.classList.toggle('active', indicatorStep === step);
            indicator.classList.toggle('done', indicatorStep < step);
        });

        if (prevBtn) {
            prevBtn.style.display = step === 1 ? 'none' : 'inline-flex';
        }

        if (nextBtn) {
            nextBtn.style.display = step === totalSteps ? 'none' : 'inline-flex';
        }

        if (submitBtn) {
            submitBtn.style.display = step === totalSteps ? 'inline-flex' : 'none';
        }

        // const firstActivePanel = document.querySelector(`.complete-step-panel[data-step="${step}"]`);

        // if (firstActivePanel) {
        //     firstActivePanel.scrollIntoView({
        //         behavior: 'smooth',
        //         block: 'start'
        //     });
        // }

    }

    function getStepFields(step) {
        const activePanel = document.querySelector(`.complete-step-panel[data-step="${step}"]`);

        if (!activePanel) {
            return [];
        }

        return Array.from(activePanel.querySelectorAll('input, select, textarea')).filter(field => {
            return !field.disabled && field.type !== 'hidden';
        });
    }

    function clearFieldError(field) {
        field.classList.remove('field-error');

        const wrapper = field.closest('.form-group') || field.parentElement;
        if (!wrapper) {
            return;
        }

        const oldMessage = wrapper.querySelector('.client-error-message');
        if (oldMessage) {
            oldMessage.remove();
        }
    }

    function showFieldError(field, message) {
        field.classList.add('field-error');

        const wrapper = field.closest('.form-group') || field.parentElement;
        if (!wrapper) {
            return;
        }

        const oldMessage = wrapper.querySelector('.client-error-message');
        if (oldMessage) {
            oldMessage.remove();
        }

        const error = document.createElement('div');
        error.className = 'client-error-message';
        error.innerText = message;

        wrapper.appendChild(error);
    }

    function validateCurrentStep() {
        const fields = getStepFields(currentStep);
        let isValid = true;
        let firstInvalidField = null;

        fields.forEach(field => {
            clearFieldError(field);

            const isRequired = field.hasAttribute('required');
            if (!isRequired) {
                return;
            }

            let valueIsEmpty = false;
            if (field.tagName === 'SELECT') {
                if (field.multiple) {
                    valueIsEmpty = !Array.from(field.selectedOptions).length;
                } else {
                    valueIsEmpty = !field.value;
                }
            } else if (field.type === 'checkbox' || field.type === 'radio') {
                const sameNameFields = form.querySelectorAll(`[name="${field.name}"]`);
                valueIsEmpty = !Array.from(sameNameFields).some(item => item.checked);
            } else if (field.type === 'file') {
                valueIsEmpty = !field.files || field.files.length === 0;
            } else {
                valueIsEmpty = !field.value.trim();
            }


            if (valueIsEmpty) {
                isValid = false;

                if (!firstInvalidField) {
                    firstInvalidField = field;
                }

                showFieldError(field, 'تکمیل این فیلد الزامی است.');
            }
        });

        if (!isValid && firstInvalidField) {
            firstInvalidField.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });

            setTimeout(() => {
                firstInvalidField.focus();
            }, 400);
        }

        return isValid;
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', function () {
            if (!validateCurrentStep()) {
                return;
            }

            if (currentStep < totalSteps) {
                currentStep += 1;
                showStep(currentStep);
            }
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', function () {
            if (currentStep > 1) {
                currentStep -= 1;
                showStep(currentStep);
            }
        });
    }

    /**
     * اگر بعد از submit خطای سمت سرور وجود داشت،
     * کاربر را به اولین مرحله دارای خطا می‌بریم.
     */
    function goToStepWithServerErrors() {
        const errorLists = document.querySelectorAll('.errorlist');

        if (!errorLists.length) {
            return false;
        }

        const firstError = errorLists[0];
        const errorPanel = firstError.closest('.complete-step-panel');

        if (!errorPanel) {
            return false;
        }

        const step = Number(errorPanel.dataset.step);

        if (!step) {
            return false;
        }

        currentStep = step;
        showStep(currentStep);

        return true;
    }

    const hasServerErrorStep = goToStepWithServerErrors();

    if (!hasServerErrorStep) {
        showStep(currentStep);
    }

    // Select2 after step init if needed
    if ($('.select2-multiple').length) {
        $('.select2-multiple').select2({
            placeholder: "زیردسته‌های کالا را انتخاب کنید",
            allowClear: true,
            width: '100%',
            dir: "rtl"
        });
    }
});
