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
| **3** | **Co se zrušenou rezervací** | Zmizení z diáře vs. zachování pro statistiku nespolehlivých pacientů. | Stavový model rezervace `PLANNED / COMPLETED / CANCELLED_BY_PATIENT / CANCELLED_BY_OFFICE / NO_SHOW`. Při zrušení i nedostavení se smažou obsazené sloty (termín se v kalendáři ihned uvolní), rezervace se nemaže a zůstává v historii pacienta (kdo a kdy stav nastavil). Do spolehlivosti pacienta se počítá zrušení pacientem a nedostavení, zrušení ordinací ne. | Schváleno a realizováno |
| **4** | **Jednoznačná totožnost pacienta** | Duplicity v diáři, nejasný primární identifikátor. | Jednoznačným klíčem v evidenci bude kombinace čísla pojištěnce (rodného čísla) a pojišťovny. Při zakládání nového pacienta systém provede deduplikační kontrolu (shoda telefonu, jména a data narození) a upozorní recepční na případnou existenci karty. | Schváleno a realizováno |
| **5** | **Výpadek / nemoc lékaře** | Hromadné zrušení, přesun k jinému lékaři, nebo jen označení a obvolání. | Režim mimořádné nedostupnosti lékaře. Lékař (svou) nebo administrátor označí **celé dny nemoci** v mini kalendáři na kartě lékaře. Naplánované a ještě nezačaté rezervace v těch dnech přejdou do stavu `TO_RESCHEDULE` (K přeobjednání). Jejich **sloty zůstávají obsazené**, takže se na původní čas nikdo jiný neobjedná. Na nemocný den nelze rezervovat. Recepce má v záložce Rezervace podzáložku **K přeobjednání**: pracovní frontu s telefonem pacienta a akcemi *Přeobjednat* (rychlý přesun na volný slot kolegy či pozdější termín, původní rezervace → `RESCHEDULED` s odkazem na novou) a *Zrušit termín* (zrušeno ordinací). Při dřívějším uzdravení se po odznačení dne nevyřízené termíny **samy vrátí** do stavu `PLANNED`. | Schváleno a realizováno |

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
  - **Odloženo:** Jednorázové výjimky v dostupnosti (konkrétní datum / nemoc) se budou řešit později spolu s otevřeným bodem 5. Pravidelná nedostupnost (např. úterní odpoledne na jiné adrese) se řeší tím, že daný blok v týdenních hodinách chybí. *(Nahrazeno 2026-11-13 blokem „Jiné pracoviště“, viz níže. Nemoc vyřešena 2026-11-13, viz záznam „Nemoc lékaře“.)*
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
- **2026-11-11:** **Fronta návštěv s filtry místo denního pohledu a omezení viditelnosti zdravotních záznamů:**
  - **Co bylo rozhodnuto:**
    - Záložka *Ordinace dnes* je nahrazena záložkou **Návštěvy**: fronta návštěv lékaře od nejnovější do minulosti, seskupená po dnech, s filtry *K vyřízení* (výchozí – K zápisu + Rozpracováno), *Dnes*, *Rozpracováno*, *Uzavřeno*, *Vše* a jejich počty; starší položky se načítají po stránkách. Budoucí dny se ve frontě nezobrazují (řeší je kalendář rezervací). Na záložce je odznak s počtem nevyřízených návštěv.
    - Viditelnost podle zásady nejmenších oprávnění (vynucuje API): záložku a frontu vidí jen lékař (pouze vlastní návštěvy) a administrátor (s výběrem lékaře); recepce ji nevidí. Detail záznamu návštěvy vidí lékaři a administrátor. V kartě pacienta vidí lékaři celou historii (kontinuita péče), recepce termíny a výkony **bez klinických poznámek**.
  - **Proč:** Při denním pohledu se nezapsaná návštěva z minulých dnů snadno ztratila – lékař musel trefit přesné datum. Neuzavřené návštěvy by přitom chyběly v měsíčním výkazu (FP7). Klinické poznámky recepce pro svou práci (rezervace, výkazy) nepotřebuje.
  - **Dopad na architekturu:** endpoint `GET /doctors/{id}/agenda` nahrazen `GET /doctors/{id}/visit-queue` (filtry, kurzorové stránkování, počty jedním SQL dotazem) a přidán `GET /visits/pending-count`; oprávnění v `VisitService`. Poznámka pro FP7: výkaz má upozornit na neuzavřené návštěvy v daném měsíci, aby recepce poznala neúplný výkaz. Testy: 92.

- **2026-11-11:** **Realizace Funkčního požadavku 5 – Zrušení rezervace a sledování spolehlivosti:**
  - **Co bylo rozhodnuto:**
    - Recepce (a administrátor) ruší termín tam, kde ho při telefonátu hned najde: v evidenci pacientů v seznamu nadcházejících rezervací (📅) a v detailu rezervace v kalendáři. Dialog rozliší *Ruší pacient* / *Ruší ordinace* a umožní krátkou nepovinnou poznámku. Zrušit lze jen naplánovaný termín, který ještě nezačal.
    - Proběhlý naplánovaný termín bez záznamu návštěvy lze označit **Nedostavil se** (recepce, administrátor, lékař, jemuž termín patří) – v detailu rezervace a ve frontě *Návštěvy*. K takovému termínu už nelze zapsat návštěvu. Obě akce jsou nevratné (auditovatelnost); omyl se řeší novou rezervací.
    - **Ukazatel spolehlivosti:** nenápadná barevná tečka u jména pacienta (evidence, karta pacienta, detail rezervace, výběr pacienta při rezervaci), podrobnosti až v tooltipu po najetí myší / ťuknutí (např. „Za posledních 12 měsíců: zrušeno 3×, nedostavil(a) se 2× (z toho 1× zrušeno méně než 24 h předem)“).
    - Skóre = počet zrušení pacientem + nedostavení za **posuvných 12 měsíců** (podle data termínu), obě události mají stejnou váhu. Prahy: **0–1 zelená, 2–3 žlutá, 4+ červená** (červená má navíc symbol „!“, aby nebyla rozlišitelná jen barvou). **Pozdní zrušení** (< 24 h před termínem) se jen eviduje a zobrazí v tooltipu, na barvu vliv nemá.
  - **Proč:** Recepční musí termín zrušit během telefonátu bez hledání v dalších obrazovkách. Okno 12 měsíců odpovídá zadání („letos pětkrát“) a frekvenci pravidelných kontrol (2–4× ročně) – za 6 měsíců by se data téměř nenasbírala. Ukazatel je záměrně jen orientační, bez velké statistiky. Uložený čas zrušení umožní později pozdní zrušení vážit bez změny schématu.
  - **Dopad na architekturu:**
    - Datová vrstva: migrace `006_appointment_cancellation` (`cancelled_at`, `cancelled_by_user_id`, `cancellation_note`, index `(patient_id, status, start_at)`), repozitář `save_releasing_slots`, `list_reliability_events`.
    - Byznys vrstva: čistý modul `src/business/reliability.py` (okno, prahy, pozdní zrušení – konstanty na jednom místě), `AppointmentService.cancel_appointment` / `mark_no_show` s oprávněními, `PatientService.get_reliability` (jeden dotaz na stránku seznamu), DTO `AppointmentCancel`, seed demo zrušení (Krátká červená, Dvořák žlutý).
    - Prezentační vrstva: `POST /appointments/{id}/cancel`, `POST /appointments/{id}/no-show`, pole `reliability` v odpovědích pacienta, údaje o zrušení v detailu rezervace a historii pacienta; UI dialog zrušení, tečka s tooltipem.
    - Testy: `tests/test_cancellation.py` (uvolnění slotu a nová rezervace, oprávnění, zrušení proběhlého / dvojí zrušení, nedostavení, okno 12 měsíců, zrušení ordinací se nepočítá, seed) a `tests/test_reliability.py` (prahy, hranice okna, pozdní zrušení přes časová pásma). Celkem 121 testů.
- **2026-11-11:** **Odstranění volných poznámek (poznámka k pacientovi, poznámka ke zrušení):**
  - **Co bylo rozhodnuto:** Z aplikace se odstraňuje interní poznámka k pacientovi (`patients.notes` – sloupec a ikona 📝 v evidenci, pole ve formuláři, řádky v detailu rezervace a v kartě pacienta) i nepovinná poznámka ke zrušení rezervace (`appointments.cancellation_note` – pole v dialogu zrušení, detail rezervace, tooltip v kartě pacienta). Dialog zrušení obsahuje jen volbu *Ruší pacient* / *Ruší ordinace*. Klinická poznámka lékaře k návštěvě (FP4) zůstává beze změny.
  - **Proč:** Rozhodnutí vývojáře – rychlejší a jednodušší ovládání pro recepci a méně volného textu s potenciálně citlivými údaji (např. „alergie na penicilin“) mimo zdravotní záznam lékaře, který má řízenou viditelnost.
  - **Dopad na architekturu:** migrace `007_drop_notes` oba sloupce odstraní (downgrade je vrací prázdné; existující poznámky se upgradem smažou), úpravy `PatientModel`, `AppointmentModel`, DTO `PatientCreate/PatientUpdate`, `AppointmentCancel`, odpovědních schémat, seedu a testů. API pole `notes` a `cancellation_note` už nepřijímá ani nevrací. Ověřeno upgradem i downgradem na PostgreSQL. Celkem 121 testů.
- **2026-11-11:** **Realizace Funkčního požadavku 6 – Týdenní přehled volných termínů:**
  - **Co bylo rozhodnuto:**
    - Základ FP6 tvoří týdenní kalendář z FP3 (zvolený lékař a týden, volné / obsazené / mimo ordinační hodiny / minulost, rezervace kliknutím či tažením). Doplněno: **výpočet volných termínů v byznys vrstvě** a tlačítko **„Nejbližší volný termín“**, které přepne kalendář na týden prvního volného slotu zvoleného lékaře a slot zvýrazní.
    - Volný slot = 15min slot v ordinačních hodinách, který není obsazený (tabulka `appointment_slots` – stejný zdroj pravdy jako ochrana proti kolizím) a nezačíná v minulosti. Souvislé volné sloty se slučují do úseků, přes polední pauzu ne. Nejbližší termín se hledá od teď nejvýše **90 dní** dopředu; API umí i požadovanou délku (násobek 15 min, max. 4 h).
    - Souhrn volných hodin u jednotlivých dnů se na přání vývojáře nezobrazuje. Jednorázová nedostupnost lékaře (nemoc, dovolená) zůstává v otevřeném bodě 5. *(Nemoc vyřešena 2026-11-13, viz záznam „Nemoc lékaře“; dovolená zatím ne.)*
  - **Proč:** Dřív volno dopočítával jen JavaScript v prohlížeči – pravidlo leželo v prezentační vrstvě, nebylo testované a API ho neposkytovalo (budoucí pacientský portál). Při plném týdnu musela recepce během telefonátu ručně listovat týdny.
  - **Dopad na architekturu:**
    - Byznys vrstva: `scheduling.free_intervals`, `scheduling.first_free_start`, `NEXT_FREE_HORIZON_DAYS`; `DoctorService.get_free_slots`, `find_next_free_slot`; kalendář vrací u každého dne `free_intervals` ze stejné funkce.
    - Datová vrstva: `AppointmentRepository.list_taken_slot_starts` (jeden dotaz na celé období).
    - Prezentační vrstva: `GET /doctors/{id}/free-slots?week_start=`, `GET /doctors/{id}/next-free-slot?minutes=`; UI určuje volné buňky podle dat ze serveru, nové tlačítko v kalendáři.
    - Testy: unit testy v `tests/test_scheduling.py` a `tests/test_free_slots.py` (ordinační hodiny, pauza, obsazení a uvolnění zrušením, minulost, přeskočení plného dne, souvislá délka, neaktivní lékař; „teď“ je v testech zafixované). Celkem 136 testů.
- **2026-11-12:** **Realizace Funkčního požadavku 7 – Měsíční výkaz pro pojišťovny:**
  - **Co bylo rozhodnuto:**
    - Nová záložka **Výkazy**: filtr *lékař + měsíc + pojišťovna* (výchozí minulý měsíc a „Všechny pojišťovny“), výkaz se po změně filtru hned zobrazí jako „papírový“ ordinační výkaz. Tlačítko **Stáhnout ▾** se rozbalí na **CSV** (pro Excel) a **PDF** (k tisku).
    - Vzhled jako běžný výkaz: hlavička s poskytovatelem, adresou a **IČZ**, lékařem, **odborností** a **IČP**; **oddíl pro každou pojišťovnu** (datum, pacient, č. pojištěnce, kód, výkon, počet, body/ks, body) s **mezisoučtem**; **souhrn podle kódů výkonů**; **celkový součet bodů**. PDF navíc číslování stran a místo pro razítko a podpis lékaře.
    - Výkaz počítá jen **uzavřené** návštěvy (`CLOSED`) s termínem v daném kalendářním měsíci; body ze **snapshotu** `points_per_unit`, takže pozdější změna číselníku výkaz nezmění. Proběhlé termíny bez záznamu nebo s rozpracovaným konceptem se do součtu nepočítají, ale výkaz na ně **nahoře upozorní** (výkaz není úplný). Zrušené termíny a nedostavení se nevykazují. Budoucí měsíc nelze zvolit, u probíhajícího měsíce výkaz upozorní, že není konečný.
    - Oprávnění: recepce a administrátor vidí výkaz libovolného lékaře, lékař jen vlastní (výběr lékaře je zamčený). Výkaz neobsahuje klinické poznámky.
    - PDF generuje knihovna **fpdf2** (čistý Python, bez systémových závislostí v Docker image) s přibaleným fontem **DejaVu Sans Condensed** kvůli české diakritice (licence `src/presentation/exports/fonts/LICENSE-DejaVu.txt`). CSV: oddělovač `;`, UTF-8 s BOM (Excel v české lokalizaci).
    - **Vědomé zjednodušení:** pojišťovna se bere z aktuální karty pacienta. Pokud pacient pojišťovnu změní, starší výkazy by se při novém vygenerování přiřadily k nové pojišťovně. Snapshot pojišťovny na návštěvě lze doplnit později bez změny API.
  - **Proč:** Odstranění ručního přepisování výkonů (celý podvečer paní Věry). Členění po pojišťovnách odpovídá praxi: každé pojišťovně se vykazuje zvlášť. Upozornění na neuzavřené návštěvy navazuje na rozhodnutí u FP4 (fronta *Návštěvy*).
  - **Dopad na architekturu:**
    - Datová vrstva: migrace `008_doctor_billing_identifiers` (`doctors.icp`, `doctors.specialty_code`, nepovinné), `VisitRepository.list_closed_for_report`, `AppointmentRepository.list_unfinished_in_period` (eager loading, bez N+1).
    - Byznys vrstva: číselník pojišťoven `src/business/insurance.py` (jediný zdroj pravdy i pro validaci pacienta), čistá logika výkazu `src/business/reports.py` (období, seskupení, mezisoučty, souhrn), `ReportService` (validace, oprávnění), údaje ordinace v konfiguraci (`PRACTICE_NAME`, `PRACTICE_ADDRESS`, `PRACTICE_ICZ`, syntetické), IČP/odbornost v DTO lékaře, seed `seed_demo_report_visits` (uzavřené návštěvy v minulém měsíci u 4 pojišťoven a jedna nezapsaná; existujícím lékařům seed doplní IČP a odbornost).
    - Prezentační vrstva: `report_router.py` (`GET /reports/monthly`, `GET /reports/monthly/export?format=csv|pdf`), exporty `src/presentation/exports/` (CSV, PDF, formátování a české skloňování), záložka *Výkazy* (stažení přes `fetch` s JWT a dočasný odkaz).
    - Testy: `tests/test_reports.py` (součty s počtem a snapshotem, jen uzavřené, upozornění, hranice měsíce, jiný lékař, filtr pojišťovny, validace, oprávnění, CSV, PDF) a `tests/test_report_logic.py` (unit testy logiky, formátování, validace IČP, idempotence seedu). Ověřeno i upgradem a downgradem migrace na PostgreSQL. Celkem 175 testů.
- **2026-11-13:** **Jiné pracoviště v ordinačních hodinách a přejmenování záložky:**
  - **Co bylo rozhodnuto:**
    - Blok týdenních ordinačních hodin má typ **Ordinace** (lze objednat) nebo **Jiné pracoviště** (lékař v tu dobu pravidelně ordinuje jinde, objednat nelze). U jiného pracoviště je **povinné krátké místo** (max. 100 znaků, např. „Poliklinika Jih“). V editoru hodin je to malý výběr u každého bloku, pole „Kde“ se ukáže až po volbě „Jiné pracoviště“.
    - Zobrazení **oranžovou/jantarovou** barvou (běžné hodiny modře, obsazeno červeně): pilulka s místem na kartě lékaře (součet „+ X h jinde“), v kalendáři rezervací šrafované buňky se štítkem „Jiné pracoviště · místo“, tooltipem a položkou v legendě. Buňky nejdou vybrat.
    - Bloky stejného dne se nesmí překrývat bez ohledu na typ. Změna bloku s naplánovanou budoucí rezervací na „Jiné pracoviště“ je odmítnuta (409). Pokus o rezervaci do takového času vrátí srozumitelnou hlášku s místem.
    - Demo: MUDr. Tomáš Malý ordinuje v úterý 13:00–17:00 na jiném pracovišti (syntetické „Poliklinika Jih“).
    - Záložka a nadpis „Lékaři a ordinační hodiny“ se přejmenovaly na **„Ordinační hodiny“** (i tag v API dokumentaci). Starší záznamy changelogu zůstávají beze změny.
  - **Proč:** Zadání (FP2) výslovně uvádí lékaře, který v úterý odpoledne ordinuje na jiné adrese. Dřív se to řešilo chybějícím blokem, takže v kalendáři to vypadalo jako „neordinuje“ a recepce nevěděla, proč nejde objednat, ani kde lékař je. Povinné místo odpovídá přání vývojáře. Je to krátký údaj o pracovišti, ne volná poznámka s citlivými daty.
  - **Dopad na architekturu:**
    - Datová vrstva: migrace `009_office_hours_kind` (`office_hours.kind` s výchozí hodnotou `OFFICE`, `office_hours.location`, CHECK omezení „jiné pracoviště musí mít místo“). Migrace v existující databázi doplní demo blok Malému, jen když úterní odpoledne nekoliduje s jiným blokem. Downgrade bloky jiného pracoviště smaže (jinak by byly rezervovatelné). Enum `OfficeHoursKind`.
    - Byznys vrstva: `blocks_by_weekday` vrací jen rezervovatelné bloky, takže rezervace, volné termíny, nejbližší volný termín i kontrola „osiřelých“ rezervací s jiným pracovištěm automaticky nepočítají. Nová `away_blocks_by_weekday`, validace DTO `OfficeHoursBlock` (`kind`, `location`), specifická hláška v `AppointmentService`.
    - Prezentační vrstva: `CalendarDay.away_blocks`, `office_hours[].kind/location` v odpovědi lékaře. API je zpětně kompatibilní: blok bez `kind` je ordinace.
    - Testy: `tests/test_away_hours.py` (seed, uložení, povinné místo, překryv, 409 při změně s rezervací, kalendář bez volna, odmítnutá rezervace se zmínkou o místě, nejbližší volný termín, DTO). Celkem 184 testů.
- **2026-11-13:** **Nemoc lékaře – otevřený bod 5 schválen a realizován:**
  - **Co bylo rozhodnuto:**
    - Nemoc se zadává po **celých dnech** v **mini kalendáři** (měsíční mřížka) přímo na kartě lékaře v záložce *Ordinační hodiny*. Kalendář je ve výchozím stavu sbalený a rozbalí se šipkou u nadpisu „Nemoc“; období nemoci je vidět i sbalené v odznaku v hlavičce karty. Kliknutí nebo tažení od neoznačeného dne nemoc přidá, od označeného ji zruší. Před uložením dialog ukáže **náhled dopadu** (kolik rezervací a pacientů). Smí administrátor nebo lékař, kterému karta patří; recepce kalendář nemoci jen vidí. Minulé dny nelze měnit, jedna operace pokryje nejvýše 92 dní.
    - Nové stavy rezervace **`TO_RESCHEDULE`** (K přeobjednání, v dřívějším návrhu `K_PREOBJEDNANI`) a **`RESCHEDULED`** (Přeobjednáno). Označení dne přesune naplánované, ještě nezačaté termíny do `TO_RESCHEDULE`. Jejich sloty zůstávají obsazené. Odznačení dne (dřívější uzdravení) je automaticky vrátí do `PLANNED`.
    - V nemocný den se nedá objednat (srozumitelná hláška), volné termíny ani „Nejbližší volný termín“ s ním nepočítají.
    - Záložka *Rezervace* má podzáložky **Kalendář** a **K přeobjednání** (počet čekajících je i v odznaku na záložce). Fronta je seskupená po původních dnech a ukazuje pacienta s ukazatelem spolehlivosti, telefon, původního lékaře a čas. Vidí ji recepce a administrátor.
    - **Přeobjednat** přepne kalendář do režimu přeobjednání: výchozí je jiný aktivní lékař (lze změnit i na téhož lékaře v jiný den), předvybere se délka původního termínu, pacient i důvod se převezmou. V jedné transakci vznikne nová rezervace (platí všechna pravidla rezervace) a původní přejde do `RESCHEDULED` s odkazem na novou a uvolní sloty. **Zrušit termín** z fronty je zrušení ordinací (jde i po uplynutí původního času).
    - Kalendář: nemocný den je **růžově šrafovaný** se štítkem „Nemoc lékaře“ (fialovou má v kalendáři MUDr. Veselá jako barvu lékaře, proto růžová). Termíny K přeobjednání mají **přerušovaný růžový okraj** a značku 📞. Obojí je v legendě.
    - Demo: MUDr. Veselá je příští středu a čtvrtek nemocná, dva její středeční termíny čekají ve frontě (seed jednou na databázi).
  - **Proč:** Dnes recepce při nemoci lékaře ručně prochází diář a pacienty obvolává jednoho po druhém (kap. 1). Fronta jí dá hotový seznam s telefony a přesun ke kolegovi na pár kliknutí. Ponechání slotů obsazených znamená, že termín během obvolávání nikdo nepřebere a dřívější uzdravení jde vrátit bez rizika. Celé dny odpovídají neschopence a jsou pro ovládání nejjednodušší. Přeobjednání i zrušení kvůli nemoci se do spolehlivosti pacienta nepočítají.
  - **Dopad na architekturu:**
    - Datová vrstva: migrace `010_doctor_sick_days` (tabulka `doctor_sick_days` s `UNIQUE(doctor_id, day)`, nové hodnoty enumu `appointmentstatus`, sloupec `appointments.rescheduled_to_id`). Downgrade vrací `TO_RESCHEDULE` → `PLANNED`, `RESCHEDULED` → `CANCELLED_BY_OFFICE` a znovu vytvoří enum bez nových hodnot. Ověřeno upgradem i downgradem na PostgreSQL. Model `DoctorSickDayModel`, metody repozitářů (nemocné dny, fronta, transakční `reschedule`). `ACTIVE_STATUSES` zahrnuje i `TO_RESCHEDULE` (nadcházející termíny pacienta, kontrola „osiřelých“ rezervací při změně hodin), kalendář má vlastní `CALENDAR_STATUSES`; fronta návštěv a výkazy se nemění.
    - Byznys vrstva: čistý modul `src/business/sick_days.py` (rozsah dnů, validace, slučování do období), `DoctorService.get_sick_days / preview_sick_change / set_sick_days`, volno a kalendář bez nemocných dnů, `AppointmentService.reschedule_appointment / list_reschedule_queue / count_reschedule_queue`, společná validace nového termínu, zrušení i z `TO_RESCHEDULE`, DTO `SickDaysChange`, `AppointmentReschedule`, seed `seed_demo_sickness`.
    - Prezentační vrstva: `GET /doctors/{id}/sick-days`, `GET /doctors/{id}/sick-days/preview`, `PUT /doctors/{id}/sick-days`, `GET /appointments/reschedule-queue`, `GET /appointments/reschedule-queue/count`, `POST /appointments/{id}/reschedule`. `CalendarDay.sick`, v detailu rezervace `rescheduled_to_id` a `rescheduled_to_term`. UI: mini kalendář s dialogem, podzáložky Rezervace, fronta, režim přeobjednání, nové stavy v detailu rezervace, nadcházejících rezervacích a kartě pacienta.
    - Testy: `tests/test_sick_days.py` (oprávnění, minulost, přesun do fronty se zachováním slotů, nezačaté vs. probíhající termíny, návrat po odznačení, zákaz rezervace, volno a kalendář, náhled, fronta a počty, přeobjednání ke kolegovi i témuž lékaři, kolize a pravidla, zrušení z fronty, spolehlivost, idempotence seedu, čistá logika). Celkem 207 testů.
