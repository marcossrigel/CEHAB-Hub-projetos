import tkinter as tk
from tkinter import messagebox


class HubRobosApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Painel Central de Robôs")
        self.root.geometry("1280x800")
        self.root.minsize(1100, 700)
        self.root.configure(bg="#f3f6fb")

        self.label_status = None
        self._montar_interface()

    def _montar_interface(self) -> None:
        frame_principal = tk.Frame(self.root, bg="#f3f6fb")
        frame_principal.pack(fill="both", expand=True, padx=24, pady=24)

        self._criar_topo(frame_principal)
        self._criar_painel(frame_principal)
        self._criar_rodape(frame_principal)

    def _criar_topo(self, parent: tk.Frame) -> None:
        topo = tk.Frame(parent, bg="#f3f6fb")
        topo.pack(fill="x", pady=(0, 18))

        tk.Label(
            topo,
            text="Painel Central de Robôs",
            font=("Segoe UI", 24, "bold"),
            bg="#f3f6fb",
            fg="#0f172a",
        ).pack(anchor="w")

        tk.Label(
            topo,
            text="Gerenciamento centralizado e completo de aplicações e automações.",
            font=("Segoe UI", 11),
            bg="#f3f6fb",
            fg="#475569",
        ).pack(anchor="w", pady=(6, 0))

        barra_info = tk.Frame(topo, bg="#ffffff", bd=1, relief="solid", padx=14, pady=10)
        barra_info.pack(fill="x", pady=(16, 0))

        tk.Label(
            barra_info,
            text="Hub principal",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff",
            fg="#111827",
        ).pack(side="left")

        tk.Label(
            barra_info,
            text="6 módulos disponíveis",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#64748b",
        ).pack(side="right")

    def _criar_painel(self, parent: tk.Frame) -> None:
        painel = tk.Frame(parent, bg="#f3f6fb")
        painel.pack(fill="both", expand=True)

        container = tk.Frame(painel, bg="#f3f6fb")
        container.pack(pady=40)

        grid = tk.Frame(container, bg="#f3f6fb")
        grid.pack()

        modulos = [
            ("Robo de Destaques", "Acompanhar e executar rotinas de destaques."),
            ("Robo de Pendencias (SEFAZ/SEPLAG)", "Monitoramento e tratamento de pendências."),
            ("Robo de Seis Parados", "Controle e verificação de SEIs sem andamento."),
            ("Gerador de OBS", "Geração e organização das observações do processo."),
            ("Robo Solicitação de Pagamento", "Fluxo automatizado de solicitações de pagamento."),
            ("Solicitação de Pagamentos BM 2026", "Acompanhamento específico dos pagamentos BM 2026."),
        ]

        for indice, (titulo, descricao) in enumerate(modulos):
            linha = indice // 3
            coluna = indice % 3
            card = self._criar_card(grid, titulo, descricao)
            card.grid(row=linha, column=coluna, padx=14, pady=14)

    def _criar_card(self, parent: tk.Frame, titulo: str, descricao: str) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg="#ffffff",
            bd=1,
            relief="solid",
            width=250,
            height=250,
            cursor="arrow",
            highlightthickness=1,
            highlightbackground="#dbe3f0",
            highlightcolor="#dbe3f0",
        )
        card.pack_propagate(False)

        topo_card = tk.Frame(card, bg="#ffffff")
        topo_card.pack(fill="x", padx=18, pady=(18, 10))

        indicador = tk.Canvas(
            topo_card,
            width=12,
            height=12,
            bg="#ffffff",
            highlightthickness=0,
        )
        indicador.create_oval(2, 2, 10, 10, fill="#2563eb", outline="#2563eb")
        indicador.pack(side="left")

        tk.Label(
            topo_card,
            text="Módulo",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#2563eb",
        ).pack(side="left", padx=(8, 0))

        corpo = tk.Frame(card, bg="#ffffff")
        corpo.pack(fill="both", expand=True, padx=18)

        lbl_titulo = tk.Label(
            corpo,
            text=titulo,
            font=("Segoe UI", 13, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            justify="left",
            wraplength=260,
            anchor="w",
        )
        lbl_titulo.pack(anchor="w")

        lbl_descricao = tk.Label(
            corpo,
            text=descricao,
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#64748b",
            justify="left",
            wraplength=260,
            anchor="w",
        )
        lbl_descricao.pack(anchor="w", pady=(10, 0))
        tk.Frame(corpo, bg="#ffffff").pack(expand=True)

        botao = tk.Button(
            card,
            text="Abrir módulo",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda nome=titulo: self._abrir_modulo(nome),
        )
        botao.pack(side="bottom", anchor="w", padx=18, pady=(0, 18), ipadx=12, ipady=8)

        botao.bind("<Enter>", lambda e, b=botao: b.configure(bg="#1d4ed8"))
        botao.bind("<Leave>", lambda e, b=botao: b.configure(bg="#2563eb"))

        return card

    def _criar_rodape(self, parent: tk.Frame) -> None:
        rodape = tk.Frame(parent, bg="#f3f6fb")
        rodape.pack(fill="x", pady=(18, 0))

        status_box = tk.Frame(rodape, bg="#ffffff", bd=1, relief="solid", padx=14, pady=10)
        status_box.pack(fill="x")

        self.label_status = tk.Label(
            status_box,
            text="Status: painel carregado com sucesso.",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#334155",
            anchor="w",
        )
        self.label_status.pack(fill="x")

    def _hover_card(self, card: tk.Frame, botao: tk.Button, ativo: bool) -> None:
        if ativo:
            card.configure(
                bg="#ffffff",
                highlightbackground="#2563eb",
                highlightcolor="#2563eb",
            )
            botao.configure(bg="#1d4ed8")
        else:
            card.configure(
                bg="#ffffff",
                highlightbackground="#dbe3f0",
                highlightcolor="#dbe3f0",
            )
            botao.configure(bg="#2563eb")

    def _abrir_modulo(self, nome: str) -> None:
        self.label_status.config(text=f"Status: módulo selecionado -> {nome}")
        messagebox.showinfo("Módulo", f"O módulo '{nome}' será conectado na próxima etapa.")


def main() -> None:
    root = tk.Tk()
    HubRobosApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
