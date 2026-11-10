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
   - Povinná textová poznámka s důvodem návštěvy (proč pacient přichází).
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
| **1** | **Délka jednoho termínu** | Mřížka po 15 minutách vs. dynamická délka termínu podle typu vyšetření. | Pevná mřížka **15minutových slotů**. Rezervace zabírá 1 až N po sobě jdoucích slotů (max. 16 slotů = 4 h) a musí celá ležet v jednom bloku ordinačních hodin. Recepce délku volí přímo v kalendáři (kliknutí = 1 slot, tažení = více slotů). Žádná fragmentace mimo mřížku, překryv lze jednoznačně kontrolovat po slotech. | Schváleno a realizováno |
| **2** | **Kdo zakládá rezervaci** | Výhradně recepce vs. pacienti přes web. | Rezervace zakládá **recepce a administrátor** (role `RECEPTIONIST`, `ADMIN`). Lékař kalendář a detaily rezervací vidí, ale termíny nezakládá. Veškerá pravidla jsou v servisní vrstvě za REST API `POST /api/v1/appointments`, takže budoucí pacientský portál lze napojit bez přepisování byznys logiky. | Schváleno a realizováno |
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
- **2026-11-10:** **Realizace Funkčního požadavku 2 – Správa lékařů a ordinačních hodin:**
  - **Co bylo rozhodnuto:** Lékař je samostatná doménová entita `doctors` (jméno, specializace, barva v kalendáři, stav) s volitelnou vazbou 1:1 na uživatelský účet. Týdenní ordinační hodiny jsou bloky `office_hours` (den v týdnu, začátek, konec), lékař může mít více bloků denně (např. dopoledne a odpoledne). Hodiny smí měnit administrátor a lékař, kterému profil patří. Seed obsahuje 3 lékaře (Hrubá, Malý, Veselá) s výchozími hodinami.
  - **Proč:** Oddělení přihlašovacího účtu od doménové entity lékaře (lékař může existovat i bez účtu, do budoucna pacientský portál). Změna hodin, která by vyřadila již naplánované budoucí rezervace, je odmítnuta (409) – rezervace nesmí „osiřet“ mimo ordinační hodiny.
  - **Odloženo:** Jednorázové výjimky v dostupnosti (konkrétní datum / nemoc) se budou řešit později spolu s otevřeným bodem 5. Pravidelná nedostupnost (např. úterní odpoledne na jiné adrese) se řeší tím, že daný blok v týdenních hodinách chybí.
  - **Dopad na architekturu:**
    - Datová vrstva: modely `DoctorModel`, `OfficeHoursModel`, migrace `003_doctors_office_hours`, repozitář `DoctorRepository`, seed `seed_doctors()`.
    - Aplikační vrstva: čistá doménová logika `src/business/scheduling.py` (zarovnání na 15 min, rozpad na sloty, kontrola ordinačních hodin, validace bloků) a `DoctorService`.
    - Prezentační vrstva: `doctor_router.py` (`/doctors`, `/doctors/{id}/office-hours`, `/doctors/{id}/calendar`), záložka *Lékaři a ordinační hodiny* s editorem hodin.
- **2026-11-10:** **Realizace Funkčního požadavku 3 – Rezervace termínu u konkrétního lékaře:**
  - **Co bylo rozhodnuto:** Rezervace (`appointments`) s povinným důvodem návštěvy a stavovým modelem `PLANNED / COMPLETED / CANCELLED_BY_PATIENT / CANCELLED_BY_OFFICE / NO_SHOW` (zatím se používá `PLANNED`, ostatní stavy připravují otevřený bod 3 a FP4/FP5). Ochrana proti překryvu je dvojí: kontrola v servisní vrstvě (srozumitelná hláška) a **databázová pojistka** – tabulka obsazených slotů `appointment_slots` s `UNIQUE(doctor_id, slot_start)`. Při souběžném pokusu o stejný slot databáze druhý zápis odmítne a API vrátí 409.
  - **Proč:** Klient trvá na tom, že kolize nesmí vzniknout „za žádných okolností“ – čistě aplikační kontrola by nebyla odolná vůči souběhu. Řešení přes sloty funguje v PostgreSQL i v SQLite testech a přesně odpovídá 15min mřížce. Při budoucím zrušení se sloty smažou (termín se uvolní), záznam rezervace zůstane v historii pro statistiky.
  - **Model času:** `start_at` / `end_at` jsou naivní lokální čas ordinace (Europe/Prague), „teď“ se počítá v této zóně.
  - **Dopad na architekturu:**
    - Datová vrstva: modely `AppointmentModel`, `AppointmentSlotModel`, migrace `004_create_appointments`, repozitář `AppointmentRepository`, demo rezervace v seedu.
    - Aplikační vrstva: `AppointmentService` (aktivní lékař a pacient, zarovnání, stejný den, max. 4 h, ne v minulosti, v ordinačních hodinách, volné sloty) a počty nadcházejících rezervací v `PatientService`.
    - Prezentační vrstva: `appointment_router.py` (`POST /appointments`, `GET /appointments/{id}`), `GET /patients/{id}/appointments`, záložka *Rezervace* s týdenním kalendářem (7 řádků Po–Ne, 15min buňky, výběr kliknutím/tažením, obsazené termíny červeně s detailem, mimo ordinační hodiny a minulost šedě, přepínání týdnů šipkami) a sloupec *Rezervace* v evidenci pacientů.
    - Testy: `tests/test_scheduling.py`, `tests/test_doctors.py`, `tests/test_appointments.py` (přesná kolize, částečný překryv, navazující termíny, DB pojistka, mimo ordinační hodiny, přes polední pauzu, oprávnění). Celá sada 54 testů prochází.
- **2026-11-10:** **Zrychlení testů:** cena bcryptu je nastavitelná přes `BCRYPT_ROUNDS` (výchozí 12 pro provoz, v testech 4). Sada testů se zrychlila z ~120 s na ~4 s, produkční bezpečnost hesel se nemění.
- **2026-11-10:** **Refaktor na striktní třívrstvou architekturu:**
  - **Co bylo rozhodnuto:** Závislosti vrstev vedou výhradně směrem Prezentace → Byznys → Infrastruktura a jsou vynucené automatickým testem.
    - Byznys vrstva nevyhazuje `HTTPException`, ale doménové výjimky (`src/business/exceptions.py`: `NotFoundError`, `BusinessRuleError`, `ConflictError`, `PermissionDeniedError`, `AuthenticationError`, `AccountDisabledError`). Na HTTP status kódy je převádí prezentační vrstva (`src/presentation/error_handlers.py`).
    - Vstupní DTO (`*Create`, `*Update`, `OfficeHoursUpdate`, `AppointmentCreate`) jsou v byznys vrstvě (`src/business/dto/`) jako Pydantic modely (varianta a – bez duplicity validací). Odpovědní modely (`*Response`) zůstávají v prezentaci.
    - Prezentace nepřistupuje k infrastruktuře – potřebné typy (`User`, `UserRole`, `AppointmentStatus`, `get_db`) získává přes fasádu `src/business/domain.py`. Ověření JWT tokenu a kontrola rolí jsou v `AuthService` (`get_user_from_token`, `ensure_role`).
    - Seed demo dat je přesunut do `src/business/seed.py` (používá byznys pravidla), datová vrstva tak nezávisí na vyšších vrstvách.
    - Kontrola „trvale smazat pacienta smí jen administrátor“ je přesunuta z routeru do `PatientService`.
  - **Proč:** Požadavek technického minima PPRO a AGENTS.md (striktně jednosměrné závislosti, žádné dotazování DB z kontrolerů). Byznys logika je nezávislá na HTTP, takže ji lze testovat bez webu a později použít např. pro pacientský portál.
  - **Dopad na architekturu:** API kontrakt (endpointy, status kódy, texty chyb) zůstal beze změny – všech 54 původních testů prošlo bez úprav. Nové testy: `tests/test_architecture.py` (AST kontrola importů každé vrstvy – na stavu před refaktorem odhalí 27 porušení) a `tests/test_services.py` (unit testy servisů bez HTTP). Celkem 66 testů.
- **2026-11-11:** **Realizace Funkčního požadavku 4 – Záznam o uskutečněné návštěvě:**
  - **Co bylo rozhodnuto:**
    - Centrální číselník výkonů `procedures` (kód, název, body, aktivita) spravuje administrátor; seed obsahuje 12 ilustrativních výkonů se syntetickými body.
    - Záznam návštěvy `visits` je vázaný 1:1 na rezervaci. Výkony k návštěvě eviduje asociační entita `visit_procedures` (**relace M:N Návštěva ↔ Výkon**) s počtem provedení a **snapshotem bodů** v okamžiku zápisu.
    - Životní cyklus **koncept (`DRAFT`) → uzavřeno (`CLOSED`)**: koncept lze průběžně ukládat, uzavřená návštěva je neměnná a rezervace přejde do stavu `COMPLETED`. Návštěvu nelze smazat (API mazání neposkytuje).
    - Výkony zapisuje lékař, kterému návštěva patří, nebo administrátor; recepce vše vidí jen ke čtení.
    - UI: nová záložka *Ordinace dnes* (fronta dne lékaře se stavy Čeká / K zápisu / Rozpracováno / Uzavřeno a panel se zápisem výkonů) a *Karta pacienta* s historií návštěv, výkonů a bodů.
  - **Proč:** Splnění FP4 a obchodních pravidel *kauzální integrita výkonů* (koncept lze založit jen k rezervaci, jejíž začátek už nastal – výkony nelze předvyplňovat do budoucna) a *neměnnost historie*. Snapshot bodů zajišťuje, že pozdější změna číselníku nezmění historii ani budoucí měsíční výkaz (FP7), který bude počítat jen uzavřené návštěvy.
  - **Dopad na architekturu:**
    - Datová vrstva: modely `ProcedureModel`, `VisitModel`, `VisitProcedureModel`, migrace `005_visits_and_procedures`, repozitáře `ProcedureRepository`, `VisitRepository`; kalendář nově zobrazuje i uskutečněné rezervace (slot zůstává obsazený).
    - Byznys vrstva: `ProcedureService`, `VisitService` (doménové výjimky), DTO `visit_dto.py`, seed číselníku a demo návštěv z minulého týdne.
    - Prezentační vrstva: `procedure_router.py`, `visit_router.py` (`/doctors/{id}/agenda`, `/appointments/{id}/visit`, `/visits/{id}`, `/visits/{id}/close`), `GET /patients/{id}/history`.
    - Testy: `tests/test_visits.py` (17 testů – kauzalita, oprávnění, M:N s počty, snapshot bodů, neměnnost, fronta dne, historie) a unit testy `VisitService`. Celkem 86 testů.

