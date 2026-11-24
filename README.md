# weather

Script simples que gera um CSV com a previsão do tempo de hoje para uma lista de cidades.
Usa a [Open-Meteo](https://open-meteo.com/) (gratuita, sem chave de API) e só Python 3, sem dependências.

## Uso

1. Liste as cidades em `cidades.txt`, uma por linha, no formato `Cidade / UF`:

   ```
   Patos / PB
   Recife / PE
   ```

2. Configure o caminho do ícone de cada condição no dicionário `ICONES`, no topo de `atualizar_previsao.py`.

3. Rode:

   ```bash
   python3 atualizar_previsao.py [--cidades cidades.txt] [--saida previsao.csv]
   ```

## Saída

Uma linha por cidade em `previsao.csv`:

```
id,cidade,uf,data,condicao,icone,codigo_wmo,temp_min,temp_max,chuva_mm,prob_chuva,vento_max_kmh,atualizado_em
patos-pb,Patos,PB,2026-11-24,Nublado,icones/nublado.png,3,24.8,40.1,0.0,0,26.5,2026-11-24T14:49:42
```

`condicao` é uma de: Ensolarado, Parcialmente nublado, Nublado, Chuva, Tempestade.

Para atualizar automaticamente, agende no cron (ex.: de hora em hora):

```
0 * * * * cd /caminho/para/weather && python3 atualizar_previsao.py
```

No Windows, use o `atualizar_previsao.bat` no Agendador de Tarefas (em "Programa/script", aponte para o .bat).
Ele roda o script na própria pasta e grava a saída em `atualizar_previsao.log`.
