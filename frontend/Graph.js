function svgElement(type, attributes, text) {
  const element = document.createElementNS('http://www.w3.org/2000/svg', type);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  if (text !== undefined) element.textContent = text;
  return element;
}

function drawChart(result) {
  const svg = document.getElementById('grafiek');
  svg.replaceChildren();
  const scans = result.scans.map(point => ({day: point.day, value: point.sld_mm}));
  const baseline = result.latest_forecast.trajectory;
  const treatment = result.latest_forecast.treatment_trajectory;
  const allDays = [...scans, ...baseline].map(point => point.day);
  const values = scans.map(point => point.value);
  for (const point of baseline) values.push(point.p10, point.p90);
  for (const point of treatment) values.push(point.sld_mm);
  for (const old of result.previous_forecasts) for (const point of old.trajectory) values.push(point.median);
  const minX = Math.min(...allDays);
  const maxX = Math.max(...allDays) + 1;
  const minY = Math.min(0, ...values);
  const maxY = Math.max(1, ...values) * 1.12;
  const x = day => 65 + (day - minX) / (maxX - minX) * 800;
  const y = value => 290 - (value - minY) / (maxY - minY) * 235;
  for (let tick = 0; tick <= 4; tick++) {
    const value = minY + (maxY - minY) * tick / 4;
    svg.appendChild(svgElement('line', {x1: 65, x2: 865, y1: y(value), y2: y(value), stroke: '#e0e5eb'}));
    svg.appendChild(svgElement('text', {x: 55, y: y(value) + 4, 'text-anchor': 'end'}, value.toFixed(1)));
    const day = minX + (maxX - minX) * tick / 4;
    svg.appendChild(svgElement('text', {x: x(day), y: 312, 'text-anchor': 'middle'}, Math.round(day)));
  }
  svg.appendChild(svgElement('text', {x: 65, y: 28}, 'SLD (mm)'));
  svg.appendChild(svgElement('text', {x: 465, y: 342, 'text-anchor': 'middle'}, 'Tijd (dagen)'));
  const band = [...baseline.map(p => `${x(p.day)},${y(p.p90)}`),
                ...[...baseline].reverse().map(p => `${x(p.day)},${y(p.p10)}`)].join(' ');
  svg.appendChild(svgElement('polygon', {points: band, fill: '#dbeafe', opacity: .7}));
  function line(points, color, dashed = false) {
    const coordinates = points.map(p => `${x(p.day)},${y(p.value)}`).join(' ');
    svg.appendChild(svgElement('polyline', {points: coordinates, fill: 'none', stroke: color,
      'stroke-width': 2.5, 'stroke-dasharray': dashed ? '6 5' : 'none'}));
  }
  for (const old of result.previous_forecasts) {
    line(old.trajectory.map(p => ({day: p.day, value: p.median})), '#a4acb8', true);
  }
  line(baseline.map(p => ({day: p.day, value: p.median})), '#2563eb');
  line(treatment.map(p => ({day: p.day, value: p.sld_mm})), '#16803d');
  line(scans, '#111827');
  for (const point of scans) {
    const circle = svgElement('circle', {cx: x(point.day), cy: y(point.value), r: 5, fill: '#111827'});
    circle.appendChild(svgElement('title', {}, `Dag ${point.day}: ${point.value} mm`));
    svg.appendChild(circle);
  }
  document.getElementById('legend')?.remove();
  const legend = document.createElement('p');
  legend.id = 'legend';
  legend.textContent = 'Zwart: CT-metingen · Blauw: basisvoorspelling en p10–p90 · Groen: fictief behandelverloop · Grijs: eerdere basisvoorspellingen';
  svg.parentElement.after(legend);
}
