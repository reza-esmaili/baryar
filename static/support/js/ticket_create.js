document.addEventListener("DOMContentLoaded", function () {
    const departmentSelect = document.getElementById("id_department");
    const topicSelect = document.getElementById("id_topic");

    if (!departmentSelect || !topicSelect) return;

    departmentSelect.addEventListener("change", function () {
        const departmentId = this.value;

        if (!departmentId) {
            topicSelect.innerHTML = '<option value="">ابتدا واحد را انتخاب کنید</option>';
            topicSelect.disabled = true;
            return;
        }

        topicSelect.disabled = true;
        topicSelect.innerHTML = '<option value="">در حال بارگذاری...</option>';

        // استفاده از متغیر جهانی که در تمپلیت تعریف می‌شود
        const url = window.LOAD_TOPICS_URL || '/'; 

        fetch(`${url}?department_id=${departmentId}`)
            .then(response => response.json())
            .then(data => {
                topicSelect.innerHTML = '<option value="">انتخاب موضوع</option>';
                if (data.topics && data.topics.length > 0) {
                    data.topics.forEach(function (topic) {
                        const option = document.createElement("option");
                        option.value = topic.id;
                        option.textContent = topic.name;
                        topicSelect.appendChild(option);
                    });
                    topicSelect.disabled = false;
                } else {
                    topicSelect.innerHTML = '<option value="">موضوعی یافت نشد</option>';
                    topicSelect.disabled = true;
                }
            })
            .catch(error => {
                console.error("Error:", error);
                topicSelect.innerHTML = '<option value="">خطا در بارگذاری</option>';
            });
    });
});
