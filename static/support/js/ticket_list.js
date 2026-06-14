document.addEventListener("DOMContentLoaded", function () {

const department = document.getElementById("departmentFilter")
const dateFrom = document.getElementById("dateFrom")
const dateTo = document.getElementById("dateTo")
const search = document.getElementById("searchInput")
const clearBtn = document.getElementById("clearFilters")
const table = document.getElementById("ticketsTable")

let timer = null

function loadTickets(){

const params = new URLSearchParams()

if(department.value)
params.append("department",department.value)

if(dateFrom.value)
params.append("date_from",dateFrom.value)

if(dateTo.value)
params.append("date_to",dateTo.value)

if(search.value)
params.append("q",search.value)

fetch(window.location.pathname+"?"+params.toString(),{
headers:{
"X-Requested-With":"XMLHttpRequest"
}
})
.then(r=>r.json())
.then(data=>{
table.innerHTML=data.html
})

}

department.addEventListener("change",loadTickets)
dateFrom.addEventListener("change",loadTickets)
dateTo.addEventListener("change",loadTickets)

search.addEventListener("keyup",function(){

clearTimeout(timer)

timer=setTimeout(loadTickets,400)

})

clearBtn.addEventListener("click",function(){

department.value=""
dateFrom.value=""
dateTo.value=""
search.value=""

loadTickets()

})

})
