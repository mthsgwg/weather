@echo off
rem Roda o atualizar_previsao.py a partir da pasta deste .bat.
rem No Agendador de Tarefas, aponte "Programa/script" para este arquivo.

cd /d "%~dp0"

rem Forca UTF-8 para acentos e setas nao quebrarem a saida no log
set PYTHONUTF8=1

rem Usa o launcher "py" se existir; senao, "python"
where py >nul 2>nul && (set PYTHON=py -3) || (set PYTHON=python)

echo ===== %date% %time% ===== >> atualizar_previsao.log
%PYTHON% atualizar_previsao.py >> atualizar_previsao.log 2>&1
exit /b %errorlevel%
