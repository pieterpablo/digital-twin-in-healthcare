const API = "/api/tumor";
let loadVersion = 0;
let currentPatient = null;
let currentData = null;

async function loadPatient(patientId, scanNumber = null) {
  const response = await fetch(
    `${API}/predict/${encodeURIComponent(patientId)}${scanNumber === null ? "" : "?scan=" + scanNumber}`
  );

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return await response.json();
}

// Laat de gegevens van één patiënt op de pagina zien
async function toonPatient(patientId, scanNumber = null) {
  const version = ++loadVersion;
  document.getElementById("resultaat").hidden = true;
  document.getElementById("save").disabled = true;
  currentPatient = null;
  try {
    const data = await loadPatient(patientId, scanNumber);
    if (version !== loadVersion) return false;

    const forecast = data.latest_forecast;

    if (!forecast) {
      throw new Error("Geen voorspelling ontvangen");
    }

    const optimization =
      forecast.treatment_optimization || {};

    const history = Array.isArray(data.forecast_history)
      ? data.forecast_history
      : [];

    // Verzamel alle CT-scans.
    const allMeasurements = new Map();

    [...history, forecast].forEach(report => {
      (report.measurements || []).forEach(point => {
        allMeasurements.set(
          Number(point.day),
          Number(point.sld_mm)
        );
      });
    });

    const measurements = [...allMeasurements.entries()]
      .sort((a, b) => a[0] - b[0]);

    if (measurements.length === 0) {
      throw new Error("Geen CT-metingen gevonden");
    }

    const firstDay = measurements[0][0];
    const lastDay = measurements.at(-1)[0];

    const toWeek = day => (day - firstDay) / 7;

    // Patiëntinformatie.
    const patientInfo =
      document.getElementById("patientinfo");

    if (patientInfo) {
      patientInfo.textContent =
        `${data.name} - stadium ${data.variables.tumor_stage}`;
    }

    // Maak het resultaat zichtbaar (Chart.js heeft een zichtbaar vak nodig om te tekenen).
    document.getElementById("resultaat").hidden = false;

   
    drawChart({
      scans: measurements.map(([day, sld]) => ({day, sld_mm: sld})),
      latest_forecast: {
        trajectory: forecast.trajectory,
        treatment_trajectory: optimization.trajectory || []
      },
      previous_forecasts: history
    });

    // Toon het actuele fictieve behandelplan
    const planElement = document.getElementById("plan");

    if (planElement) {
      planElement.replaceChildren();

      const plan = optimization.plan || [];

      for (const treatment of plan) {
        const li = document.createElement("li");
        li.textContent = treatment;
        planElement.appendChild(li);
      }
    }

    // Patiëntgegevens
    const table = document.getElementById("gegevens");

    if (table) {
      table.replaceChildren();

      const header = document.createElement("tr");

      for (const label of ["Kenmerk", "Waarde"]) {
        const th = document.createElement("th");
        th.textContent = label;
        header.appendChild(th);
      }

      table.appendChild(header);

      for (const [key, value] of Object.entries(data.variables)) {
        const row = document.createElement("tr");

        for (const cellValue of [key, value]) {
          const td = document.createElement("td");
          td.textContent = String(cellValue);
          row.appendChild(td);
        }

        table.appendChild(row);
      }
    }

    currentPatient = patientId;
    currentData = data;
    document.dispatchEvent(new CustomEvent("patient-loaded", {detail: data}));
    console.log("Digital Twin geladen:", data);
    console.log("Laatste CT-dag:", lastDay);
    console.log("CT-metingen:", measurements);

    return true;

  } catch (error) {
    if (version !== loadVersion) return false;
    document.getElementById("resultaat").hidden = true;
    document.getElementById("patientinfo").textContent = "";
    currentPatient = null;
    currentData = null;
    console.error("Digital Twin error:", error);
    zetMelding(
      "Kon de Digital Twin niet laden: " + error.message,
      true
    );
    updateSidenav(false);
    return false;
  }
}

function resetPatientPagina() {
  loadVersion++;
  currentPatient = null;
  currentData = null;
  updateSidenav(false);
  // Verberg de patiëntresultaten
  document.getElementById("resultaat").hidden = true;

  // Verwijder de informatie van de vorige patiënt
  document.getElementById("patientinfo").textContent = "";

  // Maak de zoekbalk leeg
  document.getElementById("zoekveld").value = "";

  // Herstel de beginmelding
  zetMelding("");

  // Zet de cursor terug in de zoekbalk
  document.getElementById("zoekveld").focus();
}

// Dit laadt de sidemenu als je een patient hebt gezocht
function updateSidenav(patientSelected) {
  const sidenav = document.getElementById("sidenav");
  sidenav.replaceChildren();
  const items = patientSelected
  ? [
    { label: "Patiënt zoeken", page: "" },
    { label: "Overzicht", page: "" },
    { label: "Afspraken en acties", page: "" },
    { label: "Beeldenbank", page: "" },
    { label: "Chemohistorie", page: "" },
    { label: "Consultregristraties", page: "" },
    { label: "Correspondentie", page: "" },
    { label: "Diagnoses", page: "" },
    { label: "Endoscopie", page: "" },
    { label: "Kuurinformatie", page: "" },
    { label: "Laboratorium", page: "" },
    { label: "Etc", page: "" },
      ]
  : [
    {label: "Patiënt zoeken", page: "search"}
  ]

  for (const item of items) {
    const link = document.createElement("a");

    link.href = "#";
    link.textContent = item.label;
    link.dataset.page = item.page;

    sidenav.appendChild(link);
  }
}


// Hier onthouden we de lijst met patiënten
let patienten = [];

// Tekst onder de zoekbalk. fout = true maakt de tekst rood
function zetMelding(tekst, fout = false) {
  const melding = document.getElementById("zoekmelding");
  melding.textContent = tekst;
  melding.classList.toggle("fout", fout);
}

// Zoek in de lijst: eerst een precieze naam (of ID), anders een deel van de naam
// Geeft { patient } als er precies één gevonden is, anders de { melding }
function zoekPatient(invoer) {
  const zoekterm = invoer.trim().toLowerCase();

  if (zoekterm === "") {
    return { melding: "" };
  }

  const precies = patienten.filter(p =>
    p.name.toLowerCase() === zoekterm ||
    p.id.toLowerCase() === zoekterm
  );
  if (precies.length === 1) {
    return { patient: precies[0] };
  }

  const gevonden = precies.length > 1 ? precies : patienten.filter(p =>
    p.name.toLowerCase().includes(zoekterm) ||
    p.id.toLowerCase().includes(zoekterm)
  );

  if (gevonden.length === 1) {
    return { patient: gevonden[0] };
  }

  if (gevonden.length === 0) {
    return { melding: `Geen patiënt gevonden met "${invoer.trim()}".` };
  }

  const namen = gevonden.map(p => `${p.name} (${p.id})`).join(", ");
  return { melding: `Meerdere patiënten gevonden: ${namen}. Typ de volledige naam of het ID.` };
}

// 2. Haalt de patiënten op en vult de nieuwe <ul> met <li>'s
async function laadPatientenlijst() {
  const response = await fetch(`${API}/patients`);

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  patienten = await response.json();

  const suggestiesLijst = document.getElementById("patientnamen");
  suggestiesLijst.replaceChildren();

  for (const patient of patienten) {
    const li = document.createElement("li");
    li.textContent = `${patient.name} (${patient.id})`;
    
    // Als je op een suggestie klikt, vul je het veld in en sluit de lijst
    li.addEventListener("click", () => {
      document.getElementById("zoekveld").value = patient.name;
      suggestiesLijst.style.display = "none";
      document.getElementById("zoekveld").focus();
    });

    suggestiesLijst.appendChild(li);
  }
}

// Zorgt ervoor dat de dropdown opent en filtert tijdens het TYPEN
const zoekveld = document.getElementById("zoekveld");
const suggestiesLijst = document.getElementById("patientnamen");

zoekveld.addEventListener("input", (e) => {
  const waarde = e.target.value.trim().toLowerCase();
  const listItems = suggestiesLijst.getElementsByTagName("li");

  if (waarde === "") {
    suggestiesLijst.style.display = "none";
    return;
  }

  let aantalZichtbaar = 0;

  for (const li of listItems) {
    const tekst = li.textContent.toLowerCase();
    if (tekst.includes(waarde)) {
      li.style.display = "";
      aantalZichtbaar++;
    } else {
      li.style.display = "none";
    }
  }

  // Toon de lijst alleen als er resultaten zijn
  suggestiesLijst.style.display = aantalZichtbaar > 0 ? "block" : "none";
});

// Sluit de lijst als je ergens anders op de pagina klikt
document.addEventListener("click", (e) => {
  if (!e.target.closest(".zoekbalk-wrapper")) {
    suggestiesLijst.style.display = "none";
  }
});


// Wat er gebeurt als je op "Zoek" klikt of Enter drukt.
async function zoekEnToon(event) {
  event.preventDefault();

  const resultaat = zoekPatient(document.getElementById("zoekveld").value);

  if (!resultaat.patient) {
    loadVersion++;
    currentPatient = null;
    currentData = null;
    // Niets (of meerdere) gevonden: verberg de vorige patiënt, zodat je niet de verkeerde gegevens ziet.
    document.getElementById("resultaat").hidden = true;
    document.getElementById("patientinfo").textContent = "";
    zetMelding(resultaat.melding, true);
    updateSidenav(false);
    return;
  }

  zetMelding(`Gegevens van ${resultaat.patient.name} (${resultaat.patient.id}) worden geladen...`);
  const geladen = await toonPatient(resultaat.patient.id);
  if (!geladen) return;

  // Als het laden gelukt is, staat er geen foutmelding. Dan tonen we de naam.
  if (!document.getElementById("zoekmelding").classList.contains("fout")) {
    zetMelding("");
  }
  updateSidenav(true);
}

async function start() {
  document.getElementById("zoekformulier")
    .addEventListener("submit", zoekEnToon);
  
  // Delegatie: het menu wordt na patiëntselectie opnieuw opgebouwd.
  document.getElementById("sidenav").addEventListener("click", function(event) {
    if (event.target.closest("a")?.textContent !== "Patiënt zoeken") return;
    event.preventDefault();
    resetPatientPagina();
  });

  try {
    await laadPatientenlijst();
  } catch (error) {
    console.error("Patiëntenlijst laden mislukt:", error);
    zetMelding("Patiëntenlijst laden mislukt: " + error.message, true);
  }
}

start();
