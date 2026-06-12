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
});