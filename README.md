# Digital twin voor longkanker

Dit onderwijsproject toont CT-metingen, voorspellingen van tumorgrootte en een fictief behandelplan per patiënt. De patiëntgegevens, behandelregels en behandelingseffecten zijn verzonnen voor het testen van de software. De uitkomsten zijn geen gevalideerd behandeladvies.

## Website starten

Open een terminal in deze repository:

```powershell
cd "C:\Users\20241772\OneDrive - TU Eindhoven\Documents\digital-twin-in-healthcare-1"
```

Installeer bij het eerste gebruik de omgeving met Pixi:

```powershell
pixi install
```

Start daarna de backend en website samen:

```powershell
pixi run backend
```

Open http://127.0.0.1:8000 in de browser. Laat de terminal open; stoppen kan met Ctrl+C. Een aparte frontendserver is hiervoor niet nodig.

## Gebruik

- Zoek een patiënt op naam, een uniek deel van de naam of patiënt-ID. De fictieve patiënten zijn Noor, Milan, Sara en Daan.
- Kies scan 1, 2, 3 of 4. Dit zijn de posities in de lijst `ct_scans`; de dagen staan in het patiëntbestand en kunnen per patiënt verschillen.
- De voorspelling gebruikt alleen metingen tot en met de gekozen scan.
- Bekijk de gemeten tumorgrootte, basisvoorspelling met onzekerheidsband, fictieve behandelcurve en eerdere voorspellingen. De maat is SLD in millimeters: de som van de gemeten diameters.
- Onder de grafiek staan het gekozen behandelplan, scores en uitleg over de behandelregels.
- Bij opslaan geldt de keuze om oude uitvoer te verwijderen alleen voor de geselecteerde patiënt.

Bij verwijderen wordt het bestaande uitvoerbestand van die patiënt vervangen door de nieuwe berekening. Bij behouden komen oudere berekeningen in `run_history`. Een nieuwe berekening kan zelf ook eerdere scans en voorspellingen bevatten; die horen bij de nieuwe uitvoer en verdwijnen daardoor niet met de oude opslaghistorie.

De uitvoer wordt aangemaakt in `backend/Algoritme_met_model/voorspellingen_output/`, met een bestand per naam en patiënt-ID, bijvoorbeeld `voorspellingen_output_Noor_DEMO-001.json`.

## Welke bestanden doen wat?

| Bestand of map | Functie |
| --- | --- |
| `frontend/index.html` en `Style.css` | Inhoud en vormgeving van de website. |
| `frontend/Script.js` | Patiënt zoeken en resultaten ophalen. |
| `frontend/Graph.js` | Grafiek tekenen. |
| `frontend/Integration.js` | Scanselectie, behandelresultaten en opslaan koppelen aan de pagina. |
| `backend/app/main.py` | FastAPI starten, API-routes registreren en de frontend aanbieden. Dit gebruikt `pixi run backend`. |
| `backend/app/api/predictions.py` | HTTP-aanvragen voor patiënten, voorspellingen en opslaan afhandelen. |
| `backend/app/models/prediction.py` | Structuur en validatie van API-invoer. |
| `backend/app/services/predictions.py` | De API verbinden met het voorspel- en behandelmodel. |
| `backend/Algoritme_met_model/fake_patients.json` | Fictieve patiëntgegevens, CT-metingen en behandelgeschiedenis. |
| `backend/Algoritme_met_model/run_voorspelling.py` | Patiënt en scan selecteren, berekeningen aanroepen en uitvoer opslaan; ook via de terminal te gebruiken. |
| `backend/Algoritme_met_model/twinning.py` | Bi-exponentieel voorspelmodel voor SLD met onzekerheid. Dit is momenteel geen Gompertz-model. |
| `backend/Algoritme_met_model/MPC.py` | Voorspellingen koppelen aan fictieve behandelopties en hun kosten vergelijken. |
| `backend/Algoritme_met_model/demo_treatment_rules.py` | Opdrachtregels voor behandelvolgorde; gewichten voor geslacht (2) en roken (1). |
| `backend/Algoritme_met_model/adaptive_curve.py` | De behandelcurve over opeenvolgende scans opbouwen. |
| `backend/tests/` | Automatische tests voor de backend. |
| `pixi.toml` en `pixi.lock` | Omgeving, dependencies en startcommando's. |

De website roept de Pythonbestanden niet rechtstreeks aan. De volgorde is:

```text
Browser -> FastAPI -> predictions-service -> run_voorspelling / MPC
                                                    -> twinning.predict
                                                    -> behandelregels
                    <- JSON-resultaten <- berekening
Browser toont grafiek en behandelresultaten
```

Je hoeft deze bestanden dus niet afzonderlijk na elkaar te starten.

## Model en kostenfunctie

`twinning.py` past de bi-exponentiële curve aan de beschikbare CT-metingen aan en levert voorspellingen met onzekerheid. `MPC.py` vergelijkt een beperkte verzameling behandelvolgordes met fictieve effecten voor chemo en operatie. De kostenfunctie telt relatieve tumorgrootte, fictieve toxiciteit en regelstraffen bij elkaar op. Het zijn modelkosten, geen geldbedragen.

Na selectie van een latere CT-scan wordt opnieuw gerekend. Dit is een beperkte MPC-demo (Model Predictive Control). Geslacht en roken bepalen de zelfgekozen opdrachtregels; deze regels zijn niet medisch onderbouwd. Veel overige patiëntvariabelen worden wel opgeslagen en getoond, maar beïnvloeden de berekening momenteel niet. De geregistreerde behandelgeschiedenis wordt nog niet gebruikt om behandelingseffecten te schatten.

## Voorspellen vanuit de terminal

Vanuit de hoofdmap, bijvoorbeeld voor Noor bij scan 2:

```powershell
pixi run python backend/Algoritme_met_model/run_voorspelling.py Noor 2
```

Op patiënt-ID kan ook:

```powershell
pixi run python backend/Algoritme_met_model/run_voorspelling.py DEMO-001 2
```

Dit gebruikt dezelfde berekenfuncties als de website. De terminal vraagt of oude uitvoer van die patiënt mag worden vervangen.

## API en tests

Bij de FastAPI-server staat interactieve API-documentatie op http://127.0.0.1:8000/docs.

Belangrijke routes:

- `GET /api/tumor/patients`: patiënten ophalen.
- `GET /api/tumor/predict/DEMO-001?scan=2`: voorspelling voor een patiënt en scan.
- `POST /api/predict`: voorspelling via een JSON-aanvraag.
- `POST /api/save`: uitvoer voor de geselecteerde patiënt opslaan.

Tests uitvoeren:

```powershell
pixi run test
```

## Frontendontwikkeling

Voor afzonderlijke frontendontwikkeling kan naast de FastAPI-server een Vite-server worden gestart:

```powershell
pixi run frontend-install
pixi run frontend
```

Open dan het adres dat Vite in de terminal toont. `frontend/vite.config.ts` stuurt `/api`-aanvragen door naar de backend op poort 8000. Dit is optioneel voor het normale gebruik van de website.

## Overgebleven dependency uit het oorspronkelijke template

**Lit** staat nog als dependency in `frontend/package.json` en het npm-lockbestand. Het is een JavaScriptbibliotheek voor webcomponenten. De huidige frontend gebruikt gewone HTML en JavaScript en gebruikt Lit niet meer.

De alternatieve `backend/server.py` en de oude BMI-route, BMI-code en BMI-tests zijn verwijderd. De toepassing gebruikt de oorspronkelijke startmethode: `pixi run backend` start FastAPI via `backend/app/main.py` en biedt de website en voorspel-API aan.