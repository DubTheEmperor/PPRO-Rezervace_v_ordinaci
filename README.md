# Systém pro rezervace v lékařské ordinaci (Ordinace Na Vyhlídce)

> **Předmět:** Pokročilé programování (PPRO) – ZS 2026/2027, FIM UHK  
> **Zadání:** Varianta A – Rezervace v ordinaci  
> **Klient:** MUDr. Jana Hrubá, Ordinace Na Vyhlídce  
> **Konzultace předmětu:** dominik.palla@uhk.cz  

---

## 1. Kontext a současný stav klienta

### Profil praxe
- **Ordinace Na Vyhlídce:** Soukromá lékařská praxe.
- **Personál:** 3 lékaři na částečné úvazky a recepční (paní Věra).
- **Klientská základna:** Přibližně 900 pacientů, z nichž zhruba polovina dochází na kontroly a ošetření pravidelně.

### Jak to v ordinaci funguje dnes
- **Papírový diář na recepci:** Všechny objednávky se zaznamenávají ručně tužkou.
- **Hledání termínů:** Pacienti volají telefonicky; paní Věra zdlouhavě listuje papírovým diářem a hledá volná okna.
- **Výpadky lékařů:** V případě nemoci lékaře musí recepční ručně procházet diář a pacienty jednoho po druhém telefonicky obvolávat.
- **Měsíční výkazy pro pojišťovny:** Na konci každého měsíce paní Věra ručně přepisuje provedené výkony do tabulky pro zdravotní pojišťovnu, což jí podle jejích slov pravidelně zabere celý jeden podvečer.
- **Kritický problém z praxe:** Během posledního roku se již dvakrát stalo, že v čekárně seděli dva pacienti objednaní na tentýž čas u stejného lékaře. Klientka to vnímá jako nepřijatelnou ostudu, která se nesmí opakovat.

---

## 2. Požadavky klienta

### 2.1 Co klient chce (Funkční požadavky)
1. **Evidence pacientů:**
   - Uchování údajů: jméno, příjmení, rok narození, telefonní číslo, identifikátor pojištěnce (číslo pojištěnce / rodné číslo), kód zdravotní pojišťovny.
   - Rychlé vyhledávání pacienta podle **příjmení** nebo **telefonního čísla** (klíčové pro telefonický kontakt).
2. **Správa lékařů a ordinačních hodin:**
   - Evidence lékařů ordinace.
   - Každý lékař má specifické ordinační dny a časové bloky.
   - Podpora výjimek v dostupnosti (např. jeden z lékařů ordinuje v úterý odpoledne na jiné adrese – na tento čas se v systému nesmí dát objednávat).
3. **Rezervace termínu u konkrétního lékaře:**
   - Objednání konkrétního pacienta na konkrétní datum a čas ke zvolenému lékaři.
   - Rezervaci zadává recepce.
   - Povinná/volitelná textová poznámka s důvodem návštěvy (proč pacient přichází).
4. **Záznam o uskutečněné návštěvě:**
   - Po příchodu pacienta a realizaci vyšetření zápis skutečně provedených výkonů.
   - Výkony se vybírají z centrálního číselníku výkonů (kód výkonu, název výkonu, bodové ohodnocení).
   - V rámci jedné návštěvy může být vykázáno více různých výkonů i tentýž výkon opakovaně (možnost zadat počet aplikací/opakování, např. 3× aplikace).
5. **Zrušení rezervace a sledování spolehlivosti:**
   - Možnost zrušit termín na základě telefonátu pacienta.
   - Přehled a statistika pacientů, kteří ruší termíny opakovaně či nedorazí (např. podchycení situací typu „paní Krátká nepřišla letos pětkrát“).
6. **Týdenní přehled volných termínů:**
   - Zobrazení volných slotů pro zvoleného lékaře a vybraný kalendářní týden.
   - Zásadní ergonomická funkce určená pro nejčastější použití paní Věrou během telefonátů.
7. **Měsíční výkaz pro pojišťovny:**
   - Generování přehledu za zvolený kalendářní měsíc a vybraného lékaře.
   - Seznam provedených výkonů a automatický součet vykázaných bodů (odstranění ručního přepisování).

### 2.2 Na čem klient striktně trvá (Obchodní pravidla vynucená systémem)
- **Zákaz kolizí termínů:** Dvě rezervace na stejný termín u stejného lékaře nesmí jít založit za žádných okolností (ani ručně, ani omylem).
- **Respektování ordinačních hodin:** Rezervaci nelze založit mimo platné ordinační hodiny daného lékaře.
- **Kauzální integrita výkonů:** Zdravotní výkon nelze zapsat k návštěvě, která se ještě neuskutečnila (žádné předvyplňování do budoucích termínů).
- **Neměnnost a auditovatelnost historie:** Historie pacienta a proběhlých návštěv se nesmí mazat (z důvodu právní odpovědnosti a doložitelnosti poskytnuté péče).

### 2.3 Co klient prohodil mimochodem (Přání, nálady a ergonomické aspekty)
- *„Musí to zvládnout paní Věra, ta s počítačem moc nekamarádí.“* → Rozhraní musí být přehledné, intuitivní, bez zbytečné vizuální složitosti, s velkými čitelnými prvky.
- *„Když zvoní telefon, nemůžu čekat, až se to načte.“* → Důraz na bleskovou odezvu vyhledávání a kalendářního zobrazení.
- *„Bylo by hezké, kdybych to viděla i na tabletu, ale to nespěchá.“* → Responzivní design rozhraní (tablet-friendly).
- *„Pacienti by se možná mohli objednávat sami přes internet, ale bojím se toho.“* → Architektura by do budoucna neměla vylučovat pacientský portál/API, ale v 1. fázi se soustředíme na interní provoz recepce.

---

## 3. Společné technické minimum PPRO

Podle společných pravidel předmětu PPRO projekt splňuje a dodržuje následující kritéria:
1. **Třívrstvá architektura:**
   - Striktní oddělení vrstev se závislostmi jedním směrem:
     - Prezentační vrstva (UI / API rozhraní)
     - Aplikační / Byznys vrstva (obchodní logika, doménová pravidla, validace)
     - Datová / Infrastrukturní vrstva (přístup k databázi, perzistence)
2. **Relační databáze s migracemi:**
   - Běh v Docker kontejneru.
   - Správa verzování databázového schématu pomocí migračních skriptů.
3. **Datový model:**
   - Nejméně 5 doménových entit.
   - Minimálně jedna relace M:N (např. Návštěva `M:N` Výkon přes asociační entitu položky výkonu na návštěvě s počtem a bodovou hodnotou).
4. **Kontejnerizace:**
   - Kompletní a reprodukovatelné spuštění celé aplikace jediným příkazem:
     ```bash
     docker compose up
     ```
5. **Testování:**
   - Sada automatizovaných unit a integračních testů ověřujících klíčová byznys pravidla (překryvy termínů, validace ordinačních hodin, výpočty bodů).
6. **Ochrana dat a syntetická data:**
   - Výhradně syntetická testovací data (žádná reálná rodná čísla, jména ani lékařské záznamy).
   - Žádná hesla, přístupové tokeny ani tajné klíče v git repozitáři.
7. **Kde se návrh láme (kritické doménové místo):**
   - Správný model překrývání termínů a přesná sémantika zrušené rezervace vs. uvolnění slotu vs. statistika rušení.

---

## 4. Otevřené body klienta a sekce Rozhodnutí

Následující tabulka a záznamy slouží jako **živý architektonický deník**. Zachycují, jakým způsobem jsou vyřešeny nejednoznačnosti ze zadání a na čem se v průběhu vývoje dohodneme s vývojářem a vyučujícím (klientem).

### 4.1 Řešení otevřených bodů ze zadání

| # | Otevřený bod klienta | Problém / Dilema | Přijaté rozhodnutí a odůvodnění | Stav |
|---|---|---|---|---|
| **1** | **Délka jednoho termínu** | Mřížka po 15 minutách vs. dynamická délka termínu podle typu vyšetření. | *V diskuzi s vývojářem.* Návrh: Základní časový slot s pevnou délkou (např. 15 či 30 minut) nebo násobky slotů podle typu zákroku, aby se předešlo fragmentaci a kolizím v kalendáři. | K odsouhlasení |
| **2** | **Kdo zakládá rezervaci** | Výhradně recepce vs. pacienti přes web. | Primární zaměření na recepční rozhraní (paní Věra). Backend navrhnout přes čisté servisní rozhraní / API tak, aby v budoucnu bylo možné napojit klientský portál bez přepisování byznys logiky. | K odsouhlasení |
| **3** | **Co se zrušenou rezervací** | Zmizení z diáře vs. zachování pro statistiku nespolehlivých pacientů. | Stavový model rezervace (např. `STAV: PLANOVANA, USKUTECNENA, ZRUSA_PACIENTEM, ZRUSA_ORDINACI`). V kalendáři se zrušený termín uvolní pro novou rezervaci (neblokuje slot), ale záznam o zrušení zůstává trvale v historii pacienta pro statistiky. | K odsouhlasení |
| **4** | **Jednoznačná totožnost pacienta** | Duplicity v diáři, nejasný primární identifikátor. | Jednoznačným klíčem v evidenci bude kombinace čísla pojištěnce (rodného čísla) a pojišťovny. Při zakládání nového pacienta systém provede deduplikační kontrolu (shoda telefonu, jména a data narození) a upozorní recepční na případnou existenci karty. | Schváleno a realizováno |
| **5** | **Výpadek / nemoc lékaře** | Hromadné zrušení, přesun k jinému lékaři, nebo jen označení a obvolání. | Vytvoření režimu mimořádné nedostupnosti lékaře: dotčené rezervace přejdou do stavu `K_PREOBJEDNANI` a recepční se vygeneruje přehledná pracovní fronta pro obvolání s možností rychlého přesunu na volné sloty kolegů. | K odsouhlasení |

### 4.2 Průběžný protokol dohodnutých změn a rozhodnutí (Changelog rozhodnutí)
- **2026-10-05:** Inicializace projektové dokumentace zadání A podle zadávacího dokumentu PPRO (verze 1). Založení struktury otevřených bodů k potvrzení vývojářem.
- **2026-10-05:** **Volba technologického stacku a architektury:**
  - Backend: **Python 3.12** a framework **FastAPI**.
  - ORM a migrace: **SQLAlchemy 2.0** a **Alembic**.
  - Databáze: **PostgreSQL 16** v Docker kontejneru.
  - Architektura: Striktní **třívrstvá architektura** (`presentation`, `business`, `infrastructure`).
  - Rozsah demo verze: Kontejnerizace přes `docker-compose.yml`, bezpečné přihlašování přes JWT a OAuth2 Password flow, kompletní správa uživatelů (CRUD), předdefinované role (`ADMIN`, `RECEPTIONIST`, `DOCTOR`), jednoduché webové rozhraní (HTML/CSS) a automatizované testy v `pytest`.
- **2026-10-30:** **Realizace Funkčního požadavku 1 – Evidence pacientů:**
  - **Co bylo rozhodnuto:** Vytvoření kompletního modulu evidence pacientů (jméno, příjmení, rok narození, telefonní číslo, číslo pojištěnce / rodné číslo, kód zdravotní pojišťovny, interní poznámka, stav aktivity).
  - **Proč:** Splnění funkčního požadavku 1 a vyřešení otevřeného bodu 4. Zajištění rychlého vyhledávání podle příjmení i telefonu při telefonickém kontaktu recepční (paní Věry), validace formátů a číselníku pojišťoven v ČR. Zachování zdravotní historie pomocí měkké deaktivace (`is_active = False`).
  - **Dopad na architekturu:**
    - Datová vrstva: model `PatientModel`, migrace Alembic `002_create_patients_table`, databázové indexy na `last_name`, `phone_number` a unikátní index na `insurance_number`, repozitář `PatientRepository` a syntetický seed.
    - Aplikační/byznys vrstva: Pydantic DTO validace (`patient_schemas.py`), byznys servis `PatientService` se striktní kontrolou duplicity a ochranou historie.
    - Prezentační vrstva: REST API `patient_router.py` a responzivní záložka *Evidence pacientů* ve webovém rozhraní pro paní Věru.
    - Testy: 8 nových automatizovaných testů v `tests/test_patients.py` (všechny testy v suite procházejí).

