document.getElementById("btn-cad").addEventListener("click", function() {
    const name = document.getElementById("name").value;
    const age = document.getElementById("age").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    fetch("http://127.0.0.1:8000/users",{
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        name: name,
        idade: parseInt(age),
        email: email,
        password: password
    })
})
.then(response => response.json())
.then(data => {
    if (data.msg === "usuario criado") {
        alert("Conta criada com sucesso!")
        window.location.href = "/login/index.html"
    } else {
        alert("Erro: " + data.detail)
    }
})
})
