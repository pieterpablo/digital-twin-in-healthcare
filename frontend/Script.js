// ============================================================
// DATA
// Dit zijn vaste voorbeeldgegevens. Later komt dit uit de
// database en uit het rekenmodel voor de behandelplannen.
// Het scherm hieronder laat alleen zien wat er in deze data staat.
// ============================================================

// Gegevens van de patiënt 
const patient = {
  naam: "Pépé van Dijk (voorbeeldpatiënt)",
  leeftijd: 21,
  geslacht: "M",
  stadium: "IIIA",
  egfr: "Positief",
  pdl1: "15%",
  who: "WHO 1",
  roken: "Geen roker"
};

// Het behandelplan in volgorde
const plan = [
  {
    naam: "Chemotherapie",
    weken: "week 0 t/m 7",
    reden: "Lokaal gevorderd ziektestadium en goede conditie."
  },
  {
    naam: "EGFR-TKI (osimertinib(?))",
    weken: "vanaf week 8",
    reden: "EGFR-mutatie aanwezig, dus doelgerichte therapie."
  }
];

// De x-as van de grafiek: om de 6 weken een punt
const weken = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72];

// Verwachte tumorgrootte in mm per week
const aanbevolen = [67, 34, 29, 26, 23, 20, 18, 16.5, 15.5, 16, 17, 19, 21];
const alternatief = [67, 34, 31, 32, 33, 35, 37, 40, 43, 46, 49, 52, 55];

// Gemeten waarden uit CT-scans. null = nog geen meting in die week
const gemeten = [67, null, 30, null, 24, null, null, null, null, null, null, null, null];


// ============================================================
// DE PAGINA VULLEN
// Hieronder staat geen berekening meer, alleen tekst en tabellen maken.
// ============================================================

// Patiëntinfo bovenaan
document.getElementById("patientinfo").textContent =
  patient.naam + " (" + patient.geslacht + ", " + patient.leeftijd + " jaar) - stadium " + patient.stadium;

// Behandelplan: voor elke stap in 'plan' maken we een <li> in de lijst
const planLijst = document.getElementById("plan");
for (const stap of plan) {
  const li = document.createElement("li");
  li.innerHTML =
    "<strong>" + stap.naam + "</strong> " +
    "<span class='weken'>(" + stap.weken + ")</span>" +
    "<span class='reden'>" + stap.reden + "</span>";
  planLijst.appendChild(li);
}

// Tabel met de gebruikte patiëntgegevens
// Elke rij is: [kenmerk, waarde, waarvoor het gebruikt wordt]
const gegevens = [
    ["Leeftijd", patient.leeftijd, "Bepaalt fitheid van de patiënt"],
    ["Geslacht", patient.geslacht, "Geslacht heeft invloed op bepaalde behandelingen"],
  ["Ziektestadium", patient.stadium, "Bepaalt dat chemoradiotherapie de basis is"],
  ["EGFR-mutatie", patient.egfr, "Bepaalt of een EGFR-TKI kan"],
  ["PD-L1-expressie", patient.pdl1, "Bepaalt of immunotherapie zin heeft"],
  ["Algemene conditie", patient.who, "Bepaalt of de patiënt de behandeling aankan"],
  ["Rookgeschiedenis", patient.roken, "Weegt mee bij bijwerkingen"]
];

const tabel = document.getElementById("gegevens");
tabel.innerHTML = "<tr><th>Kenmerk</th><th>Waarde</th><th>Waarvoor gebruikt</th></tr>";
for (const rij of gegevens) {
  tabel.innerHTML +=
    "<tr><td>" + rij[0] + "</td><td>" + rij[1] + "</td><td>" + rij[2] + "</td></tr>";
}


// ============================================================
// DE LIJNGRAFIEK TEKENEN (met Chart.js)
// ============================================================
new Chart(document.getElementById("grafiek"), {
  type: "line",
  data: {
    labels: weken,
    datasets: [
      {
        label: "Aanbevolen plan",
        data: aanbevolen,
        borderColor: "#16a931",
        backgroundColor: "white",  
        pointRadius: 2
      },
      {
        label: "Alleen chemotherapie",
        data: alternatief,
        borderColor: "#75160c",  
        backgroundColor: "white",
        pointRadius: 2
      },
      {
        label: "Gemeten door middel van CT-scans",
        data: gemeten,
        borderColor: "#000000",
        backgroundColor: "white",
        showLine: false,         
        pointRadius: 6
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,   // gebruik de hoogte van .grafiek-box
    interaction: { mode: "index", intersect: false },   // tooltip toont alle lijnen in die week
    scales: {
      x: { title: { display: true, text: "Tijd (Weken)" } },
      y: { title: { display: true, text: "Tumorgrootte (mm)" }, min: 0 }
    }
  }
});