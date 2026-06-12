// statics/forwarder_panel/js/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    // تابعی برای تبدیل اعداد بزرگ به فرمت خوانا (میلیون/میلیارد) مشابه تصویر
    function formatLargeNumbers() {
        const amountElements = document.querySelectorAll('.format-large-number');
        
        amountElements.forEach(el => {
            const value = parseInt(el.getAttribute('data-value'));
            if (!isNaN(value)) {
                if (value >= 1000000000) {
                    // میلیارد
                    const formatted = (value / 1000000000).toFixed(1);
                    el.textContent = formatted + ' میلیارد';
                } else if (value >= 1000000) {
                    // میلیون
                    const formatted = (value / 1000000).toFixed(1);
                    el.textContent = formatted + ' میلیون';
                } else {
                    el.textContent = value.toLocaleString('fa-IR');
                }
            }
        });
    }

    formatLargeNumbers();
});
