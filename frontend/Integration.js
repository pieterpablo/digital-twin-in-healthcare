function fillTable(id, headings, rows) {
  const table = document.getElementById(id);
  table.replaceChildren();
  const header = document.createElement('tr');
  for (const label of headings) {
    const th = document.createElement('th');
    th.textContent = label;
    header.appendChild(th);
  }
  table.appendChild(header);
  for (const values of rows) {
    const row = document.createElement('tr');
    for (const value of values) {
      const td = document.createElement('td');
      td.textContent = value ?? '—';
      row.appendChild(td);
    }
    table.appendChild(row);
  }
}

document.addEventListener('patient-loaded', event => {
  const data = event.detail;
  const latest = data.latest_forecast;
  const optimization = latest.treatment_optimization;
  const scanSelect = document.getElementById('scan-select');
  scanSelect.replaceChildren();
  for (const scan of data.available_scans) {
    scanSelect.add(new Option(`Scan ${scan.scan_number} — dag ${scan.day}`, scan.scan_number));
  }
  scanSelect.value = String(latest.scan_number);
  document.getElementById('status').textContent = `Scan ${latest.scan_number} berekend; nog niet opgeslagen.`;
  document.getElementById('save-status').textContent = '';
  document.getElementById('save').disabled = false;
  document.getElementById('score').textContent = optimization.score === null ? '' :
    `Modelscore: ${optimization.score.toFixed(3)}. Fictieve behandelingseffecten.`;
  const reports = [...data.forecast_history, latest];
  fillTable('scan-history', ['Scan', 'Dag', 'SLD (mm)', 'Demo-plan', 'Verloop'], reports.map(report => {
    const scan = report.measurements.at(-1);
    return [report.scan_number, scan.day, scan.sld_mm,
      (report.treatment_optimization.plan || []).join(' → '), report.progress.message];
  }));
  fillTable('alternatives', ['Volgorde', 'Score', 'Beoordeling'], optimization.candidates.map(candidate => [
    candidate.plan.join(' → '), candidate.score?.toFixed(3), candidate.status === 'excluded' ?
    candidate.reasons.join(' ') : candidate.plan.join() === optimization.plan?.join() ? 'Gekozen demo-plan' : 'Toegestaan alternatief'
  ]));
});

document.getElementById('scan-select').addEventListener('change', () => {
  document.getElementById('save').disabled = true;
  document.getElementById('status').textContent = 'Scankeuze gewijzigd; klik op Bereken voorspelling.';
});

document.getElementById('calculate').addEventListener('click', async () => {
  if (!currentPatient) return;
  const patientId = currentPatient;
  const scan = Number(document.getElementById('scan-select').value);
  zetMelding('Nieuwe scanvoorspelling laden…');
  if (await toonPatient(patientId, scan)) {
    zetMelding("");
    updateSidenav(true);
  }
});

document.getElementById('save').addEventListener('click', async () => {
  if (!currentPatient || !currentData) return;
  const request = {patient_id: currentPatient, scan_number: currentData.latest_forecast.scan_number,
    clear_old: document.getElementById('clear-old').value === 'yes'};
  const button = document.getElementById('save');
  const message = document.getElementById('save-status');
  button.disabled = true;
  message.textContent = 'Opslaan…';
  try {
    const response = await fetch('/api/save', {method: 'POST',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify(request)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Opslaan mislukt');
    message.textContent = `Opgeslagen: ${result.filename}. ` +
      (result.clear_old ? 'Oude uitvoer van deze patiënt vervangen.' : 'Historie van deze patiënt bewaard.');
  } catch (error) {
    message.textContent = error.message;
  } finally {
    if (currentPatient === request.patient_id &&
        Number(document.getElementById('scan-select').value) === request.scan_number) button.disabled = false;
  }
});
