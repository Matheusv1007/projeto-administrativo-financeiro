const corpoParcelas = document.getElementById("parcelas");
const botaoAdicionarParcela = document.getElementById("adicionarParcela");

botaoAdicionarParcela.addEventListener("click", () => {
    const modelo = corpoParcelas.querySelector(".parcela");
    const nova = modelo.cloneNode(true);

    nova.querySelectorAll("input").forEach((campo) => {
        campo.value = "";
    });

    corpoParcelas.appendChild(nova);
});

corpoParcelas.addEventListener("click", (evento) => {
    const botao = evento.target.closest(".remover-parcela");

    if (!botao) {
        return;
    }

    // Um registro de contas sempre possui ao menos uma parcela.
    if (corpoParcelas.querySelectorAll(".parcela").length === 1) {
        botao.closest(".parcela").querySelectorAll("input").forEach((campo) => {
            campo.value = "";
        });
        return;
    }

    botao.closest(".parcela").remove();
});
