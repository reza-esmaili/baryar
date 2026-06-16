(function ($) {
    $(document).ready(function () {

        const province = $("#id_origin_province");
        const city = $("#id_origin_city");

        const country = $("#id_destination_country");
        const destCity = $("#id_destination_city");
        const port = $("#id_destination_port");

        function resetSelect($select) {
            $select.empty();
            $select.append('<option value="">---------</option>');
            $select.val("");
            $select.trigger("change");
        }

        province.on("change", function () {
            const provinceId = $(this).val();

            resetSelect(city);

            if (!provinceId) {
                return;
            }

            $.ajax({
                url: "/documents/ajax/origin-cities/",
                data: {
                    province_id: provinceId
                },
                success: function (data) {
                    data.forEach(function (item) {
                        city.append(
                            $("<option>", {
                                value: item.id,
                                text: item.name
                            })
                        );
                    });
                },
                error: function (xhr) {
                    console.error("origin cities ajax error:", xhr.status, xhr.responseText);
                }
            });
        });

        country.on("change", function () {
            const countryId = $(this).val();

            resetSelect(destCity);
            resetSelect(port);

            if (!countryId) {
                return;
            }

            $.ajax({
                url: "/documents/ajax/destination-cities/",
                data: {
                    country_id: countryId
                },
                success: function (data) {
                    data.forEach(function (item) {
                        destCity.append(
                            $("<option>", {
                                value: item.id,
                                text: item.name
                            })
                        );
                    });
                },
                error: function (xhr) {
                    console.error("destination cities ajax error:", xhr.status, xhr.responseText);
                }
            });
        });

        destCity.on("change", function () {
            const cityId = $(this).val();

            resetSelect(port);

            if (!cityId) {
                return;
            }

            $.ajax({
                url: "/documents/ajax/destination-ports/",
                data: {
                    city_id: cityId
                },
                success: function (data) {
                    data.forEach(function (item) {
                        port.append(
                            $("<option>", {
                                value: item.id,
                                text: item.name
                            })
                        );
                    });
                },
                error: function (xhr) {
                    console.error("destination ports ajax error:", xhr.status, xhr.responseText);
                }
            });
        });

    });
})(django.jQuery);
