
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

async function start() {
  try {
    const data = await loadPatient("DEMO-001");

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
    alert(
      "Kon de Digital Twin niet laden: " +
      error.message
    );
  }
}

start();
