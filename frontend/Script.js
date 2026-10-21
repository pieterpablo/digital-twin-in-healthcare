
const API = "http://localhost:8000/api/tumor";

async function loadPatient(patientId) {
  const response = await fetch(
    `${API}/predict/${encodeURIComponent(patientId)}`
  );

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return await response.json();
}

// Laat de gegevens van één patiënt op de pagina zien.
async function toonPatient(patientId) {
  try {
    const data = await loadPatient(patientId);

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

    // LIJN 1: gemeten tumorverloop.
    // Deze lijn stopt bij de laatste CT-scan.
    const measuredPoints = measurements.map(
      ([day, sld]) => ({
        x: toWeek(day),
        y: sld
      })
    );

    // LIJN 2: adaptieve fictieve MPC-simulatie.
    // Deze begint bij de eerste CT-scan en
    // wordt na iedere CT opnieuw geoptimaliseerd.
    const rawSimulation = Array.isArray(
      forecast.full_treatment_trajectory
    )
      ? forecast.full_treatment_trajectory
      : [];

    const simulatedPoints = rawSimulation
      .map(point => ({
        x: toWeek(Number(point.day)),
        y: Number(point.sld_mm)
      }))
      .filter(point =>
        Number.isFinite(point.x) &&
        Number.isFinite(point.y)
      )
      .sort((a, b) => a.x - b.x);

    // Controleer of de backend de MPC-curve levert.
    if (simulatedPoints.length === 0) {
      throw new Error(
        "De backend levert nog geen " +
        "full_treatment_trajectory. " +
        "Controleer MPC.py en tumor.py."
      );
    }

    // Patiëntinformatie.
    const patientInfo =
      document.getElementById("patientinfo");

    if (patientInfo) {
      patientInfo.textContent =
        `${data.name} - stadium ${data.variables.tumor_stage}`;
    }

    // Maak het resultaat zichtbaar (Chart.js heeft een zichtbaar vak nodig om te tekenen).
    document.getElementById("resultaat").hidden = false;

    // Bestaande grafiek vervangen indien nodig.
    const canvas = document.getElementById("grafiek");

    if (!canvas) {
      throw new Error("Grafiekelement niet gevonden");
    }

    const oldChart = Chart.getChart(canvas);

    if (oldChart) {
      oldChart.destroy();
    }

    // Precies twee lijnen.
    new Chart(canvas, {
      type: "line",

      data: {
        datasets: [
          {
            label: "Gemeten tumorverloop (CT-scans)",
            data: measuredPoints,

            borderColor: "#222222",
            backgroundColor: "#222222",

            borderWidth: 3,
            pointRadius: 5,
            pointHoverRadius: 7,

            showLine: true,
            tension: 0,

            spanGaps: false
          },
          {
            label: "Voorspeld tumorverloop met MPC-behandeling",
            data: simulatedPoints,

            borderColor: "#16a34a",
            backgroundColor: "#16a34a",

            borderWidth: 3,
            pointRadius: 0,
            pointHoverRadius: 5,

            showLine: true,
            tension: 0,

            spanGaps: false
          }
        ]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,
        parsing: false,

        interaction: {
          mode: "nearest",
          intersect: false
        },

        scales: {
          x: {
            type: "linear",
            min: 0,

            title: {
              display: true,
              text: "Tijd (weken)"
            }
          },

          y: {
            min: 0,

            title: {
              display: true,
              text: "Tumorgrootte SLD (mm)"
            }
          }
        },

        plugins: {
          legend: {
            display: true,
            position: "top"
          },

          tooltip: {
            callbacks: {
              title: items => {
                if (!items.length) return "";

                return (
                  "Week " +
                  Number(items[0].parsed.x).toFixed(1)
                );
              },

              label: context => {
                return (
                  context.dataset.label +
                  ": " +
                  Number(context.parsed.y).toFixed(1) +
                  " mm"
                );
              }
            }
          }
        }
      }
    });

    // Toon het actuele fictieve behandelplan.
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

    // Patiëntgegevens.
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

    console.log("Digital Twin geladen:", data);
    console.log("Laatste CT-dag:", lastDay);
    console.log("CT-metingen:", measuredPoints);
    console.log("Adaptieve MPC-curve:", simulatedPoints);

  } catch (error) {
    console.error("Digital Twin error:", error);
    zetMelding(
      "Kon de Digital Twin niet laden: " + error.message,
      true
    );
  }
}


// ============================================================
// ZOEKEN OP NAAM
// ============================================================

// Hier onthouden we de lijst met patiënten: [{ id: "DEMO-001", name: "Noor" }, ...]
let patienten = [];

// Tekst onder de zoekbalk. fout = true maakt de tekst rood.
function zetMelding(tekst, fout = false) {
  const melding = document.getElementById("zoekmelding");
  melding.textContent = tekst;
  melding.classList.toggle("fout", fout);
}

// Haal de lijst met patiënten op bij de backend en vul de suggesties in de zoekbalk.
async function laadPatientenlijst() {
  const response = await fetch(`${API}/patients`);

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  patienten = await response.json();

  const suggesties = document.getElementById("patientnamen");
  suggesties.replaceChildren();

  for (const patient of patienten) {
    const optie = document.createElement("option");
    optie.value = patient.name;
    optie.label = patient.id;
    suggesties.appendChild(optie);
  }
}

// Zoek in de lijst: eerst een precieze naam (of ID), anders een deel van de naam.
// Geeft { patient } als er precies één gevonden is, anders { melding }.
function zoekPatient(invoer) {
  const zoekterm = invoer.trim().toLowerCase();

  if (zoekterm === "") {
    return { melding: "Vul een naam in om het behandeloverzicht te zien." };
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

// Wat er gebeurt als je op "Zoek" klikt of Enter drukt.
async function zoekEnToon(event) {
  event.preventDefault();

  const resultaat = zoekPatient(document.getElementById("zoekveld").value);

  if (!resultaat.patient) {
    // Niets (of meerdere) gevonden: verberg de vorige patiënt, zodat je niet de verkeerde gegevens ziet.
    document.getElementById("resultaat").hidden = true;
    document.getElementById("patientinfo").textContent = "";
    zetMelding(resultaat.melding, true);
    return;
  }

  zetMelding(`Gegevens van ${resultaat.patient.name} (${resultaat.patient.id}) worden geladen...`);
  await toonPatient(resultaat.patient.id);

  // Als het laden gelukt is, staat er geen foutmelding. Dan tonen we de naam netjes.
  if (!document.getElementById("zoekmelding").classList.contains("fout")) {
    zetMelding(`Je bekijkt: ${resultaat.patient.name} (${resultaat.patient.id})`);
  }
}

async function start() {
  document.getElementById("zoekformulier")
    .addEventListener("submit", zoekEnToon);

  try {
    await laadPatientenlijst();
  } catch (error) {
    console.error("Patiëntenlijst laden mislukt:", error);
    zetMelding(
      "Geen verbinding met de backend. Draait 'pixi run backend'? (" + error.message + ")",
      true
    );
  }
}

start();
