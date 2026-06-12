document.addEventListener("DOMContentLoaded", function() {
    // ۱. فعال‌سازی تقویم شمسی روی فیلدهای تاریخ
    if (typeof $('.p-date').persianDatepicker === 'function') {
        $('.p-date').persianDatepicker({
            initialValue: false,
            format: 'YYYY/MM/DD',
            autoClose: true
        });
    }

    // ۲. تنظیمات و مقداردهی اولیه نمودار (ApexCharts)
    var options = {
        series: [{
            name: 'مبلغ فروش',
            data: []
        }],
        chart: {
            type: 'area', // نمودار خطی با پس‌زمینه رنگی
            height: 400,
            fontFamily: 'Vazirmatn, sans-serif',
            toolbar: { show: true }
        },
        colors: ['#4318ff'],
        fill: {
            type: 'gradient',
            gradient: {
                shadeIntensity: 1,
                opacityFrom: 0.4,
                opacityTo: 0.05,
                stops: [0, 90, 100]
            }
        },
        dataLabels: { enabled: false },
        stroke: {
            curve: 'smooth',
            width: 3
        },
        xaxis: {
            categories: [],
            labels: {
                style: { colors: '#718096' }
            }
        },
        yaxis: {
            labels: {
                // فرمت کردن اعداد محور Y به صورت ریال
                formatter: function (value) {
                    if (value === undefined || value === null) return 0;
                    return value.toLocaleString('fa-IR') + ' ریال';
                },
                style: { colors: '#718096' }
            }
        },
        tooltip: {
            y: {
                formatter: function (value) {
                    return value.toLocaleString('fa-IR') + ' ریال';
                }
            }
        }
    };

    var chart = new ApexCharts(document.querySelector("#salesChart"), options);
    chart.render();

    // ۳. تابع دریافت داده‌ها از بک‌اند (با استفاده از AJAX/Fetch API)
    function fetchChartData() {
        var startDate = document.getElementById('startDate').value;
        var endDate = document.getElementById('endDate').value;
        var interval = document.getElementById('interval').value;
        
        // خواندن آدرس URL از اتریبیوت data-url در HTML
        var urlPath = document.getElementById('salesChart').getAttribute('data-url');
        
        // ساخت URL نهایی به همراه پارامترها (Query Strings)
        var fetchUrl = new URL(urlPath, window.location.origin);
        if (startDate) fetchUrl.searchParams.append('start_date', startDate);
        if (endDate) fetchUrl.searchParams.append('end_date', endDate);
        if (interval) fetchUrl.searchParams.append('interval', interval);

        // درخواست به بک‌اند
        fetch(fetchUrl)
            .then(response => response.json())
            .then(data => {
                // به‌روزرسانی نمودار با داده‌های دریافتی
                chart.updateSeries([{
                    name: 'مبلغ فروش',
                    data: data.amounts || []
                }]);
                
                chart.updateOptions({
                    xaxis: {
                        categories: data.dates || []
                    }
                });
            })
            .catch(error => {
                console.error('خطا در دریافت اطلاعات نمودار:', error);
            });
    }

    // ۴. اتصال تابع دریافت داده به دکمه "اعمال فیلتر"
    document.getElementById('applyFilterBtn').addEventListener('click', fetchChartData);

    // ۵. فراخوانی اولیه برای نمایش نمودار هنگام لود صفحه
    fetchChartData();
});
