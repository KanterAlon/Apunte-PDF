document.getElementById('apunteForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const formData = new FormData(this);
    const res = await fetch('/process', {
        method: 'POST',
        body: formData
    });

    const data = await res.json();
    document.getElementById('resultado').textContent = data.apunte;
});

function copiarTexto() {
    const texto = document.getElementById('resultado').textContent;
    navigator.clipboard.writeText(texto)
        .then(() => alert("¡Texto copiado al portapapeles!"))
        .catch(err => alert("Error al copiar: " + err));
}
