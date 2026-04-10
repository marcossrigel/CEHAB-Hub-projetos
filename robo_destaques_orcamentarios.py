# Robo da planilha -> Controle - Destaques Orcamentarios
# Acompanhamento de destaques 2026

from seleniumbase import SB
import os
import re
import time
import json
import csv
from datetime import datetime
import sys
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

import gspread
from mensagens_whatsapp import enviar_mensagem_gop
from oauth2client.service_account import ServiceAccountCredentials

SHEET_ID = "18TBjduqkPUF0UxpCJw7Ttz9aVHpPO5taz7uWox7uYyk"
GID = "2091813233"
COLUNA_SEI = "SEI"
COLUNA_OBJETO = "OBJETO"

SEI_CHROME_PROFILE = r"C:\temp\chrome_profile_sei"
CRED_JSON = "credenciais_sheets.json"

SEI_LOGIN_URL = "https://sei.pe.gov.br/sip/login.php?sigla_orgao_sistema=GOVPE&sigla_sistema=SEI"

XP_USUARIO = '//*[@id="txtUsuario"]'
XP_SENHA = '//*[@id="pwdSenha"]'
CSS_SELECT_ORGAO = '#selOrgao'
CSS_BTN_ACESSAR = "#sbmAcessar"
XP_TXT_PESQUISA_RAPIDA = '//*[@id="txtPesquisaRapida"]'
XP_BTN_LUPA = '//*[@id="spnInfraUnidade"]/img'

ROMAN_RE = re.compile(r"^(?=[IVXLCDM]+$)M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")
SEI_RE = re.compile(r"\b\d{10}\.\d{6}/\d{4}-\d{2}\b")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVOS_JSON_DIR = os.path.join(BASE_DIR, "arquivos_json")
OUT_DIR = os.path.join(BASE_DIR, "downloaded_files")

CRED_JSON = os.path.join(ARQUIVOS_JSON_DIR, "credenciais_sheets.json")
MAP_JSON = os.path.join(ARQUIVOS_JSON_DIR, "sei_last_docs_destaques_orcamentarios.json")

def load_map() -> dict:
    print("📥 Lendo MAP em:", MAP_JSON)
    if not os.path.exists(MAP_JSON):
        return {}
    try:
        with open(MAP_JSON, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as e:
        print("⚠️ Erro ao ler MAP:", repr(e))
        return {}

def save_map(data: dict) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    print("💾 Salvando MAP em:", MAP_JSON)
    with open(MAP_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

ESPERA_CARREGAR_WHATSAPP = 12

def now_ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_visible_files_in_tree(sb: SB) -> list[tuple[str, str]]:
    icons = sb.find_elements("css selector", 'img[id^="icon"]')
    items = []

    for ic in icons:
        try:
            if not ic.is_displayed():
                continue

            icon_id = (ic.get_attribute("id") or "").strip()
            if not icon_id.startswith("icon"):
                continue

            num = icon_id.replace("icon", "").strip()
            if not num.isdigit():
                continue

            span_id = f"span{num}"
            sp = sb.find_element("css selector", f"span#{span_id}")
            if not sp.is_displayed():
                continue

            txt = (sp.text or "").strip()
            if not txt:
                continue

            items.append((num, txt))
        except Exception:
            continue

    if not items:
        raise RuntimeError("Não achei arquivos visíveis (img#icon... + span#span...).")

    return items


def safe_name(s: str) -> str:
    s = (s or "").strip()
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)[:120]


def save_results_csv(rows: list[dict], csv_path: str) -> None:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    fieldnames = ["sei", "objeto", "ultimo_doc", "mudou", "qtd_novos", "screenshot"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def pick_sei_value(cell: str) -> str:
    text = (cell or "").strip()
    if not text:
        return ""
    matches = SEI_RE.findall(text)
    if matches:
        return matches[-1]
    return text

def fetch_seis_from_sheet_api() -> list[dict]:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_JSON, scope)
    client = gspread.authorize(creds)

    sh = client.open_by_key(SHEET_ID)
    ws = sh.get_worksheet_by_id(int(GID))

    rows = ws.get_all_records()

    itens = []
    seen = set()

    for r in rows:
        raw_sei = str(r.get(COLUNA_SEI, "")).strip()
        sei = pick_sei_value(raw_sei)
        objeto = str(r.get(COLUNA_OBJETO, "")).strip()

        if not sei:
            continue

        if sei in seen:
            continue

        itens.append({
            "sei": sei,
            "objeto": objeto,
        })
        seen.add(sei)

    return itens


def is_roman(s: str) -> bool:
    s = (s or "").strip().upper()
    return bool(s) and bool(ROMAN_RE.match(s))


def sei_quick_search(sb: SB, sei: str) -> None:
    sb.wait_for_element_visible(XP_TXT_PESQUISA_RAPIDA, timeout=40)
    sb.click(XP_TXT_PESQUISA_RAPIDA)
    sb.clear(XP_TXT_PESQUISA_RAPIDA)
    sb.type(XP_TXT_PESQUISA_RAPIDA, sei)
    sb.click(XP_BTN_LUPA)
    sb.sleep(2.2)


def find_tree_frame(sb: SB, timeout: int = 60) -> str:
    end = time.time() + timeout
    last_err = None

    while time.time() < end:
        try:
            sb.switch_to_default_content()
            frames = sb.find_elements("css selector", "iframe")
        except Exception as e:
            last_err = e
            time.sleep(0.5)
            continue

        for fr in frames:
            name = (fr.get_attribute("name") or "").strip()
            fid = (fr.get_attribute("id") or "").strip()
            key = name or fid
            if not key:
                continue
            try:
                sb.switch_to_default_content()
                sb.switch_to_frame(key)

                spans = sb.find_elements("css selector", 'span[id^="span"]')
                for sp in spans[:120]:
                    txt = (sp.text or "").strip()
                    if is_roman(txt):
                        sb.switch_to_default_content()
                        return key
            except Exception as e:
                last_err = e
                continue

        time.sleep(0.6)

    sb.switch_to_default_content()
    raise RuntimeError(f"Não consegui localizar o iframe da árvore automaticamente. Último erro: {last_err}")


def expand_last_roman_folder(sb: SB) -> None:
    spans = sb.find_elements("css selector", 'span[id^="span"]')
    romans = []
    for sp in spans:
        try:
            if not sp.is_displayed():
                continue
            txt = (sp.text or "").strip()
            if is_roman(txt):
                romans.append((txt, sp))
        except Exception:
            continue

    if not romans:
        raise RuntimeError("Não achei nenhuma pasta romana na árvore.")

    _, last_sp = romans[-1]
    sb.execute_script("arguments[0].scrollIntoView({block:'center'});", last_sp)
    sb.sleep(0.15)

    parent = last_sp.find_element("xpath", "./..")
    imgs = parent.find_elements("css selector", "img")
    for img in imgs:
        try:
            src = (img.get_attribute("src") or "").lower()
            if "plus" in src or "expand" in src:
                img.click()
                sb.sleep(0.6)
                return
        except Exception:
            pass


def get_last_file_in_tree(sb: SB) -> tuple[str, str]:
    icons = sb.find_elements("css selector", 'img[id^="icon"]')
    items = []

    for ic in icons:
        try:
            if not ic.is_displayed():
                continue

            icon_id = (ic.get_attribute("id") or "").strip()
            if not icon_id.startswith("icon"):
                continue

            num = icon_id.replace("icon", "").strip()
            if not num.isdigit():
                continue

            span_id = f"span{num}"
            sp = sb.find_element("css selector", f"span#{span_id}")
            if not sp.is_displayed():
                continue

            txt = (sp.text or "").strip()
            if not txt:
                continue

            items.append((num, txt))
        except Exception:
            continue

    if not items:
        raise RuntimeError("Não achei arquivos visíveis (img#icon... + span#span...).")

    return items[-1]


def click_papel_azul_do_item(sb: SB, num: str) -> None:
    xp_icon = f'//*[@id="icon{num}"]'
    sb.wait_for_element_visible(xp_icon, timeout=15)
    sb.scroll_to(xp_icon)
    try:
        sb.js_click(xp_icon)
    except Exception:
        sb.click(xp_icon)
    sb.sleep(0.12)


def open_last_doc(sb: SB, num: str) -> None:
    xp_span = f'//*[@id="span{num}"]'
    sb.wait_for_element_visible(xp_span, timeout=15)
    sb.scroll_to(xp_span)
    try:
        sb.js_click(xp_span)
    except Exception:
        sb.click(xp_span)


def save_screenshot(sb: SB, folder: str, prefix: str) -> str:
    os.makedirs(folder, exist_ok=True)
    filename = f"{prefix}_{now_ts()}.png"
    path = os.path.join(folder, filename)
    sb.save_screenshot(path)
    return path

class FloatingConsole:
    def __init__(self):
        self.root = None
        self.text = None
        self.ready = False

    def start(self):
        thread = threading.Thread(target=self._run_ui, daemon=True)
        thread.start()

        limite = time.time() + 5
        while not self.ready and time.time() < limite:
            time.sleep(0.05)

    def _run_ui(self):
        self.root = tk.Tk()
        self.root.title("Log do Robô")
        self.root.configure(bg="black")
        self.root.geometry("950x500+900+120")
        self.root.attributes("-topmost", False)

        self.text = ScrolledText(
            self.root,
            bg="black",
            fg="white",
            insertbackground="white",
            font=("Consolas", 10),
            wrap="word",
            relief="flat",
            borderwidth=0
        )
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        self.text.config(state="disabled")

        self.ready = True
        self.root.mainloop()

    def write(self, message: str):
        if not self.ready or not self.root or not self.text:
            return

        def _append():
            try:
                self.text.config(state="normal")
                self.text.insert("end", message)
                self.text.see("end")
                self.text.config(state="disabled")
            except Exception:
                pass

        try:
            self.root.after(0, _append)
        except Exception:
            pass


class DualLogger:
    def __init__(self, original_stream, floating_console: FloatingConsole):
        self.original_stream = original_stream
        self.floating_console = floating_console

    def write(self, message):
        try:
            self.original_stream.write(message)
            self.original_stream.flush()
        except Exception:
            pass

        try:
            self.floating_console.write(message)
        except Exception:
            pass

    def flush(self):
        try:
            self.original_stream.flush()
        except Exception:
            pass


floating_console = FloatingConsole()

def main():
    floating_console.start()
    sys.stdout = DualLogger(sys.__stdout__, floating_console)
    sys.stderr = DualLogger(sys.__stderr__, floating_console)
    
    try:
        os.makedirs(OUT_DIR, exist_ok=True)

        pasta_hoje = OUT_DIR
        os.makedirs(pasta_hoje, exist_ok=True)

        result_csv_path = os.path.join(OUT_DIR, "sei_last_doc_result.csv")

        itens_planilha = fetch_seis_from_sheet_api()
        if not itens_planilha:
            print("⚠️ Nenhum SEI encontrado na planilha.")
            return

        print(f"📄 SEIs encontrados na planilha: {len(itens_planilha)}")

        old_map = load_map()
        new_map = dict(old_map)
        results = []
        mudancas = {}

        sei_user = os.getenv("SEI_USER", "marcos.rigel")
        sei_pass = os.getenv("SEI_PASS", "Abc123!@")

        with SB(
            uc=False,
            headless=False,
            user_data_dir=SEI_CHROME_PROFILE
        ) as sb:

            sb.open(SEI_LOGIN_URL)
            sb.wait_for_ready_state_complete()

            if not sb.is_element_visible(XP_TXT_PESQUISA_RAPIDA):
                sb.wait_for_element_visible(XP_USUARIO, timeout=30)
                sb.type(XP_USUARIO, sei_user)

                sb.wait_for_element_visible(XP_SENHA, timeout=30)
                sb.type(XP_SENHA, sei_pass)

                sb.wait_for_element_visible(CSS_SELECT_ORGAO, timeout=30)
                sb.select_option_by_text(CSS_SELECT_ORGAO, "CEHAB")
                sb.sleep(0.5)

                sb.wait_for_element_visible(CSS_BTN_ACESSAR, timeout=30)
                sb.click(CSS_BTN_ACESSAR)
                sb.sleep(1.5)

            try:
                sb.accept_alert(timeout=2)
            except Exception:
                pass

            try:
                sb.switch_to_window(-1)
            except Exception:
                pass

            sb.wait_for_element_visible(XP_TXT_PESQUISA_RAPIDA, timeout=60)

            sei_quick_search(sb, itens_planilha[0]["sei"])
            tree_frame = find_tree_frame(sb, timeout=80)

            for idx, item_planilha in enumerate(itens_planilha, start=1):
                sei = item_planilha["sei"]
                objeto = item_planilha["objeto"]

                print(f"\n[{idx}/{len(itens_planilha)}] 🔎 SEI: {sei}")

                try:
                    sei_quick_search(sb, sei)

                    sb.switch_to_default_content()
                    sb.switch_to_frame(tree_frame)

                    expand_last_roman_folder(sb)

                    items = get_visible_files_in_tree(sb)
                    anterior = (new_map.get(sei) or "").strip()
                    texts = [t for _, t in items]

                    if anterior and anterior in texts:
                        idx_prev = texts.index(anterior)
                        novos = items[idx_prev + 1:]
                    else:
                        novos = [items[-1]]

                    novos_txts = [txt_item for _, txt_item in novos]
                    ultimo_txt = items[-1][1]
                    qtd_novos = len(novos)
                    mudou = (qtd_novos > 0 and (not anterior or ultimo_txt != anterior))

                    screenshot_paths = []

                    if qtd_novos > 0:
                        for num_item, txt_item in novos:
                            click_papel_azul_do_item(sb, num_item)
                            open_last_doc(sb, num_item)
                            sb.sleep(1.2)

                            prefix = f"sei_{safe_name(sei)}_{safe_name(txt_item)[:50]}"
                            shot = save_screenshot(sb, folder=pasta_hoje, prefix=prefix)
                            screenshot_paths.append(shot)

                        mudancas[sei] = {
                            "qtd_novos": qtd_novos,
                            "ultimo": ultimo_txt,
                            "novos": novos_txts,
                            "objeto": objeto,
                        }

                    print("   ✅ Último doc:", ultimo_txt)
                    if anterior:
                        print("   🗂️  Anterior :", anterior)
                    print("   🆕 Novos docs:", qtd_novos)
                    if novos_txts:
                        for t in novos_txts:
                            print("   ->", t)
                    print("   🔁 Mudou?    :", "SIM" if mudou else "NÃO")
                    if screenshot_paths:
                        print("   📸 Screenshots:", " | ".join(screenshot_paths))

                    new_map[sei] = ultimo_txt
                    save_map(new_map)
                    print(f"💾 MAP atualizado para {sei}: {ultimo_txt}")

                    results.append({
                        "sei": sei,
                        "objeto": objeto,
                        "ultimo_doc": ultimo_txt,
                        "mudou": "SIM" if mudou else "NAO",
                        "qtd_novos": qtd_novos,
                        "screenshot": " | ".join(screenshot_paths)
                    })

                except Exception as e:
                    print("   ❌ Erro neste SEI:", repr(e))
                    results.append({
                        "sei": sei,
                        "objeto": objeto,
                        "ultimo_doc": "",
                        "mudou": "ERRO",
                        "qtd_novos": 0,
                        "screenshot": ""
                    })
                finally:
                    sb.switch_to_default_content()

        linhas = []
        data_msg = datetime.now().strftime("%d/%m/%Y")

        linhas.append(f"🚨 CONTROLE - DESTAQUES ORÇAMENTÁRIOS Acompanhamento destaque 2026🚨 dia {data_msg}")
        linhas.append("📌 SEIs com novos documentos:")
        linhas.append("------------------------------")

        if not mudancas:
            linhas.append("Nenhum SEI mudou ✅")
        else:
            for sei_k, info in mudancas.items():
                linhas.append(sei_k)

                objeto_msg = (info.get("objeto") or "").strip()
                if objeto_msg:
                    linhas.append(f"Objeto: {objeto_msg}")

                for doc in info.get("novos", []):
                    linhas.append(f"-> {doc}")

                linhas.append("")

        mensagem_final = "\n".join(linhas)

        print("\n==============================")
        print(mensagem_final)
        print("==============================")

        save_map(new_map)
        save_results_csv(results, result_csv_path)

        if mudancas:
            enviar_mensagem_gop(mensagem_final)

        print("\n✅ Finalizado com sucesso!")

    except Exception as e:
        print(f"\n❌ Erro geral no robô: {e}")
        import traceback
        traceback.print_exc()

    finally:
        input("\n👉 Pressione ENTER para fechar o terminal...")


if __name__ == "__main__":
    main()
