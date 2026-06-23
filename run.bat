@echo off
chcp 65001 > nul
echo ======================================================
echo          Pokemon Dataset Downloader (Completo)
echo ======================================================
echo.
echo Dica: Se possuir uma chave da API do Pokemon TCG, 
echo defina-a como POKEMON_TCG_API_KEY para downloads mais rapidos.
echo.

echo [1/11] Baixando Habilidades (Abilities)...
python downloadAbility.py

echo [2/11] Baixando Frutas (Berries)...
python downloadBerry.py

echo [3/11] Baixando Encontros (Encounters)...
python downloadEnconter.py

echo [4/11] Baixando Itens (Items)...
python downloadItem.py

echo [5/11] Baixando Movimentos (Moves)...
python downloadMoves.py

echo [6/11] Baixando Natures...
python downloadNature.py

echo [7/11] Baixando Locais (Places)...
python downloadPlace.py

echo [8/11] Baixando Pokemon (Sprites, Cards)...
python downloadPokemon.py

echo [9/11] Baixando Efeitos do Super Contest (Super Contest Efeitos)...
python downloadSuperContestEfect.py

echo [10/11] Baixando Tipos (Types)...
python downloadType.py

echo [11/11] Baixando Estatisticas (Stats)...
python downloadstat.py

echo.
echo ======================================================
echo Processo concluido!
echo ======================================================
pause
