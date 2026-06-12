document.addEventListener("DOMContentLoaded", function () {

    const cards = document.querySelectorAll(".profile-card");

    cards.forEach((card, index) => {

        card.style.opacity = "0";
        card.style.transform = "translateY(15px)";

        setTimeout(() => {

            card.style.transition =
                "all .4s ease";

            card.style.opacity = "1";
            card.style.transform =
                "translateY(0)";

        }, index * 100);

    });

});

document.addEventListener("DOMContentLoaded", function(){

    const deleteButtons = document.querySelectorAll(".delete-document");

    deleteButtons.forEach(btn => {

        btn.addEventListener("click", function(e){

            if(!confirm("از حذف این مدرک اطمینان دارید؟")){
                e.preventDefault();
            }

        });

    });

});