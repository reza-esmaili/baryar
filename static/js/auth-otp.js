(function () {
    "use strict";

    const OTP_SECONDS = 120;

    // توابع کمکی
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrfToken = getCookie("csrftoken");

    function toEnglishDigits(value) {
        if (!value) return "";
        const persian = "۰۱۲۳۴۵۶۷۸۹";
        const arabic = "٠١٢٣٤٥٦٧٨٩";
        return value.toString().replace(/[۰-۹٠-٩]/g, function (d) {
            let index = persian.indexOf(d);
            if (index > -1) return index;
            index = arabic.indexOf(d);
            if (index > -1) return index;
            return d;
        });
    }

    function normalizeMobile(mobile) {
        mobile = toEnglishDigits(mobile || "").trim();
        mobile = mobile.replace(/\s|-/g, "");
        if (mobile.startsWith("+98")) {
            mobile = "0" + mobile.substring(3);
        } else if (mobile.startsWith("0098")) {
            mobile = "0" + mobile.substring(4);
        } else if (mobile.startsWith("98") && mobile.length === 12) {
            mobile = "0" + mobile.substring(2);
        }
        return mobile;
    }

    function isValidMobile(mobile) {
        return /^09\d{9}$/.test(normalizeMobile(mobile));
    }

    async function postForm(url, data) {
        const formData = new FormData();
        Object.keys(data).forEach(function (key) {
            formData.append(key, data[key]);
        });
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken || "",
                "X-Requested-With": "XMLHttpRequest"
            },
            body: formData
        });
        let json;
        try {
            json = await response.json();
        } catch (e) {
            json = { ok: false, message: "پاسخ سرور معتبر نیست." };
        }
        if (!response.ok) throw json;
        return json;
    }

    function show(el) { if (el) el.classList.remove("hidden"); }
    function hide(el) { if (el) el.classList.add("hidden"); }
    function setMessage(el, message) {
        if (el) {
            el.textContent = message || "";
            show(el);
        }
    }

    function switchModal(from, to) {
        if (from) from.classList.remove("active");
        if (to) {
            setTimeout(function () { to.classList.add("active"); }, 120);
        }
    }

    function formatTime(seconds) {
        const m = String(Math.floor(seconds / 60)).padStart(2, "0");
        const s = String(seconds % 60).padStart(2, "0");
        return `${m}:${s}`;
    }

    function createTimer(timerEl, resendBtn) {
        let timerId = null;
        let remaining = OTP_SECONDS;
        function start() {
            stop();
            remaining = OTP_SECONDS;
            if (timerEl) timerEl.textContent = formatTime(remaining);
            if (resendBtn) resendBtn.disabled = true;
            timerId = setInterval(function () {
                remaining -= 1;
                if (timerEl) timerEl.textContent = formatTime(Math.max(remaining, 0));
                if (remaining <= 0) {
                    stop();
                    if (timerEl) timerEl.textContent = "زمان کد به پایان رسید";
                    if (resendBtn) resendBtn.disabled = false;
                }
            }, 1000);
        }
        function stop() {
            if (timerId) {
                clearInterval(timerId);
                timerId = null;
            }
        }
        return { start, stop };
    }

    
    //
    function setupOtpInputs(container) {
        if (!container) return;

        if (container.dataset.otpReady === "1") {
            return;
        }

        container.dataset.otpReady = "1";

        const inputs = Array.from(container.querySelectorAll("input"));
        const targetId = container.dataset.target;
        const targetInput = document.getElementById(targetId);

        // پیدا کردن این بخش در متد setupOtpInputs
        function syncValue() {
            // اطمینان از اینکه باکس‌ها به ترتیب درست (ایندکس 0 تا 5) جمع می‌شوند
            const code = inputs.map(input => input.value).join("");
            if (targetInput) targetInput.value = code;
            console.log("Debug Code:", code); // این لاگ را بگذار تا در Console مرورگر ببینی چه کدی ارسال می‌شود
        }


        inputs.forEach(function (input, index) {
            input.addEventListener("input", function (e) {
                let value = toEnglishDigits(e.target.value).replace(/\D/g, "");

                if (value.length > 1) {
                    const chars = value.slice(0, inputs.length).split("");
                    chars.forEach((char, i) => {
                        if (inputs[i]) inputs[i].value = char;
                    });

                    const nextIndex = Math.min(chars.length, inputs.length - 1);
                    inputs[nextIndex].focus();
                    syncValue();
                    return;
                }

                e.target.value = value;

                if (value && inputs[index + 1]) {
                    inputs[index + 1].focus();
                }

                syncValue();
            });

            input.addEventListener("keydown", function (e) {
                if (e.key === "Backspace" && !input.value && inputs[index - 1]) {
                    inputs[index - 1].focus();
                }
            });

            input.addEventListener("paste", function (e) {
                e.preventDefault();

                const pasted = toEnglishDigits(
                    (e.clipboardData || window.clipboardData).getData("text")
                ).replace(/\D/g, "");

                if (!pasted) return;

                const chars = pasted.slice(0, inputs.length).split("");

                chars.forEach((char, i) => {
                    if (inputs[i]) inputs[i].value = char;
                });

                const lastIndex = Math.min(chars.length - 1, inputs.length - 1);
                inputs[lastIndex].focus();
                syncValue();
            });
        });

        return {
            focus: function () {
                if (inputs[0]) inputs[0].focus();
            },
            clear: function () {
                inputs.forEach(input => input.value = "");
                syncValue();

                if (inputs[0]) {
                    inputs[0].focus();
                }
            },
            value: function () {
                syncValue();
                return targetInput ? targetInput.value : "";
            }
        };
    }


    // مدیریت ورود
    const loginMainModal = document.getElementById("loginMainModal");

    const loginOtpModal = document.getElementById("loginOtpModal");
    const loginOtpRequestBtn = document.getElementById("loginOtpRequestBtn");
    const loginBackBtn = document.getElementById("loginBackBtn");
    const loginOtpVerifyForm = document.getElementById("loginOtpVerifyForm");
    const loginResendBtn = document.getElementById("loginResendBtn");
    const loginTimerEl = document.getElementById("loginTimer");
    const loginOtpError = document.getElementById("loginOtpError");
    const loginOtpInfo = document.getElementById("loginOtpInfo");
    const loginOtpMobileInput = document.getElementById("loginOtpMobile");
    const loginOtpMobileText = document.getElementById("loginOtpMobileText");

    const loginOtpInputsController = setupOtpInputs(document.querySelector("#loginOtpModal .otp-inputs"));
    const loginTimer = createTimer(loginTimerEl, loginResendBtn);

    async function requestLoginOtp() {
        const mobileInput = document.querySelector("#passwordLoginForm input[name='mobile']") || document.querySelector("#passwordLoginForm input[id$='mobile']");
        const mobile = normalizeMobile(mobileInput ? mobileInput.value : "");
        if (!isValidMobile(mobile)) { alert("شماره موبایل معتبر نیست."); return; }
        
        hide(loginOtpError);
        hide(loginOtpInfo);
        loginOtpRequestBtn.disabled = true;
        loginOtpRequestBtn.textContent = "در حال ارسال...";
        try {
            const result = await postForm(window.AUTH_URLS.loginRequestOtp, { mobile: mobile });
            if (loginOtpMobileInput) loginOtpMobileInput.value = mobile;
            if (loginOtpMobileText) loginOtpMobileText.textContent = mobile;
            setMessage(loginOtpInfo, result.message || "کد تایید ارسال شد.");
            switchModal(loginMainModal, loginOtpModal);
            loginTimer.start();
            setTimeout(() => { if (loginOtpInputsController) loginOtpInputsController.clear(); }, 350);
        } catch (err) { alert(err.message || "خطا در ارسال کد."); }
        finally { loginOtpRequestBtn.disabled = false; loginOtpRequestBtn.textContent = "ورود با کد یکبارمصرف"; }
    }

    if (loginOtpRequestBtn) loginOtpRequestBtn.addEventListener("click", requestLoginOtp);
    if (loginBackBtn) loginBackBtn.addEventListener("click", () => { switchModal(loginOtpModal, loginMainModal); loginTimer.stop(); });
    if (loginResendBtn) loginResendBtn.addEventListener("click", requestLoginOtp);
    if (loginOtpVerifyForm) {
        loginOtpVerifyForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            hide(loginOtpError);
            const mobile = loginOtpMobileInput ? loginOtpMobileInput.value : "";
            const code = loginOtpInputsController ? loginOtpInputsController.value() : "";
            if (!/^\d{6}$/.test(code)) { setMessage(loginOtpError, "کد ۶ رقمی را وارد کنید."); return; }
            const submitBtn = loginOtpVerifyForm.querySelector("button[type='submit']");
            submitBtn.disabled = true;
            submitBtn.textContent = "در حال بررسی...";
            try {
                const result = await postForm(window.AUTH_URLS.loginVerifyOtp, { mobile: mobile, code: code });
                window.location.href = result.redirect_url || "/";
            } catch (err) { setMessage(loginOtpError, err.message || "کد اشتباه است."); if (loginOtpInputsController) loginOtpInputsController.clear(); }
            finally { submitBtn.disabled = false; submitBtn.textContent = "تایید و ورود"; }
        });
    }

    // مدیریت ثبت‌نام
    const registerMainModal = document.getElementById("registerMainModal");
    const registerOtpModal = document.getElementById("registerOtpModal");
    const registerRequestForm = document.getElementById("registerRequestForm");
    const registerOtpVerifyForm = document.getElementById("registerOtpVerifyForm");
    const registerBackBtn = document.getElementById("registerBackBtn");
    const registerCancelBtn = document.getElementById("registerCancelBtn");
    const registerResendBtn = document.getElementById("registerResendBtn");
    const registerTimerEl = document.getElementById("registerTimer");
    const registerError = document.getElementById("registerError");
    const registerOtpError = document.getElementById("registerOtpError");
    const registerOtpInfo = document.getElementById("registerOtpInfo");
    const registerOtpMobileText = document.getElementById("registerOtpMobileText");

    const registerOtpInputsController = setupOtpInputs(document.querySelector("#registerOtpModal .otp-inputs"));
    const registerTimer = createTimer(registerTimerEl, registerResendBtn);

    function getRegisterFormData() {
        const data = {};
        new FormData(registerRequestForm).forEach((v, k) => { data[k] = v; });
        if (data.mobile) data.mobile = normalizeMobile(data.mobile);
        return data;
    }

    async function requestRegisterOtp() {
        const data = getRegisterFormData();
        hide(registerError); hide(registerOtpError); hide(registerOtpInfo);
        if (!data.mobile || !isValidMobile(data.mobile)) { setMessage(registerError, "شماره موبایل معتبر نیست."); return; }
        const submitBtn = registerRequestForm.querySelector("button[type='submit']");
        submitBtn.disabled = true;
        submitBtn.textContent = "در حال ارسال...";
        try {
            const result = await postForm(window.AUTH_URLS.registerRequestOtp, data);
            if (registerOtpMobileText) registerOtpMobileText.textContent = data.mobile;
            setMessage(registerOtpInfo, result.message || "کد تایید ارسال شد.");
            switchModal(registerMainModal, registerOtpModal);
            registerTimer.start();
            setTimeout(() => { if (registerOtpInputsController) registerOtpInputsController.clear(); }, 350);
        } catch (err) { setMessage(registerError, err.message || "خطا در ارسال کد."); }
        finally { submitBtn.disabled = false; submitBtn.textContent = "ثبت اطلاعات و دریافت کد تایید"; }
    }

    if (registerRequestForm) registerRequestForm.addEventListener("submit", (e) => { e.preventDefault(); requestRegisterOtp(); });
    if (registerBackBtn) registerBackBtn.addEventListener("click", () => { switchModal(registerOtpModal, registerMainModal); registerTimer.stop(); });
    if (registerResendBtn) registerResendBtn.addEventListener("click", requestRegisterOtp);
    if (registerCancelBtn) registerCancelBtn.addEventListener("click", async () => {
        try { if (window.AUTH_URLS.registerCancel) await postForm(window.AUTH_URLS.registerCancel, {}); } catch(e) {}
        switchModal(registerOtpModal, registerMainModal); registerTimer.stop();
        if (registerOtpInputsController) registerOtpInputsController.clear();
    });
    if (registerOtpVerifyForm) {
        registerOtpVerifyForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            hide(registerOtpError);
            const code = registerOtpInputsController ? registerOtpInputsController.value() : "";
            if (!/^\d{6}$/.test(code)) { setMessage(registerOtpError, "کد ۶ رقمی را وارد کنید."); return; }
            const submitBtn = registerOtpVerifyForm.querySelector("button[type='submit']");
            submitBtn.disabled = true;
            submitBtn.textContent = "در حال تایید...";
            try {
                const result = await postForm(window.AUTH_URLS.registerVerifyOtp, { code: code });
                window.location.href = result.redirect_url || "/";
            } catch (err) { setMessage(registerOtpError, err.message || "کد اشتباه است."); if (registerOtpInputsController) registerOtpInputsController.clear(); }
            finally { submitBtn.disabled = false; submitBtn.textContent = "تایید و تکمیل ثبت‌نام"; }
        });
    }
})();
