document.addEventListener("DOMContentLoaded", function () {
    const levelField = document.getElementById("id_requirement_level");

    if (!levelField) {
        console.warn("DocumentRule dynamic: #id_requirement_level not found");
        return;
    }

    function getRow(fieldName) {
        return document.querySelector(".field-" + fieldName);
    }

    function getInput(fieldName) {
        return document.getElementById("id_" + fieldName);
    }

    const allFields = [
        "shipping_procedure",
        "transport_mode",
        "origin_province",
        "origin_city",
        "destination_country",
        "destination_city",
        "destination_port",
        "cargo_type",
        "cargo_subcategory"
    ];

    const fieldMap = {};

    allFields.forEach(function (fieldName) {
        fieldMap[fieldName] = {
            row: getRow(fieldName),
            input: getInput(fieldName)
        };
    });

    const allowedByLevel = {
        general: [],

        shipping_procedure: [
            "shipping_procedure"
        ],

        transport_mode: [
            "transport_mode"
        ],

        origin: [
            "origin_province",
            "origin_city"
        ],

        destination: [
            "destination_country",
            "destination_city",
            "destination_port"
        ],

        cargo_type: [
            "cargo_type"
        ],

        cargo_subcategory: [
            "cargo_type",
            "cargo_subcategory"
        ],

        custom: [
            "shipping_procedure",
            "transport_mode",
            "origin_province",
            "origin_city",
            "destination_country",
            "destination_city",
            "destination_port",
            "cargo_type",
            "cargo_subcategory"
        ]
    };

    function clearField(fieldName) {
        const item = fieldMap[fieldName];

        if (!item || !item.input) {
            return;
        }

        const input = item.input;

        if (input.tagName === "SELECT") {
            input.value = "";

            // برای فیلدهای عادی و بعضی وابستگی‌ها
            input.dispatchEvent(new Event("change", { bubbles: true }));

            // برای select2/autocomplete جنگو
            if (window.django && django.jQuery) {
                django.jQuery(input).val("").trigger("change");
            }
        } else if (input.type === "checkbox") {
            input.checked = false;
            input.dispatchEvent(new Event("change", { bubbles: true }));
        } else {
            input.value = "";
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
        }
    }

    function hideField(fieldName, shouldClear) {
        const item = fieldMap[fieldName];

        if (item && item.row) {
            item.row.style.display = "none";
        }

        if (shouldClear) {
            clearField(fieldName);
        }
    }

    function showField(fieldName) {
        const item = fieldMap[fieldName];

        if (item && item.row) {
            item.row.style.display = "";
        }
    }

    function toggleFields() {
        const level = levelField.value;
        const allowedFields = allowedByLevel[level] || [];

        allFields.forEach(function (fieldName) {
            if (allowedFields.includes(fieldName)) {
                showField(fieldName);
            } else {
                hideField(fieldName, true);
            }
        });
    }

    toggleFields();

    levelField.addEventListener("change", toggleFields);
});
