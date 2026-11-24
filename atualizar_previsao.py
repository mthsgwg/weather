#!/usr/bin/env python3
"""Atualiza um CSV com a previsão do tempo de hoje das cidades listadas em cidades.txt.

Fonte: Open-Meteo (gratuita, sem chave de API).

Arquivo de cidades: uma por linha, "Cidade / UF" (UF opcional; # comenta a linha).
    Patos / PB
    Recife / PE

Uso:
    python3 atualizar_previsao.py [--cidades cidades.txt] [--saida previsao.csv]
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "America/Sao_Paulo"

UFS = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Federal District", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia",
    "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
    "TO": "Tocantins",
}

# ===== CONFIGURE AQUI: caminho do ícone de cada condição =====
ICONES = {
    "Ensolarado": "icones/ensolarado.png",
    "Parcialmente nublado": "icones/parcialmente_nublado.png",
    "Nublado": "icones/nublado.png",
    "Chuva": "icones/chuva.png",
    "Tempestade": "icones/tempestade.png",
}


def condicao_base(codigo_wmo):
    """Agrupa os códigos WMO da Open-Meteo nas 5 condições base."""
    if codigo_wmo in (0, 1):
        return "Ensolarado"
    if codigo_wmo == 2:
        return "Parcialmente nublado"
    if codigo_wmo in (3, 45, 48):  # nublado e nevoeiro
        return "Nublado"
    if codigo_wmo >= 95:  # trovoadas, com ou sem granizo
        return "Tempestade"
    return "Chuva"  # garoa, chuva, pancadas (e neve, que não ocorre aqui)


COLUNAS_SAIDA = [
    "id", "cidade", "uf", "data", "condicao", "icone", "codigo_wmo",
    "temp_min", "temp_max", "chuva_mm", "prob_chuva", "vento_max_kmh",
    "atualizado_em",
]


def get_json(url, params):
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(full_url, timeout=20) as resp:
        return json.load(resp)


def normalizar(texto):
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore")
    return sem_acento.decode().strip().lower()


def geocodificar(nome, uf):
    data = get_json(GEOCODING_URL, {
        "name": nome, "count": 10, "language": "pt", "countryCode": "BR",
    })
    resultados = data.get("results") or []
    if uf:
        estado = normalizar(UFS.get(uf.upper(), uf))
        resultados = [r for r in resultados if normalizar(r.get("admin1")) == estado]
    if not resultados:
        raise ValueError("cidade não encontrada")
    return resultados[0]


def buscar_previsao_hoje(lat, lon):
    daily = get_json(FORECAST_URL, {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join([
            "weather_code", "temperature_2m_min", "temperature_2m_max",
            "precipitation_sum", "precipitation_probability_max",
            "wind_speed_10m_max",
        ]),
        "timezone": TIMEZONE,
        "forecast_days": 1,
    })["daily"]
    # Com forecast_days=1 cada campo vem como lista de um único item (hoje)
    return {campo: valores[0] for campo, valores in daily.items()}


def ler_cidades(caminho):
    """Lê linhas "Cidade / UF" e devolve [(linha, nome, uf)]. Aceita também "Cidade - UF" ou "Cidade, UF"."""
    cidades = []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.split("#", 1)[0].strip()
            if not linha:
                continue
            m = re.fullmatch(r"(.+?)\s*[/,-]\s*([A-Za-z]{2})", linha)
            # Só separa se o final for uma UF válida, para não quebrar nomes como "Embu-Guaçu"
            if m and m.group(2).upper() in UFS:
                cidades.append((linha, m.group(1).strip(), m.group(2).upper()))
            else:
                cidades.append((linha, linha, ""))
    return cidades


def slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", normalizar(texto)).strip("-")


def gravar_atomico(caminho, linhas):
    # Escreve em arquivo temporário e renomeia, para quem lê o CSV nunca pegar arquivo pela metade
    pasta = os.path.dirname(os.path.abspath(caminho))
    fd, tmp = tempfile.mkstemp(dir=pasta, suffix=".csv")
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUNAS_SAIDA)
        writer.writeheader()
        writer.writerows(linhas)
    os.replace(tmp, caminho)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cidades", default="cidades.txt")
    parser.add_argument("--saida", default="previsao.csv")
    args = parser.parse_args()

    agora = datetime.now().isoformat(timespec="seconds")
    linhas, falhas = [], 0

    for linha, nome, uf in ler_cidades(args.cidades):
        try:
            local = geocodificar(nome, uf)
            hoje = buscar_previsao_hoje(local["latitude"], local["longitude"])
        except Exception as e:
            falhas += 1
            print(f"[erro] {linha}: {e}", file=sys.stderr)
            continue

        # Usa o nome oficial encontrado (com acentos corretos) e a UF real do resultado
        nome = local["name"]
        uf = uf or next((s for s, e in UFS.items() if normalizar(e) == normalizar(local.get("admin1"))), "")
        cid = slug(f"{nome} {uf}")

        condicao = condicao_base(hoje["weather_code"])
        linhas.append({
            "id": cid,
            "cidade": nome,
            "uf": uf,
            "data": hoje["time"],
            "condicao": condicao,
            "icone": ICONES[condicao],
            "codigo_wmo": hoje["weather_code"],
            "temp_min": hoje["temperature_2m_min"],
            "temp_max": hoje["temperature_2m_max"],
            "chuva_mm": hoje["precipitation_sum"],
            "prob_chuva": hoje["precipitation_probability_max"],
            "vento_max_kmh": hoje["wind_speed_10m_max"],
            "atualizado_em": agora,
        })
        print(f"[ok] {linha} → {nome}/{uf}")

    if not linhas:
        print("Nenhuma previsão obtida; arquivo de saída não foi alterado.", file=sys.stderr)
        return 1

    gravar_atomico(args.saida, linhas)
    print(f"{args.saida} atualizado ({len(linhas)} linhas, {falhas} falha(s))")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
