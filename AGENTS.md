# Pravidla a metodika agenta (AGENTS.md)

Tento dokument definuje lokální pravidla, hranice a metodiku práce AI asistenta (agenta) na tomto projektu. Pravidla jsou závazná pro všechny interakce a operace nad repozitářem.

---

## 1. O projektu (stručný přehled)

Jedná se o semestrální projekt v předmětu **Pokročilé programování (PPRO)** na FIM UHK (ZS 2026/2027).  
Aplikace řeší **rezervační a evidenční systém pro soukromou lékařskou praxi (Varianta A – Ordinace Na Vyhlídce)**.

> Veškeré detailní informace o zadání, funkčních požadavcích, obchodních pravidlech, technickém minimu a evidenci rozhodnutí jsou soustředěny v technické dokumentaci:  
> 📄 **[README.md](file:///u:/ING/1.%20semestr/PPRO/README.md)**  
> *(Informace se zde neduplikují, směrodatný je vždy dokument README.md).*

---

## 2. Podmínky a metodika práce na projektu

### 2.1 Schvalování postupu vývojářem (Approval First)
- **Každý krok a postup musí být předem konzultován a odsouhlasen vývojářem.**
- Agent nikdy neprovádí rozsáhlé změny, negeneruje celistvé moduly, ani nevolí klíčové technologie bez předchozího předložení plánu a získání výslovného souhlasu.
- Před zahájením práce na úkolu agent stručně shrne:
  1. Co přesně se chystá udělat.
  2. Jaké soubory/vrstvy budou dotčeny.
  3. Jaká rozhodnutí nebo alternativy zvažuje.
- Až po schválení vývojářem přistoupí k samotné realizaci.

### 2.2 Práce s Gitem a vzdáleným repozitářem
- **Push do vzdáleného repozitáře:**  
  Příkaz `git push` (na GitHub či jiný remote) je **přísně zakázáno spouštět svévolně či automaticky**. Push se provádí **výhradně na explicitní pokyn vývojáře**.
- **Lokální commity:**  
  Lokální commity se tvoří po ucelených, logických a funkčních krocích s dodržením konvence *Conventional Commits* (např. `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- **Integrita repozitáře:**  
  Před commitem musí být kód zkontrolován, zformátován a funkční.

### 2.3 Živá dokumentace a správa rozhodnutí
- Při každé domluvě o otevřeném bodu, volbě technologie či změně požadavku od vyučujícího (klienta na cvičení) musí agent zaznamenat rozhodnutí do sekce **4. Otevřené body klienta a sekce Rozhodnutí** v [README.md](file:///u:/ING/1.%20semestr/PPRO/README.md).
- Zápis musí vždy obsahovat: co bylo rozhodnuto, proč a jaký to má dopad na architekturu.

### 2.4 Technické a architektonické hranice
- **Třívrstvá architektura:** Dodržovat striktně jednosměrné závislosti (Prezentační vrstva $\to$ Aplikační/Byznys vrstva $\to$ Datová/Infrastrukturní vrstva). Žádné přímé dotazování databáze z kontrolerů/UI.
- **Relační databáze a migrace:** Veškeré změny schématu řešit výhradně přes migrace, nikdy ručním zásahem do databáze.
- **Docker Compose:** Projekt musí zůstat kdykoliv spustitelný jediným příkazem `docker compose up`.
- **Testování:** Kritická byznys pravidla (zejména zákaz překryvu termínů a dodržení ordinačních hodin) musí být pokryta automatizovanými testy.
- **Bezpečnost a čistota dat:** Žádné reálné osobní údaje, žádné přihlašovací údaje/tajné klíče v kódu ani v gitu (používat proměnné prostředí / syntetická data).
