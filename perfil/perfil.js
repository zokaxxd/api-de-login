const token = localStorage.getItem('token')
fetch("http://127.0.0.1:8000/perfil", {
    headers: {
        "Authorization": "Bearer " + token
    }
})
.then(response => response.json())
.then(data => {
    document.getElementById("nome").innerText = data.seu_nome
    document.getElementById("idade").innerText = data.seu_idade
    document.getElementById("email").innerText = data.seu_email
    document.getElementById("id").innerText = data.seu_id
})