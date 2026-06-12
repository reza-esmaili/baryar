// static/admin/js/rate_form.js
(function($) {
    $(document).ready(function() {
        
        // --- مدیریت مبدا ---
        $("#id_origin_province").change(function() {
            const url = "/rates/ajax/load-cities/";
            const provinceId = $(this).val();

            $.ajax({
                url: url,
                data: {
                    'province_id': provinceId
                },
                success: function(data) {
                    let options = '<option value="">---------</option>';
                    data.forEach(function(city) {
                        options += `<option value="${city.id}">${city.name}</option>`;
                    });
                    $("#id_origin_city").html(options);
                }
            });
        });

        // --- مدیریت مقصد ---
        $("#id_destination_country").change(function() {
            const url = "/rates/ajax/load-destination-cities/";
            const countryId = $(this).val();

            // خالی کردن شهر و پورت مقصد
            $("#id_destination_city").html('<option value="">---------</option>');
            $("#id_destination_port").html('<option value="">---------</option>');

            $.ajax({
                url: url,
                data: {
                    'country_id': countryId
                },
                success: function(data) {
                    let options = '<option value="">---------</option>';
                    data.forEach(function(city) {
                        options += `<option value="${city.id}">${city.name}</option>`;
                    });
                    $("#id_destination_city").html(options);
                }
            });
        });

        // --- مدیریت پورت‌ها بر اساس شهر مقصد و روش حمل ---
        function updatePorts() {
            const url = "/rates/ajax/load-ports/";
            const cityId = $("#id_destination_city").val();
            const transportMode = $("#id_transport_mode").val();

            if (!cityId || !transportMode) {
                $("#id_destination_port").html('<option value="">---------</option>');
                return;
            }

            $.ajax({
                url: url,
                data: {
                    'city_id': cityId,
                    'transport_mode': transportMode
                },
                success: function(data) {
                    let options = '<option value="">---------</option>';
                    data.forEach(function(port) {
                        options += `<option value="${port.id}">${port.name}</option>`;
                    });
                    $("#id_destination_port").html(options);
                }
            });
        }
        
        // این تابع هم در زمان تغییر شهر و هم در زمان تغییر روش حمل باید فراخوانی شود
        $("#id_destination_city").change(updatePorts);
        $("#id_transport_mode").change(updatePorts);

    });
})(django.jQuery);
